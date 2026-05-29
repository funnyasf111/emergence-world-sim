"""SQLite persistence for world state, memories, and metrics history."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from config import DB_PATH


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Persistence:
    def __init__(self, path: str = DB_PATH) -> None:
        self.path = Path(path)
        self._init_schema()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agent_state (
                    agent_id TEXT PRIMARY KEY,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    energy REAL NOT NULL,
                    credits INTEGER NOT NULL,
                    inventory INTEGER NOT NULL DEFAULT 0,
                    goals_json TEXT NOT NULL,
                    alive INTEGER NOT NULL DEFAULT 1,
                    updated_turn INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS agent_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    turn INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS relationships (
                    src TEXT NOT NULL,
                    dst TEXT NOT NULL,
                    weight REAL NOT NULL,
                    updated_turn INTEGER NOT NULL,
                    PRIMARY KEY (src, dst)
                );
                CREATE TABLE IF NOT EXISTS constitution (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    text TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    updated_turn INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS proposals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proposer TEXT NOT NULL,
                    amendment TEXT NOT NULL,
                    created_turn INTEGER NOT NULL,
                    closes_turn INTEGER NOT NULL,
                    yes_votes INTEGER NOT NULL DEFAULT 0,
                    no_votes INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'open'
                );
                CREATE TABLE IF NOT EXISTS votes (
                    proposal_id INTEGER NOT NULL,
                    voter TEXT NOT NULL,
                    vote TEXT NOT NULL,
                    turn INTEGER NOT NULL,
                    PRIMARY KEY (proposal_id, voter)
                );
                CREATE TABLE IF NOT EXISTS event_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    turn INTEGER NOT NULL,
                    agent_id TEXT,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS metrics_history (
                    turn INTEGER PRIMARY KEY,
                    metrics_json TEXT NOT NULL
                );
                """
            )
            row = conn.execute("SELECT value FROM meta WHERE key='turn'").fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO meta(key, value) VALUES ('turn', '0'), ('seed', '42')"
                )
            if conn.execute("SELECT 1 FROM constitution WHERE id=1").fetchone() is None:
                conn.execute(
                    """
                    INSERT INTO constitution(id, text, version, updated_turn)
                    VALUES (1, ?, 1, 0)
                    """,
                    (
                        "We cooperate peacefully, respect property, vote on amendments, "
                        "and share public knowledge at the Commons.",
                    ),
                )

    def get_turn(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key='turn'").fetchone()
            return int(row["value"]) if row else 0

    def set_turn(self, turn: int) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO meta(key,value) VALUES('turn',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(turn),),
            )

    def log_event(
        self,
        turn: int,
        event_type: str,
        payload: Dict[str, Any],
        agent_id: Optional[str] = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO event_log(turn, agent_id, event_type, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (turn, agent_id, event_type, json.dumps(payload), _utc_now()),
            )

    def add_memory(
        self, agent_id: str, turn: int, category: str, content: str
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_memory(agent_id, turn, category, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (agent_id, turn, category, content, _utc_now()),
            )

    def get_memories(self, agent_id: str, limit: int = 20) -> List[Dict[str, str]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT turn, category, content FROM agent_memory
                WHERE agent_id=? ORDER BY id DESC LIMIT ?
                """,
                (agent_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def save_agent(
        self,
        agent_id: str,
        x: int,
        y: int,
        energy: float,
        credits: int,
        inventory: int,
        goals: List[str],
        alive: bool,
        turn: int,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_state(agent_id,x,y,energy,credits,inventory,goals_json,alive,updated_turn)
                VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    x=excluded.x, y=excluded.y, energy=excluded.energy,
                    credits=excluded.credits, inventory=excluded.inventory,
                    goals_json=excluded.goals_json, alive=excluded.alive,
                    updated_turn=excluded.updated_turn
                """,
                (
                    agent_id,
                    x,
                    y,
                    energy,
                    credits,
                    inventory,
                    json.dumps(goals),
                    1 if alive else 0,
                    turn,
                ),
            )

    def save_relationship(self, src: str, dst: str, weight: float, turn: int) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO relationships(src,dst,weight,updated_turn)
                VALUES (?,?,?,?)
                ON CONFLICT(src,dst) DO UPDATE SET weight=excluded.weight, updated_turn=excluded.updated_turn
                """,
                (src, dst, weight, turn),
            )

    def load_relationships(self) -> List[tuple]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT src, dst, weight FROM relationships"
            ).fetchall()
        return [(r["src"], r["dst"], r["weight"]) for r in rows]

    def save_constitution(self, text: str, version: int, turn: int) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE constitution SET text=?, version=?, updated_turn=? WHERE id=1",
                (text, version, turn),
            )

    def get_constitution(self) -> tuple:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT text, version, updated_turn FROM constitution WHERE id=1"
            ).fetchone()
        return row["text"], row["version"], row["updated_turn"]

    def save_metrics_snapshot(self, turn: int, metrics: Dict[str, float]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO metrics_history(turn, metrics_json) VALUES (?,?)
                ON CONFLICT(turn) DO UPDATE SET metrics_json=excluded.metrics_json
                """,
                (turn, json.dumps(metrics)),
            )
