"""OpenStreetMap-Kachel-Proxy mit Festplatten-Cache.

* Kacheln werden unter /data/tiles/<hash der URL-Vorlage>/z/x/y gespeichert.
* Ist eine Kachel älter als ``max_age_days``, wird sie beim Server neu angefragt
  (bedingt per ETag/Last-Modified – unveränderte Kacheln kosten kaum Datenvolumen).
* Ist der Server nicht erreichbar (Funkloch), wird die vorhandene Kachel ausgeliefert.
* Der Cache wird regelmäßig auf ``max_mb`` begrenzt (älteste Nutzung zuerst entfernt).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import threading
import time
import urllib.error
import urllib.request

_LOG = logging.getLogger("trackview.tiles")


class TileCache:
    def __init__(self, root: str, user_agent: str):
        self.root = root
        self.ua = user_agent
        self.url = ""
        self.max_age = 7 * 86400
        self.max_bytes = 500 * 1024 * 1024
        self._locks: dict[str, threading.Lock] = {}
        self._glock = threading.Lock()
        self._offline_until = 0.0
        self.stats = {"hits": 0, "fetched": 0, "revalidated": 0, "stale_served": 0, "errors": 0}
        os.makedirs(root, exist_ok=True)

    def configure(self, url: str, max_age_days: float, max_mb: float) -> None:
        self.url = url.strip() or "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        self.max_age = max(0.0, float(max_age_days)) * 86400
        self.max_bytes = max(20.0, float(max_mb)) * 1024 * 1024

    @property
    def _dir(self) -> str:
        return os.path.join(self.root, hashlib.sha1(self.url.encode()).hexdigest()[:12])

    def _lock(self, key: str) -> threading.Lock:
        with self._glock:
            lk = self._locks.get(key)
            if lk is None:
                if len(self._locks) > 2000:
                    self._locks.clear()
                lk = self._locks[key] = threading.Lock()
            return lk

    @property
    def online(self) -> bool:
        return time.time() >= self._offline_until

    def get(self, z: int, x: int, y: int) -> tuple[bytes, str] | None:
        """Kachel holen (synchron, für Thread-Pool). None, wenn nicht verfügbar."""
        if not (0 <= z <= 19 and 0 <= x < 2 ** z and 0 <= y < 2 ** z):
            return None
        key = f"{z}/{x}/{y}"
        base = os.path.join(self._dir, str(z), str(x), str(y))
        data_path, meta_path = base + ".tile", base + ".json"
        with self._lock(key):
            meta = None
            if os.path.exists(data_path) and os.path.exists(meta_path):
                try:
                    with open(meta_path, encoding="utf-8") as f:
                        meta = json.load(f)
                except (OSError, ValueError):
                    meta = None
            if meta is not None:
                fresh = time.time() - meta.get("fetched", 0) < self.max_age
                if fresh or not self.online:
                    if not fresh:
                        self.stats["stale_served"] += 1
                    self.stats["hits"] += 1
                    return self._read(data_path, meta)
            elif not self.online:
                return None

            req = urllib.request.Request(
                self.url.replace("{z}", str(z)).replace("{x}", str(x)).replace("{y}", str(y)),
                headers={"User-Agent": self.ua})
            if meta:
                if meta.get("etag"):
                    req.add_header("If-None-Match", meta["etag"])
                if meta.get("lastmod"):
                    req.add_header("If-Modified-Since", meta["lastmod"])
            try:
                with urllib.request.urlopen(req, timeout=8) as resp:
                    body = resp.read()
                    ctype = resp.headers.get("Content-Type", "image/png")
                    if not ctype.startswith("image/"):
                        raise ValueError(f"unexpected content type {ctype}")
                    os.makedirs(os.path.dirname(data_path), exist_ok=True)
                    tmp = data_path + ".tmp"
                    with open(tmp, "wb") as f:
                        f.write(body)
                    os.replace(tmp, data_path)
                    meta = {"fetched": time.time(), "etag": resp.headers.get("ETag"),
                            "lastmod": resp.headers.get("Last-Modified"), "ctype": ctype}
                    self._write_meta(meta_path, meta)
                    self.stats["fetched"] += 1
                    return body, ctype
            except urllib.error.HTTPError as e:
                if e.code == 304 and meta:
                    meta["fetched"] = time.time()
                    self._write_meta(meta_path, meta)
                    self.stats["revalidated"] += 1
                    return self._read(data_path, meta)
                self.stats["errors"] += 1
                _LOG.debug("Tile %s: HTTP %s", key, e.code)
                if e.code in (403, 429):
                    _LOG.warning("Tile server refused request (HTTP %s) – backing off", e.code)
                    self._offline_until = time.time() + 60
            except Exception as e:  # noqa: BLE001 – Netzfehler jeder Art
                self.stats["errors"] += 1
                self._offline_until = time.time() + 30
                _LOG.debug("Tile %s: %s", key, e)
            if meta is not None:
                self.stats["stale_served"] += 1
                return self._read(data_path, meta)
            return None

    def _read(self, path: str, meta: dict):
        try:
            os.utime(path, None)  # für LRU-Bereinigung
            with open(path, "rb") as f:
                return f.read(), meta.get("ctype", "image/png")
        except OSError:
            return None

    @staticmethod
    def _write_meta(path: str, meta: dict) -> None:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(meta, f)
        os.replace(tmp, path)

    # ----------------------------------------------------------- Verwaltung
    def usage(self) -> tuple[int, int]:
        total = count = 0
        for dirpath, _, files in os.walk(self.root):
            for fn in files:
                try:
                    total += os.path.getsize(os.path.join(dirpath, fn))
                except OSError:
                    pass
                if fn.endswith(".tile"):
                    count += 1
        return total, count

    def cleanup(self) -> int:
        """Begrenzt die Cache-Größe und entfernt Caches alter Kachel-URLs."""
        removed = 0
        current = os.path.basename(self._dir)
        for name in os.listdir(self.root):
            p = os.path.join(self.root, name)
            if os.path.isdir(p) and name != current:
                shutil.rmtree(p, ignore_errors=True)
                removed += 1
        files = []
        total = 0
        for dirpath, _, fns in os.walk(self.root):
            for fn in fns:
                if fn.endswith(".tile"):
                    p = os.path.join(dirpath, fn)
                    try:
                        st = os.stat(p)
                    except OSError:
                        continue
                    files.append((st.st_mtime, p, st.st_size))
                    total += st.st_size
        if total <= self.max_bytes:
            return removed
        files.sort()
        target = self.max_bytes * 0.85
        for _, p, size in files:
            if total <= target:
                break
            for q in (p, p[:-5] + ".json"):
                try:
                    os.remove(q)
                except OSError:
                    pass
            total -= size
            removed += 1
        _LOG.info("Tile cache trimmed, %s files removed", removed)
        return removed

    def clear(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)
        os.makedirs(self.root, exist_ok=True)
