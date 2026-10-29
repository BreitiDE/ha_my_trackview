"""Einlesen der GPS-Logdatei und Erkennung von Reisen und Etappen.

Dateiformat (CSV, eine Zeile pro Messpunkt):
    date,latitude,longitude,altitude,speed
    2026-10-18T15:02:01,51.47258759,6.60797644,24,39

Erkennung
---------
* Zustand ZUHAUSE: Punkte innerhalb des Heimradius. Eine Abfahrt gilt erst als bestätigt,
  wenn ``leave_points`` Punkte in Folge außerhalb liegen (oder einer deutlich außerhalb).
* Zustand UNTERWEGS: alle Punkte gehören zur Reise. Der erste Punkt wieder im Radius
  beendet die Reise.
* Etappen: Lücken im Log länger als ``stage_gap_min`` (das GPS loggt im Stand nicht).
* Nicht zuordenbar: Daten beginnen außerhalb des Heimradius, oder nach einer Lücke
  springt die Position um mehr als ``jump_km`` (Daten fehlen).
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from geo import haversine

_LOG = logging.getLogger("trackview.import")

HOME, AWAY, UNKNOWN = "home", "away", "unknown"


class ImportError_(Exception):
    """Fehler, der dem Benutzer angezeigt wird (Schlüssel für Übersetzung + Details)."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


# --------------------------------------------------------------------- Parser
class LineParser:
    def __init__(self, file_tz: str, local_tz: ZoneInfo):
        self.local = file_tz == "local"
        self.tz = local_tz
        self._cache_key: bytes | None = None
        self._cache_val = 0

    def parse(self, raw: bytes):
        """Gibt (t, lat, lon, alt, spd) zurück oder None bei ungültiger Zeile."""
        parts = raw.strip().split(b",")
        if len(parts) < 3:
            return None
        try:
            ts = self._ts(parts[0].strip().strip(b'"'))
            lat = float(parts[1])
            lon = float(parts[2])
        except (ValueError, OverflowError):
            return None
        if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
            return None
        try:
            alt = round(float(parts[3])) if len(parts) > 3 and parts[3].strip() else None
        except ValueError:
            alt = None
        try:
            spd = round(float(parts[4]), 1) if len(parts) > 4 and parts[4].strip() else None
        except ValueError:
            spd = None
        return ts, round(lat, 7), round(lon, 7), alt, spd

    def _ts(self, s: bytes) -> int:
        # Unix-Zeitstempel (Sekunden oder Millisekunden)
        if s.replace(b".", b"", 1).isdigit():
            v = float(s)
            return int(v / 1000 if v > 1e11 else v)
        # Cache auf Minuten-Präfix spart Zeit bei 1-Hz-Logs
        txt = s.decode("ascii")
        if len(txt) >= 19 and txt[19:] == "" and txt[10] in "T ":
            key = s[:16]
            if key == self._cache_key:
                return self._cache_val + int(txt[17:19])
            dt = self._dt(txt[:16] + ":00")
            self._cache_key = key
            self._cache_val = int(dt.timestamp())
            return self._cache_val + int(txt[17:19])
        return int(self._dt(txt).timestamp())

    def _dt(self, txt: str) -> datetime:
        if txt.endswith("Z"):
            txt = txt[:-1] + "+00:00"
        dt = datetime.fromisoformat(txt.replace(" ", "T", 1))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=self.tz if self.local else timezone.utc)
        return dt


