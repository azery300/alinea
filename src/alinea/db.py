"""Postgres connection helpers."""

import psycopg

from alinea.config import get_settings


def connect(url: str | None = None) -> psycopg.Connection:
    """Open a connection and make sure the pgvector extension is available."""
    conn = psycopg.connect(url or get_settings().database_url)
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.commit()
    return conn
