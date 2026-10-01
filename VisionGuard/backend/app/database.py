"""SQLite storage for detection history and emergency events (standard library only)."""
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .danger import LEVELS, RANK

SCHEMA = """
CREATE TABLE IF NOT EXISTS detection_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    session_id TEXT NOT NULL,
    track_id INTEGER,
    label TEXT NOT NULL,
    confidence REAL NOT NULL,
    distance_m REAL NOT NULL,
    position TEXT NOT NULL,
    danger TEXT NOT NULL,
    score REAL NOT NULL,
    approaching INTEGER NOT NULL DEFAULT 0,
    message TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_history_created ON detection_history(created_at DESC);
CREATE TABLE IF NOT EXISTS emergency_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    session_id TEXT,
    note TEXT,
    last_level TEXT,
    last_message TEXT
);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path = config.DB_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def ok(self) -> bool:
        try:
            with self._conn() as c:
                c.execute("SELECT 1")
            return True
        except sqlite3.Error:
            return False

    # ---- history ----------------------------------------------------------
    def add_history(self, rows: list[dict]) -> int:
        if not rows:
            return 0
        with self._lock, self._conn() as c:
            c.executemany(
                "INSERT INTO detection_history (created_at, session_id, track_id, label, confidence,"
                " distance_m, position, danger, score, approaching, message)"
                " VALUES (:created_at,:session_id,:track_id,:label,:confidence,:distance_m,:position,"
                ":danger,:score,:approaching,:message)", rows)
            c.commit()
        return len(rows)

    def prune_history(self, max_rows: int = config.HISTORY_MAX_ROWS):
        with self._lock, self._conn() as c:
            c.execute("DELETE FROM detection_history WHERE id NOT IN "
                      "(SELECT id FROM detection_history ORDER BY id DESC LIMIT ?)", (max_rows,))
            c.commit()

    def list_history(self, limit=50, offset=0, level=None, label=None) -> list[dict]:
        q, args = "SELECT * FROM detection_history WHERE 1=1", []
        if level:
            q += " AND danger = ?"
            args.append(level)
        if label:
            q += " AND label = ?"
            args.append(label)
        q += " ORDER BY id DESC LIMIT ? OFFSET ?"
        args += [max(1, min(limit, 500)), max(0, offset)]
        with self._conn() as c:
            return [dict(r) for r in c.execute(q, args).fetchall()]

    def history_stats(self) -> dict:
        with self._conn() as c:
            total = c.execute("SELECT COUNT(*) n FROM detection_history").fetchone()["n"]
            by_level = {lvl: 0 for lvl in LEVELS}
            for r in c.execute("SELECT danger, COUNT(*) n FROM detection_history GROUP BY danger"):
                by_level[r["danger"]] = r["n"]
            top = [dict(r) for r in c.execute(
                "SELECT label, COUNT(*) n FROM detection_history GROUP BY label ORDER BY n DESC LIMIT 5")]
        return {"total": total, "by_level": by_level, "top_labels": top}

    def clear_history(self) -> int:
        with self._lock, self._conn() as c:
            n = c.execute("SELECT COUNT(*) n FROM detection_history").fetchone()["n"]
            c.execute("DELETE FROM detection_history")
            c.commit()
        return n

    # ---- emergency --------------------------------------------------------
    def add_emergency(self, session_id, note, last_level, last_message) -> dict:
        created = utc_now()
        with self._lock, self._conn() as c:
            cur = c.execute(
                "INSERT INTO emergency_events (created_at, session_id, note, last_level, last_message)"
                " VALUES (?,?,?,?,?)", (created, session_id, note, last_level, last_message))
            c.commit()
            return {"id": cur.lastrowid, "created_at": created}

    def list_emergency(self, limit=20) -> list[dict]:
        with self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM emergency_events ORDER BY id DESC LIMIT ?", (limit,))]


class HistoryLogger:
    """Writes detections to SQLite, throttled so a static object does not flood the table:
    one row per tracked object every `min_interval_s`, or immediately when its danger level changes."""

    def __init__(self, db: Database, min_interval_s: float = config.HISTORY_MIN_INTERVAL_S,
                 max_rows: int = config.HISTORY_MAX_ROWS):
        self.db, self.min_interval_s, self.max_rows = db, min_interval_s, max_rows
        self._last: dict[tuple, tuple] = {}
        self._inserted = 0

    def log(self, session_id: str, detections: list[dict], now: float) -> int:
        rows = []
        for d in detections:
            key = (session_id, d["track_id"])
            level = d["danger"]["level"]
            prev = self._last.get(key)
            if prev and prev[1] == level and now - prev[0] < self.min_interval_s:
                continue
            self._last[key] = (now, level)
            rows.append({
                "created_at": utc_now(), "session_id": session_id, "track_id": d["track_id"],
                "label": d["label"], "confidence": d["confidence"], "distance_m": d["distance_m"],
                "position": d["position"], "danger": level, "score": d["danger"]["score"],
                "approaching": int(d["approaching"]), "message": d["message"],
            })
        if len(self._last) > 2000:
            cutoff = now - 60
            self._last = {k: v for k, v in self._last.items() if v[0] > cutoff}
        n = self.db.add_history(rows)
        self._inserted += n
        if self._inserted >= 200:
            self._inserted = 0
            self.db.prune_history(self.max_rows)
        return n