# ------------------------------------------------------------- Statistiken
def build_candidate(points: list, params: dict, status: str, reason: str | None) -> dict:
    """Bereinigt Punkte und berechnet Kennzahlen für einen Track."""
    pts = dedupe(points)
    gap = params["stage_gap_s"]
    jump_m = params["jump_m"]
    breaks: list[int] = []
    dist = 0.0
    driving = 0
    stage_start_t = pts[0][0]
    minlat = minlon = 1e9
    maxlat = maxlon = -1e9
    for i, p in enumerate(pts):
        if p[1] < minlat:
            minlat = p[1]
        if p[1] > maxlat:
            maxlat = p[1]
        if p[2] < minlon:
            minlon = p[2]
        if p[2] > maxlon:
            maxlon = p[2]
        if i == 0:
            continue
        q = pts[i - 1]
        d = haversine(q[1], q[2], p[1], p[2])
        if p[0] - q[0] > gap:
            breaks.append(i)
            driving += q[0] - stage_start_t
            stage_start_t = p[0]
            if d <= jump_m:
                dist += d
        else:
            dist += d
    driving += pts[-1][0] - stage_start_t
    return {
        "status": status,
        "reason": reason,
        "start_ts": pts[0][0],
        "end_ts": pts[-1][0],
        "duration_s": pts[-1][0] - pts[0][0],
        "driving_s": driving,
        "distance_m": round(dist, 1),
        "stage_count": len(breaks) + 1,
        "stage_breaks": breaks,
        "point_count": len(pts),
        "bbox": (minlat, minlon, maxlat, maxlon),
        "points": pts,
    }


def dedupe(points: list) -> list:
    """Entfernt aufeinanderfolgende Punkte mit identischer Position.

    Ein Punkt bleibt erhalten, wenn seit dem letzten behaltenen Punkt mehr als 60 s
    vergangen sind – so bleibt die Zeitachse (und damit die Etappenerkennung) korrekt.
    """
    if not points:
        return []
    out = [list(points[0])]
    for p in points[1:]:
        last = out[-1]
        if p[0] < last[0]:
            continue
        if p[1] == last[1] and p[2] == last[2] and p[0] - last[0] < 60:
            continue
        out.append(list(p))
    if out[-1][0] != points[-1][0]:
        out.append(list(points[-1]))
    return out


def stage_ranges(cand_or_track: dict) -> list[tuple[int, int]]:
    """Index-Bereiche [a, b) der Etappen."""
    n = cand_or_track["point_count"] if "points" not in cand_or_track else len(cand_or_track["points"])
    b = [0] + list(cand_or_track["stage_breaks"]) + [n]
    return [(b[i], b[i + 1]) for i in range(len(b) - 1)]


def stage_stats(track: dict, params: dict) -> list[dict]:
    pts = track["points"]
    out = []
    for a, b in stage_ranges(track):
        seg = pts[a:b]
        d = 0.0
        for i in range(1, len(seg)):
            d += haversine(seg[i - 1][1], seg[i - 1][2], seg[i][1], seg[i][2])
        out.append({"start_ts": seg[0][0], "end_ts": seg[-1][0],
                    "duration_s": seg[-1][0] - seg[0][0], "distance_m": round(d, 1),
                    "points": len(seg)})
    return out


