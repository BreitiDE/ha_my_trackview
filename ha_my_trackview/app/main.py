"""My TrackView – Home-Assistant-App: Webserver, API und Scheduler."""
from __future__ import annotations

import asyncio
import collections
import glob
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from aiohttp import ClientSession, ClientTimeout, web

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importer  # noqa: E402
import render  # noqa: E402
from db import DEFAULT_SETTINGS, DETECTION_KEYS, Database  # noqa: E402
from geo import simplify  # noqa: E402
from pdfexport import TEXT as PDF_TEXT  # noqa: E402
from pdfexport import build_pdf  # noqa: E402
from tiles import TileCache  # noqa: E402

VERSION = os.environ.get("TRACKVIEW_VERSION", "1.1.0")
DATA = os.environ.get("TRACKVIEW_DATA", "/data")
PORT = int(os.environ.get("TRACKVIEW_PORT", "8099"))
DEV = os.environ.get("TRACKVIEW_DEV") == "1"
STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN")
INGRESS_IPS = {"172.30.32.2", "127.0.0.1", "::1"}
USER_AGENT = f"MyTrackView/{VERSION} (Home Assistant app; +https://github.com/BreitiDE/ha_my_trackview)"


# ------------------------------------------------------------------ Logging
class RingHandler(logging.Handler):
    def __init__(self, size: int = 1000):
        super().__init__()
        self.buf: collections.deque = collections.deque(maxlen=size)
        self.seq = 0

    def emit(self, record):
        self.seq += 1
        self.buf.append({"id": self.seq, "ts": record.created, "level": record.levelname,
                         "logger": record.name.replace("trackview.", ""),
                         "msg": record.getMessage()})


ring = RingHandler()
logging.basicConfig(level=os.environ.get("TRACKVIEW_LOG_LEVEL", "info").upper(),
                    format="%(asctime)s %(levelname)s (%(name)s) %(message)s", stream=sys.stdout)
logging.getLogger().addHandler(ring)
logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
_LOG = logging.getLogger("trackview")


def _num(v, lo=None, hi=None, typ=float):
    v = typ(v)
    if lo is not None and v < lo:
        raise ValueError
    if hi is not None and v > hi:
        raise ValueError
    return v


SETTING_VALIDATORS = {
    "gps_file": lambda v: str(v).strip(),
    "home_lat": lambda v: None if v in (None, "") else _num(v, -90, 90),
    "home_lon": lambda v: None if v in (None, "") else _num(v, -180, 180),
    "home_radius_m": lambda v: _num(v, 10, 100000),
    "leave_points": lambda v: _num(v, 1, 600, int),
    "stage_gap_min": lambda v: _num(v, 1, 100000),
    "min_trip_km": lambda v: _num(v, 0, 10000),
    "max_speed_kmh": lambda v: _num(v, 20, 2000),
    "jump_km": lambda v: _num(v, 0.1, 100000),
    "file_timezone": lambda v: v if v in ("utc", "local") else (_ for _ in ()).throw(ValueError()),
    "import_interval_min": lambda v: _num(v, 0, 1440, int),
    "distance_unit": lambda v: v if v in ("km", "mi") else (_ for _ in ()).throw(ValueError()),
    "default_color": lambda v: _color(v),
    "language": lambda v: v if v in ("auto", "de", "en") else (_ for _ in ()).throw(ValueError()),
    "tile_url": lambda v: _tile_url(v),
    "tile_cache_days": lambda v: _num(v, 0, 3650),
    "tile_cache_max_mb": lambda v: _num(v, 20, 100000),
    "page_size": lambda v: _num(v, 0, 100000, int),
}


def _color(v):
    v = str(v).strip()
    if len(v) == 7 and v[0] == "#" and all(c in "0123456789abcdefABCDEF" for c in v[1:]):
        return v.lower()
    raise ValueError


