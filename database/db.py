"""
Database connection helper — the ONE place that knows how to reach Postgres.

"""

import os

import psycopg


def get_db_connection():
    """Open and return a new connection to the PostgreSQL database.

    Values are read from the environment (set in .env, injected by Docker
    Compose). The defaults match docker-compose.yml so the app still works if a
    variable is missing. Note host defaults to "db" — the Compose service name
    of the Postgres container, NOT "localhost".
    """
    return psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "db"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "appdb"),
        user=os.environ.get("POSTGRES_USER", "appuser"),
        password=os.environ.get("POSTGRES_PASSWORD", "changeme"),
    )
