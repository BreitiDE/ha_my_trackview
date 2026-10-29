"""SQLite-Datenhaltung für My TrackView."""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
import zlib
from typing import Any, Iterable

_LOG = logging.getLogger("trackview.db")

SCHEMA_VERSION = 1

DEFAULT_SETTINGS: dict[str, Any] = {
    "gps_file": "/config/gpsdata.log",
    "home_lat": None,
    "home_lon": None,
    "home_radius_m": 200,
    "leave_points": 5,
    "stage_gap_min": 30,
    "min_trip_km": 1.0,
    "max_speed_kmh": 250,
    "jump_km": 5.0,
    "file_timezone": "utc",          # utc | local
    "import_interval_min": 5,        # 0 = nur manuell
    "distance_unit": "km",           # km | mi
    "default_color": "#ce6c00",
    "language": "auto",              # auto | de | en
    "tile_url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    "tile_cache_days": 7,
    "tile_cache_max_mb": 500,
    "page_size": 25,
}

# Einstellungen, deren Änderung die Erkennung beeinflusst
DETECTION_KEYS = ("home_lat", "home_lon", "home_radius_m", "leave_points", "stage_gap_min",
                  "min_trip_km", "max_speed_kmh", "jump_km", "file_timezone")


def pack_points(points: list) -> bytes:
    return zlib.compress(json.dumps(points, separators=(",", ":")).encode(), 6)


def unpack_points(blob: bytes | None) -> list:
    if not blob:
        return []
    return json.loads(zlib.decompress(blob).decode())


