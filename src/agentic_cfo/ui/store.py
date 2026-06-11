"""SQLite-backed persistence for the platform UI.

Replaces ad-hoc folder scanning with a durable metadata store for background
jobs (and a small key/value table for UI settings). The database lives at
``<repo>/.agentic_cfo/platform.db`` by default and is safe to delete; it holds
only operational metadata, never primary research artifacts.

The module is pure Python (no Streamlit) so it is fully unit-testable and can be
driven from the job manager running on a background thread. SQLite connections
are opened per-call with WAL mode so concurrent reader/writer access from the UI
thread and a worker thread is safe.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

JOB_STATUSES = ("queued", "running", "succeeded", "failed", "cancelled")
_TERMINAL = {"succeeded", "failed", "cancelled"}


def default_db_path(repo_root: Path) -> Path:
    return repo_root / ".agentic_cfo" / "platform.db"


@dataclass(frozen=True)
class JobRecord:
    id: str
    kind: str
    status: str
    params: dict[str, Any]
    progress: int
    total: int
    message: str
    result: dict[str, Any]
    error: str
    created_at: float
    started_at: float | None
    finished_at: float | None

    @property
    def is_terminal(self) -> bool:
        return self.status in _TERMINAL

    @property
    def fraction(self) -> float:
        return (self.progress / self.total) if self.total else 0.0

    def to_dict(self) -> dict[str, Any]:
        data = {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "params": self.params,
            "progress": self.progress,
            "total": self.total,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "fraction": self.fraction,
        }
        return data


class PlatformStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    progress INTEGER NOT NULL DEFAULT 0,
                    total INTEGER NOT NULL DEFAULT 0,
                    message TEXT NOT NULL DEFAULT '',
                    result_json TEXT NOT NULL DEFAULT '{}',
                    error TEXT NOT NULL DEFAULT '',
                    created_at REAL NOT NULL,
                    started_at REAL,
                    finished_at REAL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS review_samples (
                    blinded_id TEXT PRIMARY KEY,
                    artifact_id TEXT NOT NULL,
                    system TEXT NOT NULL,
                    condition TEXT NOT NULL,
                    release_action TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reviews (
                    review_id TEXT PRIMARY KEY,
                    blinded_id TEXT NOT NULL,
                    artifact_id TEXT NOT NULL,
                    reviewer_id TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    rationale TEXT NOT NULL DEFAULT '',
                    created_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_reviews_blinded_reviewer "
                "ON reviews (blinded_id, reviewer_id)"
            )

    # ----- jobs -----------------------------------------------------------

    def create_job(self, *, job_id: str, kind: str, params: dict[str, Any]) -> JobRecord:
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO jobs (id, kind, status, params_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (job_id, kind, "queued", json.dumps(params, default=str), now),
            )
        return self.get_job(job_id)  # type: ignore[return-value]

    def update_job(self, job_id: str, **fields: Any) -> None:
        if not fields:
            return
        columns = []
        values: list[Any] = []
        for key, value in fields.items():
            if key == "params":
                key, value = "params_json", json.dumps(value, default=str)
            elif key == "result":
                key, value = "result_json", json.dumps(value, default=str)
            columns.append(f"{key} = ?")
            values.append(value)
        values.append(job_id)
        with self._connect() as conn:
            conn.execute(f"UPDATE jobs SET {', '.join(columns)} WHERE id = ?", values)

    def mark_started(self, job_id: str, *, total: int) -> None:
        self.update_job(job_id, status="running", total=total, started_at=time.time(), message="running")

    def mark_progress(self, job_id: str, *, progress: int, total: int) -> None:
        self.update_job(job_id, progress=progress, total=total)

    def mark_finished(
        self,
        job_id: str,
        *,
        status: str,
        result: dict[str, Any] | None = None,
        error: str = "",
        message: str = "",
    ) -> None:
        if status not in _TERMINAL:
            raise ValueError(f"Not a terminal status: {status}")
        self.update_job(
            job_id,
            status=status,
            result=result or {},
            error=error,
            message=message or status,
            finished_at=time.time(),
        )

    def get_job(self, job_id: str) -> JobRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return _row_to_job(row) if row else None

    def list_jobs(self, *, limit: int = 100) -> tuple[JobRecord, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return tuple(_row_to_job(r) for r in rows)

    def clear_terminal_jobs(self) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM jobs WHERE status IN ('succeeded','failed','cancelled')"
            )
            return cur.rowcount

    # ----- settings -------------------------------------------------------

    def set_setting(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def get_setting(self, key: str, default: str = "") -> str:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    # ----- review samples -------------------------------------------------

    def replace_review_samples(self, samples: list[dict[str, Any]]) -> int:
        """Replace the current blinded review assignment with a new sample set."""
        now = time.time()
        with self._connect() as conn:
            conn.execute("DELETE FROM review_samples")
            conn.executemany(
                "INSERT INTO review_samples "
                "(blinded_id, artifact_id, system, condition, release_action, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        s["blinded_id"],
                        s["artifact_id"],
                        s["system"],
                        s["condition"],
                        s["release_action"],
                        now,
                    )
                    for s in samples
                ],
            )
        return len(samples)

    def list_review_samples(self) -> tuple[dict[str, Any], ...]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM review_samples ORDER BY blinded_id"
            ).fetchall()
        return tuple(dict(r) for r in rows)

    def clear_review_samples(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM review_samples")

    # ----- reviews --------------------------------------------------------

    def record_review(
        self,
        *,
        review_id: str,
        blinded_id: str,
        artifact_id: str,
        reviewer_id: str,
        rating: int,
        rationale: str = "",
    ) -> None:
        """Insert or update a reviewer's rating for one blinded item."""
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO reviews "
                "(review_id, blinded_id, artifact_id, reviewer_id, rating, rationale, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(blinded_id, reviewer_id) DO UPDATE SET "
                "rating = excluded.rating, rationale = excluded.rationale, "
                "created_at = excluded.created_at",
                (review_id, blinded_id, artifact_id, reviewer_id, int(rating), rationale, time.time()),
            )

    def list_reviews(self) -> tuple[dict[str, Any], ...]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM reviews ORDER BY created_at").fetchall()
        return tuple(dict(r) for r in rows)

    def get_review(self, *, blinded_id: str, reviewer_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM reviews WHERE blinded_id = ? AND reviewer_id = ?",
                (blinded_id, reviewer_id),
            ).fetchone()
        return dict(row) if row else None

    def clear_reviews(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM reviews")


def _row_to_job(row: sqlite3.Row) -> JobRecord:
    return JobRecord(
        id=row["id"],
        kind=row["kind"],
        status=row["status"],
        params=json.loads(row["params_json"] or "{}"),
        progress=int(row["progress"]),
        total=int(row["total"]),
        message=row["message"] or "",
        result=json.loads(row["result_json"] or "{}"),
        error=row["error"] or "",
        created_at=float(row["created_at"]),
        started_at=float(row["started_at"]) if row["started_at"] is not None else None,
        finished_at=float(row["finished_at"]) if row["finished_at"] is not None else None,
    )
