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


def add_events(event_name, country, city, time, date, lattitude, longitude):
    conn = get_db_connection()

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO events (event_name, country, city, time, date, latitude, longitude) VALUES (%s, %s, %s, %s, %s, %s, %s)", (event_name, country, city, time, date, lattitude, longitude))
 
    conn.commit # Make the changes to the database persistent
    conn.close


def get_events():
    conn = get_db_connection()

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM events")
        events = cur.fetchall()
        
    conn.close
    return events


def delete_events(event_id):
    conn = get_db_connection()

    with conn.cursor() as cur:
        cur.execute("DELETE FROM events WHERE id = %s", (event_id))

    conn.commit
    conn.close

def delete_old_events():
    conn = get_db_connection()
    cutoff_date = date.today() - timedelta(days=365)

    with conn.cursor() as cur:
        cur.execute("DELETE FROM events WHERE date < %s", (cutoff_date,))
        deleted_count = cur.rowcount

    conn.commit()
    conn.close()
    return deleted_count
    