class Database:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self._migrate()

    # ------------------------------------------------------------------ setup
    def _migrate(self) -> None:
        with self._lock:
            c = self.conn
            c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
            row = c.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
            ver = int(row[0]) if row else 0
            if ver < 1:
                c.executescript(
                    """
                    BEGIN;
                    CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
                    CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT);
                    CREATE TABLE IF NOT EXISTS tracks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        status TEXT NOT NULL,            -- trip | running | unassigned
                        reason TEXT,                      -- start_outside | gap | manual
                        deleted INTEGER NOT NULL DEFAULT 0,
                        deleted_at INTEGER,
                        edited INTEGER NOT NULL DEFAULT 0,
                        start_ts INTEGER NOT NULL,
                        end_ts INTEGER NOT NULL,
                        duration_s INTEGER NOT NULL,
                        driving_s INTEGER NOT NULL,
                        distance_m REAL NOT NULL,
                        stage_count INTEGER NOT NULL,
                        stage_breaks TEXT NOT NULL,
                        point_count INTEGER NOT NULL,
                        min_lat REAL, min_lon REAL, max_lat REAL, max_lon REAL,
                        color TEXT,
                        name TEXT,
                        points BLOB NOT NULL,
                        created_at INTEGER NOT NULL,
                        updated_at INTEGER NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS ix_tracks_start ON tracks(start_ts);
                    CREATE INDEX IF NOT EXISTS ix_tracks_status ON tracks(deleted, status);
                    CREATE TABLE IF NOT EXISTS track_keys (
                        key INTEGER PRIMARY KEY,
                        track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE
                    );
                    CREATE INDEX IF NOT EXISTS ix_keys_track ON track_keys(track_id);
                    INSERT OR REPLACE INTO meta(key, value) VALUES('schema', '1');
                    COMMIT;
                    """
                )
                _LOG.info("Database schema created (v1)")

    # -------------------------------------------------------------- settings
    def get_settings(self) -> dict[str, Any]:
        with self._lock:
            rows = self.conn.execute("SELECT key, value FROM settings").fetchall()
        s = dict(DEFAULT_SETTINGS)
        for r in rows:
            try:
                s[r["key"]] = json.loads(r["value"])
            except (ValueError, TypeError):
                pass
        return s

    def save_settings(self, values: dict[str, Any]) -> None:
        with self._lock:
            c = self.conn
            c.execute("BEGIN")
            try:
                for k, v in values.items():
                    if k in DEFAULT_SETTINGS:
                        c.execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)",
                                  (k, json.dumps(v)))
                c.execute("COMMIT")
            except Exception:
                c.execute("ROLLBACK")
                raise

    # ----------------------------------------------------------------- state
    def get_state(self) -> dict[str, Any]:
        with self._lock:
            rows = self.conn.execute("SELECT key, value FROM state").fetchall()
        out = {}
        for r in rows:
            try:
                out[r["key"]] = json.loads(r["value"])
            except (ValueError, TypeError):
                pass
        return out

    def set_state(self, values: dict[str, Any], cursor: sqlite3.Connection | None = None) -> None:
        c = cursor or self.conn
        with self._lock:
            for k, v in values.items():
                c.execute("INSERT OR REPLACE INTO state(key, value) VALUES(?, ?)", (k, json.dumps(v)))

    # ---------------------------------------------------------------- tracks
    LIST_COLS = ("id, status, reason, deleted, deleted_at, edited, start_ts, end_ts, duration_s, "
                 "driving_s, distance_m, stage_count, point_count, min_lat, min_lon, max_lat, "
                 "max_lon, color, name, updated_at")

    def list_tracks(self, *, scope: str, sort: str = "start", order: str = "desc",
                    limit: int | None = None, offset: int = 0) -> tuple[list[dict], int]:
        where = {
            "trips": "deleted=0 AND status IN ('trip','running')",
            "unassigned": "deleted=0 AND status='unassigned'",
            "trash": "deleted=1",
        }[scope]
        col = {"start": "start_ts", "duration": "duration_s", "distance": "distance_m",
               "driving": "driving_s", "deleted": "deleted_at"}.get(sort, "start_ts")
        direction = "ASC" if order == "asc" else "DESC"
        sql = f"SELECT {self.LIST_COLS} FROM tracks WHERE {where} ORDER BY {col} {direction}, id {direction}"
        params: list = []
        if limit:
            sql += " LIMIT ? OFFSET ?"
            params = [limit, offset]
        with self._lock:
            total = self.conn.execute(f"SELECT COUNT(*) FROM tracks WHERE {where}").fetchone()[0]
            rows = [dict(r) for r in self.conn.execute(sql, params).fetchall()]
        return rows, total

    def get_track(self, track_id: int, with_points: bool = True) -> dict | None:
        cols = self.LIST_COLS + ", stage_breaks" + (", points" if with_points else "")
        with self._lock:
            r = self.conn.execute(f"SELECT {cols} FROM tracks WHERE id=?", (track_id,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["stage_breaks"] = json.loads(d["stage_breaks"] or "[]")
        if with_points:
            d["points"] = unpack_points(d["points"])
        return d

    def neighbours(self, track_id: int) -> tuple[int | None, int | None]:
        """Chronologisch vorheriger/nächster nicht gelöschter Eintrag."""
        with self._lock:
            r = self.conn.execute("SELECT start_ts FROM tracks WHERE id=?", (track_id,)).fetchone()
            if not r:
                return None, None
            ts = r[0]
            p = self.conn.execute(
                "SELECT id FROM tracks WHERE deleted=0 AND (start_ts<? OR (start_ts=? AND id<?)) "
                "ORDER BY start_ts DESC, id DESC LIMIT 1", (ts, ts, track_id)).fetchone()
            n = self.conn.execute(
                "SELECT id FROM tracks WHERE deleted=0 AND (start_ts>? OR (start_ts=? AND id>?)) "
                "ORDER BY start_ts ASC, id ASC LIMIT 1", (ts, ts, track_id)).fetchone()
        return (p[0] if p else None), (n[0] if n else None)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            c = self.conn
            t = c.execute(
                "SELECT COUNT(*), COALESCE(SUM(distance_m),0), COALESCE(SUM(driving_s),0), "
                "COALESCE(SUM(duration_s),0), COALESCE(SUM(stage_count),0), MAX(start_ts) "
                "FROM tracks WHERE deleted=0 AND status IN ('trip','running')").fetchone()
            running = c.execute(
                "SELECT id, start_ts, distance_m FROM tracks WHERE deleted=0 AND status='running' "
                "ORDER BY start_ts DESC LIMIT 1").fetchone()
            unassigned = c.execute(
                "SELECT COUNT(*) FROM tracks WHERE deleted=0 AND status='unassigned'").fetchone()[0]
            trash = c.execute("SELECT COUNT(*) FROM tracks WHERE deleted=1").fetchone()[0]
        return {
            "trips": t[0], "distance_m": t[1], "driving_s": t[2], "duration_s": t[3],
            "stages": t[4], "last_start": t[5],
            "running": dict(running) if running else None,
            "unassigned": unassigned, "trash": trash,
            "db_size": os.path.getsize(self.path) if os.path.exists(self.path) else 0,
        }

    # ------------------------------------------------------------- mutations
    def transaction(self):
        return _Tx(self)

    def insert_track(self, c, cand: dict, *, edited: int = 0, color=None, name=None,
                     deleted: int = 0, deleted_at=None, keys: Iterable[int] = ()) -> int:
        now = int(time.time())
        cur = c.execute(
            "INSERT INTO tracks(status, reason, deleted, deleted_at, edited, start_ts, end_ts, "
            "duration_s, driving_s, distance_m, stage_count, stage_breaks, point_count, min_lat, "
            "min_lon, max_lat, max_lon, color, name, points, created_at, updated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (cand["status"], cand.get("reason"), deleted, deleted_at, edited, cand["start_ts"],
             cand["end_ts"], cand["duration_s"], cand["driving_s"], cand["distance_m"],
             cand["stage_count"], json.dumps(cand["stage_breaks"]), cand["point_count"],
             *cand["bbox"], color, name, pack_points(cand["points"]), now, now))
        tid = cur.lastrowid
        for k in keys:
            c.execute("INSERT OR REPLACE INTO track_keys(key, track_id) VALUES(?, ?)", (int(k), tid))
        return tid

    def update_track_geometry(self, c, tid: int, cand: dict, *, status=None, reason=None,
                              edited=None) -> None:
        c.execute(
            "UPDATE tracks SET status=?, reason=?, edited=COALESCE(?, edited), start_ts=?, end_ts=?, "
            "duration_s=?, driving_s=?, distance_m=?, stage_count=?, stage_breaks=?, point_count=?, "
            "min_lat=?, min_lon=?, max_lat=?, max_lon=?, points=?, updated_at=? WHERE id=?",
            (status or cand["status"], reason if reason is not None else cand.get("reason"), edited,
             cand["start_ts"], cand["end_ts"], cand["duration_s"], cand["driving_s"],
             cand["distance_m"], cand["stage_count"], json.dumps(cand["stage_breaks"]),
             cand["point_count"], *cand["bbox"], pack_points(cand["points"]), int(time.time()), tid))

    def set_fields(self, tid: int, **fields) -> None:
        allowed = {"color", "name", "deleted", "deleted_at", "status", "reason", "edited"}
        sets, vals = [], []
        for k, v in fields.items():
            if k in allowed:
                sets.append(f"{k}=?")
                vals.append(v)
        if not sets:
            return
        sets.append("updated_at=?")
        vals.append(int(time.time()))
        with self._lock:
            self.conn.execute(f"UPDATE tracks SET {', '.join(sets)} WHERE id=?", (*vals, tid))

    def purge(self, ids: list[int]) -> int:
        with self._lock:
            c = self.conn
            c.execute("BEGIN")
            try:
                n = 0
                for tid in ids:
                    n += c.execute("DELETE FROM tracks WHERE id=? AND deleted=1", (tid,)).rowcount
                c.execute("COMMIT")
            except Exception:
                c.execute("ROLLBACK")
                raise
        return n

    def backup(self, target: str) -> None:
        with self._lock:
            dst = sqlite3.connect(target)
            try:
                self.conn.backup(dst)
            finally:
                dst.close()

    def vacuum(self) -> None:
        with self._lock:
            self.conn.execute("VACUUM")


class _Tx:
    def __init__(self, db: Database):
        self.db = db

    def __enter__(self):
        self.db._lock.acquire()
        self.db.conn.execute("BEGIN IMMEDIATE")
        return self.db.conn

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self.db.conn.execute("COMMIT")
            else:
                self.db.conn.execute("ROLLBACK")
        finally:
            self.db._lock.release()
        return False
