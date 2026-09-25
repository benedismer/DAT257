import os
from datetime import date, timedelta

import psycopg
# Psycopg is the most popular PostgreSQL database adapter for Python
# https://www.psycopg.org/psycopg3/docs/basic/usage.html for method usages



def get_db_connection():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "event"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "Your_Postgres_Password"),
    )


def add_events(event_name, country, city, event_time, event_date, latitude, longitude):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO events
                    (event_name, country, city, time, date, latitude, longitude)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (event_name, country, city, event_time, event_date, latitude, longitude),
            )
            return cur.fetchone()[0]


def get_events():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                  SELECT id, event_name, country, city,
                      time::text AS time, date::text AS date,
                      latitude, longitude
                FROM events
                ORDER BY date, time, id
                """
            )
            return cur.fetchall()


def delete_events(event_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM events WHERE id = %s", (event_id,))

def delete_old_events():
    cutoff_date = date.today() - timedelta(days=365)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM events WHERE date < %s", (cutoff_date,))
            return cur.rowcount
    
