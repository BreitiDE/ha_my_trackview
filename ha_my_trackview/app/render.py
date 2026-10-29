"""Statische Kartenbilder (Miniaturen und PDF) aus OSM-Kacheln + Tracks."""
from __future__ import annotations

import colorsys
import io
import math
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageDraw, ImageFont

from geo import fit_zoom, lonlat_to_px, simplify

STAGE_PALETTE = ["#ce6c00", "#2a78d6", "#1baf7a", "#6250d6", "#d55181", "#008300"]
MULTI_PALETTE = STAGE_PALETTE
BG = (232, 230, 225)
_pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix="tiles")


def palette_color(i: int) -> str:
    if i < len(STAGE_PALETTE):
        return STAGE_PALETTE[i]
    h = (i * 0.618033988749895) % 1.0
    r, g, b = colorsys.hls_to_rgb(h, 0.45, 0.65)
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = (h or "#ce6c00").lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return 206, 108, 0


def _font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # ältere Pillow-Versionen
        return ImageFont.load_default()


def render_map(layers: list[dict], width: int, height: int, tiles, *, pad: int = 24,
               max_zoom: int = 16, line_width: float = 4.0, markers: bool = True,
               attribution: bool = True) -> Image.Image:
    """layers: [{"segments": [[(lat, lon), ...], ...], "colors": [hex, ...]}]

    Jedes Segment wird in seiner Farbe gezeichnet (colors[i] oder colors[0]).
    """
    all_pts = [pt for L in layers for seg in L["segments"] for pt in seg]
    if not all_pts:
        return Image.new("RGB", (width, height), BG)
    minlat = min(p[0] for p in all_pts)
    maxlat = max(p[0] for p in all_pts)
    minlon = min(p[1] for p in all_pts)
    maxlon = max(p[1] for p in all_pts)
    z = fit_zoom((minlat, minlon, maxlat, maxlon), width - 2 * pad, height - 2 * pad,
                 max_zoom=max_zoom)
    x1, y1 = lonlat_to_px(maxlat, minlon, z)
    x2, y2 = lonlat_to_px(minlat, maxlon, z)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    ox, oy = cx - width / 2, cy - height / 2  # globale Pixel der linken oberen Ecke

    img = Image.new("RGB", (width, height), BG)
    tx0, ty0 = int(math.floor(ox / 256)), int(math.floor(oy / 256))
    tx1, ty1 = int(math.floor((ox + width) / 256)), int(math.floor((oy + height) / 256))
    n = 2 ** z
    jobs = {}
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            if 0 <= ty < n:
                jobs[(tx, ty)] = _pool.submit(tiles.get, z, tx % n, ty)
    missing = 0
    for (tx, ty), fut in jobs.items():
        try:
            res = fut.result(timeout=30)
        except Exception:  # noqa: BLE001
            res = None
        if not res:
            missing += 1
            continue
        try:
            tile = Image.open(io.BytesIO(res[0])).convert("RGB")
        except Exception:  # noqa: BLE001
            missing += 1
            continue
        img.paste(tile, (int(round(tx * 256 - ox)), int(round(ty * 256 - oy))))

    # Linien mit 2-facher Auflösung zeichnen und herunterrechnen (Kantenglättung)
    ss = 2
    overlay = Image.new("RGBA", (width * ss, height * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    mpp = 156543.03392 * math.cos(math.radians((minlat + maxlat) / 2)) / n
    lw = max(1, int(round(line_width * ss)))

    def proj(lat, lon):
        x, y = lonlat_to_px(lat, lon, z)
        return ((x - ox) * ss, (y - oy) * ss)

    for L in layers:
        cols = L["colors"]
        for i, seg in enumerate(L["segments"]):
            if len(seg) < 2:
                continue
            simp = simplify([(0, a, b) for a, b in seg], mpp * 0.6)
            xy = [proj(p[1], p[2]) for p in simp]
            col = hex_rgb(cols[i] if i < len(cols) else cols[0])
            # dezente helle Kontur für Lesbarkeit auf der Karte
            d.line(xy, fill=(255, 255, 255, 170), width=lw + 2 * ss, joint="curve")
            d.line(xy, fill=col + (255,), width=lw, joint="curve")
    if markers:
        r = max(4, int(line_width * 1.4)) * ss
        for L in layers:
            segs = [s for s in L["segments"] if s]
            if not segs:
                continue
            for pt, fill in ((segs[0][0], (12, 163, 12)), (segs[-1][-1], (11, 11, 11))):
                x, y = proj(*pt)
                d.ellipse((x - r, y - r, x + r, y + r), fill=fill + (255,), outline=(255, 255, 255, 255),
                          width=max(2, ss * 2))
    overlay = overlay.resize((width, height), Image.LANCZOS)
    img = img.convert("RGBA")
    img.alpha_composite(overlay)
    img = img.convert("RGB")

    if attribution:
        dr = ImageDraw.Draw(img)
        txt = "© OpenStreetMap contributors"
        f = _font(max(10, height // 55))
        bb = dr.textbbox((0, 0), txt, font=f)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        dr.rectangle((width - tw - 12, height - th - 10, width, height), fill=(255, 255, 255))
        dr.text((width - tw - 6, height - th - 7), txt, fill=(60, 60, 60), font=f)
    return img


def track_layer(track: dict, color: str, by_stage: bool) -> dict:
    """Wandelt einen Track (mit points + stage_breaks) in eine Render-Ebene."""
    pts = track["points"]
    b = [0] + list(track["stage_breaks"]) + [len(pts)]
    segs = [[(p[1], p[2]) for p in pts[b[i]:b[i + 1]]] for i in range(len(b) - 1)]
    if by_stage:
        colors = [palette_color(i) for i in range(len(segs))]
    else:
        colors = [color]
    return {"segments": segs, "colors": colors}


def to_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()