def _tile_url(v):
    v = str(v).strip()
    if v.startswith(("http://", "https://")) and all(k in v for k in ("{z}", "{x}", "{y}")):
        return v
    raise ValueError


# ---------------------------------------------------------------------- App
class TrackView:
    def __init__(self):
        self.db = Database(os.path.join(DATA, "trackview.db"))
        self.tiles = TileCache(os.path.join(DATA, "tiles"), USER_AGENT)
        self.thumb_dir = os.path.join(DATA, "thumbs")
        os.makedirs(self.thumb_dir, exist_ok=True)
        self.settings = self.db.get_settings()
        self.ha = {"language": None, "time_zone": None, "latitude": None, "longitude": None}
        self.import_lock = asyncio.Lock()
        self.import_status = {"running": False, "mode": None, "progress": None,
                              "started": None, "error": None}
        self.wakeup = asyncio.Event()
        self._apply_settings()

    # ---- Einstellungen / Umgebung
    def _apply_settings(self):
        s = self.settings
        self.tiles.configure(s["tile_url"], s["tile_cache_days"], s["tile_cache_max_mb"])

    @property
    def tz(self) -> ZoneInfo:
        for name in (self.ha.get("time_zone"), os.environ.get("TZ")):
            if name:
                try:
                    return ZoneInfo(name)
                except Exception:  # noqa: BLE001
                    pass
        return ZoneInfo("UTC")

    @property
    def lang(self) -> str:
        if self.settings["language"] in ("de", "en"):
            return self.settings["language"]
        ha = (self.ha.get("language") or "").lower()
        return "de" if ha.startswith("de") else ("en" if ha else "de")

    async def refresh_ha(self):
        if not SUPERVISOR_TOKEN:
            return
        try:
            async with ClientSession(timeout=ClientTimeout(total=10)) as s:
                async with s.get("http://supervisor/core/api/config",
                                 headers={"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}) as r:
                    if r.status == 200:
                        cfg = await r.json()
                        for k in self.ha:
                            self.ha[k] = cfg.get(k, self.ha[k])
                        _LOG.debug("HA config: lang=%s tz=%s", self.ha["language"], self.ha["time_zone"])
                    else:
                        _LOG.warning("Could not read Home Assistant config (HTTP %s)", r.status)
        except Exception as e:  # noqa: BLE001
            _LOG.warning("Could not read Home Assistant config: %s", e)

    # ---- Import
    async def run_import(self, mode: str = "incremental", restore_deleted: bool = False) -> dict:
        if self.import_lock.locked():
            raise web.HTTPConflict(text=json.dumps({"error": "import_running"}),
                                   content_type="application/json")
        async with self.import_lock:
            st = self.import_status
            st.update(running=True, mode=mode, progress=0, started=time.time(), error=None)
            loop = asyncio.get_running_loop()

            def progress(done, total):
                st["progress"] = round(done / total * 100) if total else None

            try:
                if mode == "rebuild":
                    await loop.run_in_executor(None, self.backup_db, "rebuild")
                res = await loop.run_in_executor(
                    None, lambda: importer.run_import(self.db, self.settings, self.tz, mode,
                                                      restore_deleted, progress))
                st["error"] = None
                return res
            except importer.ImportError_ as e:
                st["error"] = {"code": e.code, "detail": e.detail}
                self.db.set_state({"last_import": int(time.time()),
                                   "last_result": {"error": e.code, "detail": e.detail}})
                _LOG.error("Import failed: %s %s", e.code, e.detail)
                raise
            except Exception as e:  # noqa: BLE001
                st["error"] = {"code": "exception", "detail": str(e)}
                self.db.set_state({"last_import": int(time.time()),
                                   "last_result": {"error": "exception", "detail": str(e)}})
                _LOG.exception("Import failed")
                raise
            finally:
                st.update(running=False, progress=None)

    def backup_db(self, reason: str) -> str:
        d = os.path.join(DATA, "backups")
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f"trackview-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{reason}.db")
        self.db.backup(path)
        files = sorted(glob.glob(os.path.join(d, "trackview-*.db")))
        for old in files[:-5]:
            try:
                os.remove(old)
            except OSError:
                pass
        _LOG.info("Database backup created: %s", path)
        return path

    async def scheduler(self):
        await asyncio.sleep(3)
        last_cleanup = 0.0
        while True:
            interval = int(self.settings.get("import_interval_min") or 0)
            if self.settings.get("home_lat") is not None and os.path.isfile(self.settings["gps_file"]):
                if interval > 0 or not self.db.get_state().get("last_import"):
                    try:
                        await self.run_import("incremental")
                    except Exception:  # noqa: BLE001 – bereits protokolliert
                        pass
            if time.time() - last_cleanup > 3600:
                last_cleanup = time.time()
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self.tiles.cleanup)
                await self.refresh_ha()
            self.wakeup.clear()
            try:
                await asyncio.wait_for(self.wakeup.wait(), timeout=max(1, interval or 60) * 60)
            except asyncio.TimeoutError:
                pass

    # ---- Darstellung
    def color_of(self, t: dict) -> str:
        return t.get("color") or self.settings["default_color"]

    def geometry(self, t: dict, tol: float) -> list[list]:
        pts = t["points"]
        b = [0] + list(t["stage_breaks"]) + [len(pts)]
        out = []
        for i in range(len(b) - 1):
            seg = simplify(pts[b[i]:b[i + 1]], tol)
            out.append([[p[1], p[2]] for p in seg])
        return out


