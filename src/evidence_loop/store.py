from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .config import LoopError


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def workspace_lock(root: Path):
    """Keep the lock inode in place so waiting processes lock the same file."""
    path = root / ".evidence-loop.lock"
    with path.open("a+b") as handle:
        if path.stat().st_size == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        try:
            if __import__("os").name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise LoopError("another runner owns this workspace") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if __import__("os").name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class Store:
    def __init__(self, root: Path):
        self.connection = sqlite3.connect(root / "ledger.sqlite3", timeout=10)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS attempts (
                sequence INTEGER PRIMARY KEY,
                task_id TEXT NOT NULL,
                attempt INTEGER NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('running','succeeded','failed','interrupted')),
                decision TEXT,
                score REAL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                duration REAL NOT NULL DEFAULT 0,
                reason TEXT,
                evidence TEXT NOT NULL DEFAULT '[]',
                UNIQUE(task_id, attempt)
            );
        """)

    def close(self):
        self.connection.close()

    def bind(self, fingerprint: str):
        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO metadata VALUES ('config_hash', ?)", (fingerprint,)
            )
            stored = self.connection.execute(
                "SELECT value FROM metadata WHERE key='config_hash'"
            ).fetchone()[0]
            if stored != fingerprint:
                raise LoopError("configuration changed; use a new workspace for a new protocol")

    def recover(self):
        with self.connection:
            self.connection.execute(
                """UPDATE attempts SET state='interrupted', decision='reject', finished_at=?,
                duration=MAX(duration, ? - (julianday(started_at)-2440587.5)*86400.0),
                reason='Runner exited before committing a result; explicit retry required.'
                WHERE state='running'""",
                (now(), int(datetime.now(timezone.utc).timestamp())),
            )

    def rows(self) -> list[dict]:
        rows = [
            dict(row) for row in self.connection.execute("SELECT * FROM attempts ORDER BY sequence")
        ]
        for row in rows:
            row["evidence"] = json.loads(row["evidence"])
        return rows

    def start(self, task_id: str) -> dict:
        with self.connection:
            attempt = self.connection.execute(
                "SELECT COALESCE(MAX(attempt),0)+1 FROM attempts WHERE task_id=?", (task_id,)
            ).fetchone()[0]
            cursor = self.connection.execute(
                "INSERT INTO attempts(task_id,attempt,state,started_at) VALUES (?,?,'running',?)",
                (task_id, attempt, now()),
            )
        return {"sequence": cursor.lastrowid, "attempt": attempt}

    def finish(self, sequence, state, decision, score, duration, reason, evidence):
        with self.connection:
            cursor = self.connection.execute(
                """UPDATE attempts SET state=?,decision=?,score=?,finished_at=?,duration=?,
                reason=?,evidence=? WHERE sequence=? AND state='running'""",
                (
                    state,
                    decision,
                    score,
                    now(),
                    duration,
                    reason,
                    json.dumps(evidence, allow_nan=False),
                    sequence,
                ),
            )
            if cursor.rowcount != 1:
                raise LoopError("attempt is no longer running")
