"""SQLite persistence for review runs, feedback, and metrics."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.config import settings


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a connection to the SQLite database."""
    path = db_path or settings.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


_DB_INITIALIZED = False


def init_db(db_path: Path | None = None) -> None:
    """Create tables if they don't exist (called once at startup)."""
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        return
    with db_connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                source TEXT NOT NULL,
                model_name TEXT NOT NULL,
                prompt_version TEXT NOT NULL,
                diff_preview TEXT NOT NULL,
                output TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES runs(id)
            )
            """
        )
        conn.commit()
    _DB_INITIALIZED = True


def save_run(
    source: str,
    model_name: str,
    prompt_version: str,
    diff_text: str,
    output: str,
) -> str:
    """Save a review run and return the run ID."""
    init_db()
    run_id = uuid.uuid4().hex[:12]
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO runs (id, created_at, source, model_name, prompt_version, diff_preview, output)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, _now_iso(), source, model_name, prompt_version, diff_text[:500], output),
        )
        conn.commit()
    return run_id


def load_history(limit: int = 15) -> list[dict]:
    """Load recent review runs."""
    init_db()
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]


def get_run(run_id: str) -> dict | None:
    """Load a single run by ID."""
    init_db()
    with db_connect() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    return dict(row) if row else None


def save_feedback(run_id: str, rating: int, comment: str = "") -> dict:
    """Save user feedback for a run."""
    from src.models import AppError

    init_db()
    if not get_run(run_id):
        raise AppError("Run not found.", status_code=404)
    if rating < 1 or rating > 5:
        raise AppError("Rating must be between 1 and 5.")
    feedback_id = uuid.uuid4().hex[:12]
    with db_connect() as conn:
        conn.execute(
            "INSERT INTO feedback (id, run_id, rating, comment, created_at) VALUES (?, ?, ?, ?, ?)",
            (feedback_id, run_id, rating, comment[:1000], _now_iso()),
        )
        conn.commit()
    return {"id": feedback_id, "run_id": run_id, "rating": rating, "comment": comment[:1000]}


def metrics_summary() -> dict:
    """Return aggregate metrics."""
    init_db()
    with db_connect() as conn:
        run_count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        feedback_count = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        avg_rating = conn.execute("SELECT AVG(rating) FROM feedback").fetchone()[0]
    return {
        "runs": run_count,
        "feedback": feedback_count,
        "average_rating": round(avg_rating or 0, 2),
    }
