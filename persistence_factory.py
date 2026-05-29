"""Create SQLite or PostgreSQL persistence backend."""

from __future__ import annotations

import os
from typing import Union

from config import DB_PATH
from persistence import Persistence

PersistenceBackend = Union[Persistence, "PostgresPersistence"]


def create_persistence(database_url: str | None = None) -> PersistenceBackend:
    url = database_url or os.environ.get("DATABASE_URL")
    if url and url.startswith(("postgres://", "postgresql://")):
        from persistence_postgres import PostgresPersistence

        return PostgresPersistence(url)
    return Persistence(DB_PATH)
