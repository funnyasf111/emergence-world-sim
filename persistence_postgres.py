"""PostgreSQL persistence — mirrors SQLite API for long-horizon runs."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional

from config import SEED_CONSTITUTION

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None  # type: ignore


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PostgresPersistence:
    """Drop-in replacement for Persistence when DATABASE_URL is set."""

    def __init__(self, database_url: str) -> None:
        if psycopg is None:
            raise ImportError("Install psycopg: pip install 'psycopg[binary]'")
        self.database_url = database_url
        self.path = None  # compat with Simulation.reset
        self._init_schema()

    @contextmanager
    def connect(self) -> Iterator[Any]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agent_state (
                    agent_id TEXT PRIMARY KEY,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    energy DOUBLE PRECISION NOT NULL,
                    credits INTEGER NOT NULL,
                    inventory INTEGER NOT NULL DEFAULT 0,
                    goals_json TEXT NOT NULL,
                    alive INTEGER NOT NULL DEFAULT 1,
                    updated_turn INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS agent_memory (
                    id SERIAL PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    turn INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS relationships (
                    src TEXT NOT NULL,
                    dst TEXT NOT NULL,
                    weight DOUBLE PRECISION NOT NULL,
                    updated_turn INTEGER NOT NULL,
                    PRIMARY KEY (src, dst)
                );
                CREATE TABLE IF NOT EXISTS constitution (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    text TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    updated_turn INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS event_log (
                    id SERIAL PRIMARY KEY,
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
                    VALUES (1, %s, 1, 0)
                    """,
                    (SEED_CONSTITUTION,),
                )

    def reset_all(self) -> None:
        with self.connect() as conn:
            for table in (
                "agent_memory",
                "event_log",
                "metrics_history",
                "relationships",
                "agent_state",
                "meta",
            ):
                conn.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            conn.execute(
                "UPDATE constitution SET text=%s, version=1, updated_turn=0 WHERE id=1",
                (SEED_CONSTITUTION,),
            )
            conn.execute(
                "INSERT INTO meta(key, value) VALUES ('turn', '0') "
                "ON CONFLICT (key) DO UPDATE SET value='0'"
            )

    def get_turn(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key='turn'").fetchone()
            return int(row["value"]) if row else 0

    def set_turn(self, turn: int) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO meta(key, value) VALUES ('turn', %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """,
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
                VALUES (%s, %s, %s, %s, %s)
                """,
                (turn, agent_id, event_type, json.dumps(payload), _utc_now()),
            )

    def add_memory(self, agent_id: str, turn: int, category: str, content: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_memory(agent_id, turn, category, content, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (agent_id, turn, category, content, _utc_now()),
            )

    def get_memories(self, agent_id: str, limit: int = 20) -> List[Dict[str, str]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT turn, category, content FROM agent_memory
                WHERE agent_id=%s ORDER BY id DESC LIMIT %s
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
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (agent_id) DO UPDATE SET
                    x=EXCLUDED.x, y=EXCLUDED.y, energy=EXCLUDED.energy,
                    credits=EXCLUDED.credits, inventory=EXCLUDED.inventory,
                    goals_json=EXCLUDED.goals_json, alive=EXCLUDED.alive,
                    updated_turn=EXCLUDED.updated_turn
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
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (src,dst) DO UPDATE SET
                    weight=EXCLUDED.weight, updated_turn=EXCLUDED.updated_turn
                """,
                (src, dst, weight, turn),
            )

    def save_constitution(self, text: str, version: int, turn: int) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE constitution SET text=%s, version=%s, updated_turn=%s WHERE id=1",
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
                INSERT INTO metrics_history(turn, metrics_json) VALUES (%s,%s)
                ON CONFLICT (turn) DO UPDATE SET metrics_json=EXCLUDED.metrics_json
                """,
                (turn, json.dumps(metrics)),
            )