# ------------------------------------------------------------------ Format
def fmt_date(ts, lang, tz):
    return datetime.fromtimestamp(ts, tz).strftime("%d.%m.%Y" if lang == "de" else "%Y-%m-%d")


def fmt_time(ts, tz):
    return datetime.fromtimestamp(ts, tz).strftime("%H:%M")


def fmt_dur(s, lang):
    s = int(s)
    d, rem = divmod(s, 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    if d:
        return f"{d} {'T' if lang == 'de' else 'd'} {h} h"
    if h:
        return f"{h} h {m:02d} min"
    return f"{m} min"


def fmt_dist(m, lang, unit):
    v = m / 1000 if unit == "km" else m / 1609.344
    txt = f"{v:,.1f}"
    if lang == "de":
        txt = txt.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{txt} {unit}"


# ------------------------------------------------------------------- Routes
routes = web.RouteTableDef()


def app_of(request) -> TrackView:
    return request.app["tv"]


def jerr(code: str, status: int = 400, **extra):
    return web.json_response({"error": code, **extra}, status=status)


@web.middleware
async def guard(request, handler):
    if not DEV and request.remote not in INGRESS_IPS:
        return web.Response(status=403, text="Access only via Home Assistant ingress")
    try:
        resp = await handler(request)
    except importer.ImportError_ as e:
        return jerr(e.code, 400, detail=e.detail)
    except (ValueError, KeyError, TypeError) as e:
        _LOG.debug("Bad request %s: %s", request.path, e)
        return jerr("bad_request", 400, detail=str(e))
    if request.path.startswith("/api/") and "Cache-Control" not in resp.headers:
        resp.headers["Cache-Control"] = "no-store"
    return resp


@routes.get("/")
async def index(request):
    with open(os.path.join(STATIC, "index.html"), encoding="utf-8") as f:
        html = f.read().replace("{{VERSION}}", VERSION)
    return web.Response(text=html, content_type="text/html", headers={"Cache-Control": "no-cache"})


@routes.get("/api/info")
async def api_info(request):
    tv = app_of(request)
    return web.json_response({
        "version": VERSION, "lang": tv.lang, "tz": str(tv.tz), "settings": tv.settings,
        "ha_location": {"lat": tv.ha.get("latitude"), "lon": tv.ha.get("longitude")},
        "defaults": DEFAULT_SETTINGS, "palette": render.STAGE_PALETTE,
    })


@routes.get("/api/stats")
async def api_stats(request):
    tv = app_of(request)
    st = tv.db.get_state()
    s = tv.db.stats()
    s.update(last_import=st.get("last_import"), last_result=st.get("last_result"),
             import_status=tv.import_status, tiles_online=tv.tiles.online,
             params_changed=bool(st.get("params")) and st.get("params") != _params_or_none(tv.settings),
             configured=tv.settings.get("home_lat") is not None,
             file_exists=os.path.isfile(tv.settings["gps_file"]))
    return web.json_response(s)


def _params_or_none(settings):
    try:
        return importer.detection_params(settings)
    except (TypeError, ValueError):
        return None


@routes.get("/api/tracks")
async def api_tracks(request):
    tv = app_of(request)
    q = request.query
    scope = q.get("scope", "trips")
    if scope not in ("trips", "unassigned", "trash"):
        raise ValueError("scope")
    size = int(q.get("size", 25))
    page = max(1, int(q.get("page", 1)))
    rows, total = tv.db.list_tracks(scope=scope, sort=q.get("sort", "start"),
                                    order=q.get("order", "desc"),
                                    limit=size if size > 0 else None,
                                    offset=(page - 1) * size if size > 0 else 0)
    for r in rows:
        r["color_eff"] = tv.color_of(r)
    return web.json_response({"rows": rows, "total": total, "page": page, "size": size})


@routes.get("/api/tracks/{id:\\d+}")
async def api_track(request):
    tv = app_of(request)
    t = tv.db.get_track(int(request.match_info["id"]))
    if not t:
        return jerr("not_found", 404)
    loop = asyncio.get_running_loop()
    params = importer.detection_params(tv.settings) if tv.settings.get("home_lat") is not None else None

    def work():
        stages = importer.stage_stats(t, params or {})
        geo = tv.geometry(t, 4)
        return stages, geo

    stages, geo = await loop.run_in_executor(None, work)
    prev_id, next_id = tv.db.neighbours(t["id"])
    t.pop("points")
    t.update(stages=stages, geometry=geo, color_eff=tv.color_of(t), prev_id=prev_id, next_id=next_id)
    return web.json_response(t)


@routes.get("/api/geometry")
async def api_geometry(request):
    tv = app_of(request)
    ids = [int(x) for x in request.query.get("ids", "").split(",") if x.strip().isdigit()][:500]
    tol = 4 if len(ids) <= 3 else (12 if len(ids) <= 20 else 30)
    loop = asyncio.get_running_loop()

    def work():
        out = []
        for i in ids:
            t = tv.db.get_track(i)
            if not t:
                continue
            g = tv.geometry(t, tol)
            t.pop("points")
            t.pop("stage_breaks")
            t.update(geometry=g, color_eff=tv.color_of(t))
            out.append(t)
        out.sort(key=lambda x: x["start_ts"])
        return out

    return web.json_response({"tracks": await loop.run_in_executor(None, work)})


@routes.get("/api/tracks/{id:\\d+}/thumb.png")
async def api_thumb(request):
    tv = app_of(request)
    tid = int(request.match_info["id"])
    t = tv.db.get_track(tid, with_points=False)
    if not t:
        return web.Response(status=404)
    color = tv.color_of(t)
    tag = hashlib.sha1(f"{t['updated_at']}{color}{tv.tiles.url}".encode()).hexdigest()[:10]
    path = os.path.join(tv.thumb_dir, f"{tid}_{tag}.png")
    if not os.path.exists(path):
        loop = asyncio.get_running_loop()

        def work():
            full = tv.db.get_track(tid)
            img = render.render_map([render.track_layer(full, color, False)], 240, 160, tv.tiles,
                                    pad=14, max_zoom=15, line_width=3, markers=False,
                                    attribution=False)
            for old in glob.glob(os.path.join(tv.thumb_dir, f"{tid}_*.png")):
                try:
                    os.remove(old)
                except OSError:
                    pass
            tmp = path + ".tmp"
            with open(tmp, "wb") as f:
                f.write(render.to_png(img))
            os.replace(tmp, path)
            return tv.tiles.online

        online = await loop.run_in_executor(None, work)
        if not online:
            # ohne Netz gerendert: nicht dauerhaft behalten, später neu versuchen
            with open(path, "rb") as f:
                body = f.read()
            os.remove(path)
            return web.Response(body=body, content_type="image/png",
                                headers={"Cache-Control": "no-store"})
    return web.FileResponse(path, headers={"Cache-Control": "private, max-age=86400"})


@routes.get("/api/pdf")
async def api_pdf(request):
    tv = app_of(request)
    ids = [int(x) for x in request.query.get("ids", "").split(",") if x.strip().isdigit()][:200]
    by_stage = request.query.get("stages") == "1"
    override = request.query.get("color")
    if override:
        override = _color(override)
    lang = tv.lang
    T = PDF_TEXT[lang]
    tz = tv.tz
    unit = tv.settings["distance_unit"]
    loop = asyncio.get_running_loop()

    def work():
        tracks = [t for t in (tv.db.get_track(i) for i in ids) if t]
        if not tracks:
            return None, None
        tracks.sort(key=lambda t: t["start_ts"])
        if len(tracks) == 1:
            t = tracks[0]
            color = override or tv.color_of(t)
            layers = [render.track_layer(t, color, by_stage)]
            stages = importer.stage_stats(t, {})
            title = f"{T['trip']} {fmt_date(t['start_ts'], lang, tz)}"
            if t.get("name"):
                title += f" - {t['name']}"
            end_txt = fmt_time(t["end_ts"], tz)
            if fmt_date(t["end_ts"], lang, tz) != fmt_date(t["start_ts"], lang, tz):
                end_txt = f"{fmt_date(t['end_ts'], lang, tz)} {end_txt}"
            subtitle = f"{fmt_date(t['start_ts'], lang, tz)} {fmt_time(t['start_ts'], tz)} - {end_txt}"
            facts = [(T["date"], fmt_date(t["start_ts"], lang, tz)),
                     (T["start"], fmt_time(t["start_ts"], tz)), (T["end"], end_txt),
                     (T["duration"], fmt_dur(t["duration_s"], lang)),
                     (T["driving"], fmt_dur(t["driving_s"], lang)),
                     (T["distance"], fmt_dist(t["distance_m"], lang, unit)),
                     (T["stages"], str(t["stage_count"]))]
            head, rows, sw = [], [], None
            if len(stages) > 1:
                head = ["", T["stage"], T["start"], T["end"], T["duration"], T["distance"]]
                sw = [render.palette_color(i) if by_stage else color for i in range(len(stages))]
                for i, s in enumerate(stages):
                    rows.append(["", f"{i + 1}",
                                 f"{fmt_date(s['start_ts'], lang, tz)} {fmt_time(s['start_ts'], tz)}",
                                 f"{fmt_date(s['end_ts'], lang, tz)} {fmt_time(s['end_ts'], tz)}",
                                 fmt_dur(s["duration_s"], lang), fmt_dist(s["distance_m"], lang, unit)])
            fname = f"TrackView_{datetime.fromtimestamp(t['start_ts'], tz).strftime('%Y-%m-%d_%H%M')}.pdf"
        else:
            colors = multi_colors(tv, tracks)
            layers = [render.track_layer(t, c, False) for t, c in zip(tracks, colors)]
            first, last = tracks[0], tracks[-1]
            title = f"{len(tracks)} {T['trips']}"
            subtitle = f"{fmt_date(first['start_ts'], lang, tz)} - {fmt_date(last['end_ts'], lang, tz)}"
            facts = [(T["trips"], str(len(tracks))),
                     (T["duration"], fmt_dur(sum(t["duration_s"] for t in tracks), lang)),
                     (T["driving"], fmt_dur(sum(t["driving_s"] for t in tracks), lang)),
                     (T["distance"], fmt_dist(sum(t["distance_m"] for t in tracks), lang, unit)),
                     (T["stages"], str(sum(t["stage_count"] for t in tracks)))]
            head = ["", T["date"], T["start"], T["end"], T["duration"], T["distance"]]
            rows = [["", fmt_date(t["start_ts"], lang, tz), fmt_time(t["start_ts"], tz),
                     f"{fmt_date(t['end_ts'], lang, tz)} {fmt_time(t['end_ts'], tz)}",
                     fmt_dur(t["duration_s"], lang), fmt_dist(t["distance_m"], lang, unit)]
                    for t in tracks]
            sw = colors
            fname = f"TrackView_{len(tracks)}_{datetime.now(tz).strftime('%Y-%m-%d')}.pdf"
        # Seitenverhältnis exakt wie der Kartenbereich im PDF (277 x 112 bzw. 140 mm)
        img = render.render_map(layers, 2200, round(2200 * (112 if rows else 140) / 277), tv.tiles, pad=60,
                                line_width=5, max_zoom=17)
        png = render.to_png(img)
        pdf = build_pdf(lang=lang, title=title, subtitle=subtitle, facts=facts, map_png=png,
                        table_head=head, table_rows=rows, swatches=sw, tz=tz)
        return pdf, fname

    pdf, fname = await loop.run_in_executor(None, work)
    if pdf is None:
        return jerr("not_found", 404)
    disp = "attachment" if request.query.get("dl") == "1" else "inline"
    return web.Response(body=pdf, content_type="application/pdf",
                        headers={"Content-Disposition": f'{disp}; filename="{fname}"'})


def multi_colors(tv, tracks):
    """Eigene Farbe, falls gesetzt – sonst Palette, damit Reisen unterscheidbar sind."""
    used = {(t.get("color") or "").lower() for t in tracks if t.get("color")}
    out, k = [], 0
    for t in tracks:
        if t.get("color"):
            out.append(t["color"])
            continue
        while render.palette_color(k).lower() in used:
            k += 1
        out.append(render.palette_color(k))
        k += 1
    return out


@routes.patch("/api/tracks/{id:\\d+}")
async def api_patch(request):
    tv = app_of(request)
    body = await request.json()
    fields = {}
    if "color" in body:
        fields["color"] = _color(body["color"]) if body["color"] else None
    if "name" in body:
        fields["name"] = (str(body["name"]).strip()[:120] or None) if body["name"] is not None else None
    tv.db.set_fields(int(request.match_info["id"]), **fields)
    return web.json_response({"ok": True})


async def _ids(request) -> list[int]:
    body = await request.json()
    ids = [int(i) for i in body.get("ids", [])]
    if not ids:
        raise ValueError("ids")
    return ids


@routes.post("/api/tracks/delete")
async def api_delete(request):
    tv = app_of(request)
    now = int(time.time())
    ids = await _ids(request)
    for i in ids:
        tv.db.set_fields(i, deleted=1, deleted_at=now)
    _LOG.info("%s track(s) moved to trash", len(ids))
    return web.json_response({"ok": True, "count": len(ids)})


@routes.post("/api/tracks/restore")
async def api_restore(request):
    tv = app_of(request)
    ids = await _ids(request)
    for i in ids:
        tv.db.set_fields(i, deleted=0, deleted_at=None)
    _LOG.info("%s track(s) restored", len(ids))
    return web.json_response({"ok": True, "count": len(ids)})


@routes.post("/api/tracks/purge")
async def api_purge(request):
    tv = app_of(request)
    body = await request.json()
    if body.get("all"):
        rows, _ = tv.db.list_tracks(scope="trash")
        ids = [r["id"] for r in rows]
    else:
        ids = [int(i) for i in body.get("ids", [])]
    n = tv.db.purge(ids)
    for i in ids:
        for f in glob.glob(os.path.join(tv.thumb_dir, f"{i}_*.png")):
            try:
                os.remove(f)
            except OSError:
                pass
    _LOG.info("%s track(s) deleted permanently", n)
    return web.json_response({"ok": True, "count": n})


@routes.post("/api/tracks/assign")
async def api_assign(request):
    tv = app_of(request)
    ids = await _ids(request)
    for i in ids:
        t = tv.db.get_track(i, with_points=False)
        if t and t["status"] == "unassigned":
            tv.db.set_fields(i, status="trip", reason=None, edited=1)
    _LOG.info("%s track(s) accepted as trip", len(ids))
    return web.json_response({"ok": True})


@routes.post("/api/tracks/merge")
async def api_merge(request):
    tv = app_of(request)
    ids = await _ids(request)
    async with tv.import_lock:
        tid = await asyncio.get_running_loop().run_in_executor(
            None, importer.merge_tracks, tv.db, ids, importer.detection_params(tv.settings))
    _LOG.info("Tracks %s merged into %s", ids, tid)
    return web.json_response({"ok": True, "id": tid})


@routes.post("/api/tracks/{id:\\d+}/split")
async def api_split(request):
    tv = app_of(request)
    body = await request.json()
    async with tv.import_lock:
        a, b = await asyncio.get_running_loop().run_in_executor(
            None, importer.split_track, tv.db, int(request.match_info["id"]), int(body["stage"]),
            importer.detection_params(tv.settings))
    _LOG.info("Track %s split, new track %s", a, b)
    return web.json_response({"ok": True, "ids": [a, b]})


@routes.post("/api/import")
async def api_import(request):
    tv = app_of(request)
    body = await request.json() if request.can_read_body else {}
    mode = body.get("mode", "incremental")
    if mode not in ("incremental", "reconcile", "rebuild"):
        raise ValueError("mode")
    if tv.import_lock.locked():
        return jerr("import_running", 409)
    task = asyncio.create_task(tv.run_import(mode, bool(body.get("restore_deleted"))))
    task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
    await asyncio.sleep(0.05)
    return web.json_response({"ok": True, "started": True})


@routes.get("/api/settings")
async def api_settings_get(request):
    return web.json_response(app_of(request).settings)


@routes.post("/api/settings")
async def api_settings_post(request):
    tv = app_of(request)
    body = await request.json()
    clean, errors = {}, []
    for k, v in body.items():
        if k not in SETTING_VALIDATORS:
            continue
        try:
            clean[k] = SETTING_VALIDATORS[k](v)
        except (ValueError, TypeError):
            errors.append(k)
    if errors:
        return jerr("invalid_settings", 400, fields=errors)
    old = dict(tv.settings)
    tv.db.save_settings(clean)
    tv.settings = tv.db.get_settings()
    tv._apply_settings()
    changed_detection = any(old.get(k) != tv.settings.get(k) for k in DETECTION_KEYS)
    has_tracks = tv.db.stats()["trips"] > 0
    _LOG.info("Settings saved (%s)", ", ".join(sorted(clean)))
    if old.get("tile_url") != tv.settings.get("tile_url"):
        for f in glob.glob(os.path.join(tv.thumb_dir, "*.png")):
            try:
                os.remove(f)
            except OSError:
                pass
    tv.wakeup.set()
    return web.json_response({"ok": True, "settings": tv.settings,
                              "rebuild_recommended": changed_detection and has_tracks})


@routes.get("/api/file/check")
async def api_file_check(request):
    tv = app_of(request)
    path = request.query.get("path") or tv.settings["gps_file"]
    out = {"path": path, "exists": os.path.isfile(path)}
    if out["exists"]:
        out["size"] = os.path.getsize(path)
        out["mtime"] = os.path.getmtime(path)
        parser = importer.LineParser(tv.settings["file_timezone"], tv.tz)
        sample, ok = [], 0
        with open(path, "rb") as f:
            for _ in range(20):
                raw = f.readline()
                if not raw:
                    break
                sample.append(raw.decode("utf-8", "replace").rstrip("\r\n")[:160])
                if parser.parse(raw):
                    ok += 1
        out.update(sample=sample[:6], parsed=ok, checked=len(sample))
    else:
        parent = os.path.dirname(path)
        out["dir_exists"] = os.path.isdir(parent)
    return web.json_response(out)


@routes.get("/api/ha/location")
async def api_ha_location(request):
    tv = app_of(request)
    await tv.refresh_ha()
    return web.json_response({"lat": tv.ha.get("latitude"), "lon": tv.ha.get("longitude")})


@routes.get("/api/tiles/info")
async def api_tiles_info(request):
    tv = app_of(request)
    size, count = await asyncio.get_running_loop().run_in_executor(None, tv.tiles.usage)
    return web.json_response({"bytes": size, "count": count, "online": tv.tiles.online,
                              "stats": tv.tiles.stats})


@routes.post("/api/tiles/clear")
async def api_tiles_clear(request):
    tv = app_of(request)
    await asyncio.get_running_loop().run_in_executor(None, tv.tiles.clear)
    for f in glob.glob(os.path.join(tv.thumb_dir, "*.png")):
        try:
            os.remove(f)
        except OSError:
            pass
    _LOG.info("Tile cache cleared")
    return web.json_response({"ok": True})


@routes.get("/api/tiles/{z:\\d+}/{x:\\d+}/{y:\\d+}.png")
async def api_tile(request):
    tv = app_of(request)
    z, x, y = (int(request.match_info[k]) for k in ("z", "x", "y"))
    res = await asyncio.get_running_loop().run_in_executor(None, tv.tiles.get, z, x, y)
    if not res:
        return web.Response(status=504, headers={"Cache-Control": "no-store"})
    return web.Response(body=res[0], content_type=res[1].split(";")[0],
                        headers={"Cache-Control": "private, max-age=3600"})


@routes.post("/api/backup")
async def api_backup(request):
    tv = app_of(request)
    path = await asyncio.get_running_loop().run_in_executor(None, tv.backup_db, "manual")
    return web.json_response({"ok": True, "path": path})


@routes.get("/api/log")
async def api_log(request):
    after = int(request.query.get("after", 0))
    levels = {"debug": 10, "info": 20, "warning": 30, "error": 40}
    minlvl = levels.get(request.query.get("level", "debug"), 10)
    rows = [r for r in ring.buf
            if r["id"] > after and levels.get(r["level"].lower(), 40) >= minlvl]
    return web.json_response({"rows": rows[-500:], "last": ring.seq})


@routes.post("/api/log/clear")
async def api_log_clear(request):
    ring.buf.clear()
    return web.json_response({"ok": True})


# ------------------------------------------------------------------- Start
async def on_startup(app):
    tv: TrackView = app["tv"]
    await tv.refresh_ha()
    _LOG.info("My TrackView %s ready – language %s, time zone %s", VERSION, tv.lang, tv.tz)
    if tv.settings.get("home_lat") is None:
        _LOG.warning("Home location not configured yet – please open Settings")
    app["scheduler"] = asyncio.create_task(tv.scheduler())


async def on_cleanup(app):
    task = app.get("scheduler")
    if task:
        task.cancel()


def make_app() -> web.Application:
    app = web.Application(middlewares=[guard], client_max_size=4 * 1024 * 1024)
    app["tv"] = TrackView()
    app.add_routes(routes)
    app.router.add_static("/static/", STATIC, show_index=False)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == "__main__":
    web.run_app(make_app(), host="0.0.0.0", port=PORT, access_log=None, print=None)