# ---------------------------------------------------------------- Erkennung
class Detector:
    def __init__(self, params: dict, state: str = UNKNOWN):
        self.p = params
        self.state = state
        self.home = (params["home_lat"], params["home_lon"])
        self.radius = params["home_radius_m"]
        self.candidates: list[dict] = []
        self.seg: list = []
        self.seg_reason: str | None = None
        self.seg_anchor: tuple[int, int] | None = None  # (offset, ts) für Wiederaufnahme
        self.pending: list = []
        self.last_home: tuple | None = None
        self.last_home_off: tuple[int, int] | None = None
        self.unknown_anchor: tuple[int, int] | None = None
        # Ausreißerfilter
        self.last_ok = None
        self.drops = 0
        self.dropped_total = 0
        self.fed = 0

    def _inside(self, p) -> bool:
        return haversine(self.home[0], self.home[1], p[1], p[2]) <= self.radius

    def _plausible(self, p) -> bool:
        q = self.last_ok
        if q is None:
            return True
        dt = p[0] - q[0]
        if dt > self.p["stage_gap_s"]:
            return True  # nach Lücken ist jeder Sprung erlaubt (wird separat bewertet)
        d = haversine(q[1], q[2], p[1], p[2])
        if d < 50:
            return True
        if dt <= 0:
            return False
        return d / dt * 3.6 <= self.p["max_speed_kmh"]

    def feed(self, p, offset: int) -> None:
        self.fed += 1
        if not self._plausible(p):
            self.drops += 1
            self.dropped_total += 1
            if self.drops < 10:
                return
        self.drops = 0
        prev = self.last_ok
        self.last_ok = p

        if self.state == UNKNOWN:
            if self._inside(p):
                self.state = HOME
                self.last_home, self.last_home_off = p, (offset, p[0])
            else:
                self.state = AWAY
                self.seg = [p]
                self.seg_reason = "start_outside"
                self.seg_anchor = None
                self.unknown_anchor = (offset, p[0])
            return

        if self.state == HOME:
            if self._inside(p):
                self.pending.clear()
                self.last_home, self.last_home_off = p, (offset, p[0])
                return
            self.pending.append((p, offset))
            far = haversine(self.home[0], self.home[1], p[1], p[2]) > 3 * self.radius
            if len(self.pending) >= self.p["leave_points"] or far:
                first = self.pending[0][0]
                pts = [x[0] for x in self.pending]
                reason = None
                if self.last_home and first[0] - self.last_home[0] <= self.p["stage_gap_s"]:
                    pts.insert(0, self.last_home)
                    anchor = self.last_home_off
                else:
                    anchor = (self.pending[0][1], first[0])
                    if haversine(self.home[0], self.home[1], first[1], first[2]) > self.p["jump_m"]:
                        reason = "gap"
                self.state = AWAY
                self.seg = pts
                self.seg_reason = reason
                self.seg_anchor = anchor
                self.pending = []
            return

        # AWAY
        if prev is not None and p[0] - prev[0] > self.p["stage_gap_s"]:
            if haversine(prev[1], prev[2], p[1], p[2]) > self.p["jump_m"]:
                self.seg_reason = self.seg_reason or "gap"
        self.seg.append(p)
        if self._inside(p):
            self._close(p, offset)

    def _close(self, p, offset: int) -> None:
        status = "unassigned" if self.seg_reason else "trip"
        cand = build_candidate(self.seg, self.p, status, self.seg_reason)
        if cand["distance_m"] >= self.p["min_trip_m"] or status == "unassigned":
            cand["key"] = cand["start_ts"]
            self.candidates.append(cand)
        self.state = HOME
        self.seg = []
        self.seg_reason = None
        self.seg_anchor = None
        self.unknown_anchor = None
        self.last_home, self.last_home_off = p, (offset, p[0])

    def finish(self) -> dict:
        """Schließt die Auswertung ab und liefert den Wiederaufnahmepunkt."""
        resume = {"state": self.state, "offset": 0, "ts": 0}
        if self.state == AWAY and self.seg:
            cand = build_candidate(self.seg, self.p, "running", self.seg_reason)
            cand["key"] = cand["start_ts"]
            self.candidates.append(cand)
            if self.seg_anchor is not None:
                resume.update(state=HOME, offset=self.seg_anchor[0], ts=self.seg_anchor[1])
            elif self.unknown_anchor is not None:
                resume.update(state=UNKNOWN, offset=self.unknown_anchor[0], ts=self.unknown_anchor[1])
        elif self.state == HOME and self.last_home_off:
            resume.update(state=HOME, offset=self.last_home_off[0], ts=self.last_home_off[1])
        else:
            resume["state"] = UNKNOWN
        return resume


# ------------------------------------------------------------------ Import
def detection_params(settings: dict) -> dict:
    return {
        "home_lat": float(settings["home_lat"]),
        "home_lon": float(settings["home_lon"]),
        "home_radius_m": float(settings["home_radius_m"]),
        "leave_points": max(1, int(settings["leave_points"])),
        "stage_gap_s": max(60, int(float(settings["stage_gap_min"]) * 60)),
        "min_trip_m": float(settings["min_trip_km"]) * 1000,
        "max_speed_kmh": float(settings["max_speed_kmh"]),
        "jump_m": float(settings["jump_km"]) * 1000,
    }


