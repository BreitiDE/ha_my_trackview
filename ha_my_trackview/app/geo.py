"""Geometrie-Hilfsfunktionen: Distanz, Vereinfachung, Projektion."""
from __future__ import annotations

import math

EARTH_R = 6371008.8  # mittlerer Erdradius in Metern


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distanz in Metern zwischen zwei WGS84-Koordinaten."""
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R * math.asin(min(1.0, math.sqrt(a)))


def simplify(points: list, tolerance_m: float) -> list:
    """Douglas-Peucker (iterativ) auf Punktlisten [t, lat, lon, ...].

    Arbeitet in einer lokalen äquirektangulären Projektion – für Track-Darstellung
    völlig ausreichend. Erster und letzter Punkt bleiben immer erhalten.
    """
    n = len(points)
    if n <= 2 or tolerance_m <= 0:
        return list(points)
    lat0 = math.radians(sum(p[1] for p in points[:: max(1, n // 50)]) / len(points[:: max(1, n // 50)]))
    kx = math.cos(lat0) * EARTH_R * math.pi / 180.0
    ky = EARTH_R * math.pi / 180.0
    xs = [p[2] * kx for p in points]
    ys = [p[1] * ky for p in points]
    keep = bytearray(n)
    keep[0] = keep[n - 1] = 1
    tol2 = tolerance_m * tolerance_m
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        ax, ay, bx, by = xs[a], ys[a], xs[b], ys[b]
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy
        best, idx = -1.0, -1
        for i in range(a + 1, b):
            px, py = xs[i] - ax, ys[i] - ay
            if seg2 == 0:
                d2 = px * px + py * py
            else:
                t = (px * dx + py * dy) / seg2
                if t < 0:
                    t = 0
                elif t > 1:
                    t = 1
                ex, ey = px - t * dx, py - t * dy
                d2 = ex * ex + ey * ey
            if d2 > best:
                best, idx = d2, i
        if best > tol2:
            keep[idx] = 1
            stack.append((a, idx))
            stack.append((idx, b))
    return [p for i, p in enumerate(points) if keep[i]]


# ---- Web-Mercator (Slippy-Map-Kacheln) --------------------------------------

def lonlat_to_px(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    """Globale Pixelkoordinate bei gegebener Zoomstufe (256-px-Kacheln)."""
    lat = max(-85.05112878, min(85.05112878, lat))
    scale = 256 * (2 ** zoom)
    x = (lon + 180.0) / 360.0 * scale
    s = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * scale
    return x, y


def fit_zoom(bbox: tuple[float, float, float, float], width: int, height: int,
             max_zoom: int = 17, min_zoom: int = 1) -> int:
    """Höchste Zoomstufe, bei der die Bounding-Box (minlat, minlon, maxlat, maxlon) passt."""
    minlat, minlon, maxlat, maxlon = bbox
    for z in range(max_zoom, min_zoom - 1, -1):
        x1, y1 = lonlat_to_px(maxlat, minlon, z)
        x2, y2 = lonlat_to_px(minlat, maxlon, z)
        if (x2 - x1) <= width and (y2 - y1) <= height:
            return z
    return min_zoom