def file_signature(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha1(f.read(4096)).hexdigest()


def run_import(db, settings: dict, local_tz: ZoneInfo, mode: str = "incremental",
               restore_deleted: bool = False, progress=None) -> dict:
    """mode: incremental | reconcile | rebuild"""
    t0 = time.time()
    if settings.get("home_lat") in (None, "") or settings.get("home_lon") in (None, ""):
        raise ImportError_("no_home")
    path = settings["gps_file"]
    if not os.path.isfile(path):
        raise ImportError_("file_missing", path)
    params = detection_params(settings)
    size = os.path.getsize(path)
    sig = file_signature(path)
    st = db.get_state()

    start_offset, skip_ts, state = 0, None, UNKNOWN
    if mode == "incremental" and st.get("resume_state"):
        if st.get("file_sig") == sig and size >= int(st.get("resume_offset", 0)):
            start_offset = int(st.get("resume_offset", 0))
            state = st["resume_state"]
        else:
            _LOG.warning("GPS file changed or was replaced – resuming by timestamp")
            skip_ts = int(st.get("resume_ts") or 0)
            state = st["resume_state"]
        if st.get("params") != params:
            _LOG.warning("Detection settings changed since last import – a rebuild is recommended")

    parser = LineParser(settings.get("file_timezone", "utc"), local_tz)
    det = Detector(params, state)
    lines = invalid = out_of_order = 0
    last_t = None
    ooo_run = 0
    future_limit = int(time.time()) + 86400
    offset = start_offset
    with open(path, "rb") as f:
        f.seek(start_offset)
        while True:
            raw = f.readline()
            if not raw:
                break
            if not raw.endswith(b"\n"):
                break  # unvollständige letzte Zeile – wird beim nächsten Mal gelesen
            line_off = offset
            offset += len(raw)
            lines += 1
            if progress and lines % 200000 == 0:
                progress(offset, size)
            p = parser.parse(raw)
            if p is None:
                if raw.strip() and not raw.lower().startswith(b"date"):
                    invalid += 1
                continue
            if skip_ts is not None and p[0] < skip_ts:
                continue
            if p[0] > future_limit:
                invalid += 1
                continue
            if last_t is not None and p[0] < last_t:
                out_of_order += 1
                ooo_run += 1
                if ooo_run <= 20:
                    continue
                # viele Zeilen in Folge "älter": der vorherige Zeitstempel war vermutlich falsch
                _LOG.warning("Timestamp sequence reset at offset %s", line_off)
            ooo_run = 0
            last_t = p[0]
            det.feed(p, line_off)
    resume = det.finish()
    if det.fed == 0 and st.get("resume_state") and mode == "incremental":
        # nichts Neues gelesen – bisherigen Wiederaufnahmepunkt beibehalten
        resume = {"state": st["resume_state"], "offset": int(st.get("resume_offset", 0)),
                  "ts": int(st.get("resume_ts") or 0)}
    result = apply_candidates(db, det.candidates, mode=mode, resume=resume, sig=sig,
                              params=params, restore_deleted=restore_deleted,
                              window_start=(skip_ts if skip_ts is not None else st.get("resume_ts", 0))
                              if mode == "incremental" else None)
    result.update(lines=lines, invalid=invalid, out_of_order=out_of_order,
                  dropped=det.dropped_total, bytes=offset - start_offset, mode=mode,
                  seconds=round(time.time() - t0, 2))
    db.set_state({"last_import": int(time.time()), "last_result": result})
    _LOG.info("Import (%s): %s lines, %s new, %s updated, %s overlapping skipped, %.2fs",
              mode, lines, result["inserted"], result["updated"], result["overlap"], result["seconds"])
    if invalid:
        _LOG.warning("%s invalid lines skipped", invalid)
    if out_of_order:
        _LOG.warning("%s lines with older timestamps skipped", out_of_order)
    return result


def apply_candidates(db, cands: list[dict], *, mode: str, resume: dict, sig: str, params: dict,
                     restore_deleted: bool, window_start) -> dict:
    inserted = updated = overlap = restored = removed = 0
    keys = {c["key"] for c in cands}
    with db.transaction() as c:
        if mode == "rebuild":
            c.execute("DELETE FROM tracks")
            c.execute("DELETE FROM track_keys")
            c.execute("DELETE FROM sqlite_sequence WHERE name='tracks'")
        # Veraltete „läuft“-Einträge entfernen, die nicht mehr erzeugt wurden
        rows = c.execute("SELECT t.id, k.key FROM tracks t LEFT JOIN track_keys k ON k.track_id=t.id "
                         "WHERE t.status='running' AND t.edited=0").fetchall()
        for r in rows:
            if r["key"] not in keys and (window_start is None or (r["key"] or 0) >= (window_start or 0)):
                c.execute("DELETE FROM tracks WHERE id=?", (r["id"],))
                removed += 1
        for cand in cands:
            k = c.execute("SELECT t.id, t.edited, t.deleted FROM track_keys k JOIN tracks t ON "
                          "t.id=k.track_id WHERE k.key=?", (cand["key"],)).fetchone()
            if k:
                if restore_deleted and k["deleted"]:
                    c.execute("UPDATE tracks SET deleted=0, deleted_at=NULL WHERE id=?", (k["id"],))
                    restored += 1
                if not k["edited"]:
                    db.update_track_geometry(c, k["id"], cand)
                    updated += 1
                continue
            ov = c.execute("SELECT id FROM tracks WHERE start_ts < ? AND end_ts > ? LIMIT 1",
                           (cand["end_ts"], cand["start_ts"])).fetchone()
            if ov:
                overlap += 1
                continue
            db.insert_track(c, cand, keys=[cand["key"]])
            inserted += 1
        db.set_state({"resume_state": resume["state"], "resume_offset": resume["offset"],
                      "resume_ts": resume["ts"], "file_sig": sig, "params": params}, c)
    return {"inserted": inserted, "updated": updated, "overlap": overlap,
            "restored": restored, "removed_running": removed, "candidates": len(cands)}


# --------------------------------------------------------------- Bearbeiten
def merge_tracks(db, ids: list[int], params: dict) -> int:
    tracks = [db.get_track(i) for i in ids]
    tracks = [t for t in tracks if t and not t["deleted"]]
    if len(tracks) < 2:
        raise ImportError_("merge_min_two")
    tracks.sort(key=lambda t: t["start_ts"])
    pts = []
    for t in tracks:
        pts.extend(t["points"])
    pts.sort(key=lambda p: p[0])
    statuses = {t["status"] for t in tracks}
    status = "running" if "running" in statuses else ("trip" if "trip" in statuses else "unassigned")
    cand = build_candidate(pts, params, status, "manual" if status == "unassigned" else None)
    keep = tracks[0]
    with db.transaction() as c:
        db.update_track_geometry(c, keep["id"], cand, edited=1,
                                 reason=cand["reason"] or "")
        for t in tracks[1:]:
            c.execute("UPDATE track_keys SET track_id=? WHERE track_id=?", (keep["id"], t["id"]))
            c.execute("DELETE FROM tracks WHERE id=?", (t["id"],))
    return keep["id"]


def split_track(db, tid: int, stage_index: int, params: dict) -> tuple[int, int]:
    """Teilt einen Track vor der Etappe ``stage_index`` (1-basiert ab 2. Etappe)."""
    t = db.get_track(tid)
    if not t:
        raise ImportError_("not_found")
    breaks = t["stage_breaks"]
    if stage_index < 1 or stage_index > len(breaks):
        raise ImportError_("split_invalid")
    cut = breaks[stage_index - 1]
    a = build_candidate(t["points"][:cut], params, t["status"] if t["status"] != "running" else "unassigned",
                        t["reason"] or "manual")
    b = build_candidate(t["points"][cut:], params, t["status"], t["reason"] or "manual")
    if a["status"] == "trip":
        a["status"] = "unassigned"
    if b["status"] == "trip":
        b["status"] = "unassigned"
    with db.transaction() as c:
        db.update_track_geometry(c, tid, a, edited=1)
        nid = db.insert_track(c, b, edited=1, color=t["color"], keys=[b["start_ts"]])
    return tid, nid
