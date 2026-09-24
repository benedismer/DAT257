"""
Database connection helper — the ONE place that knows how to reach Postgres.

"""

import os

import psycopg
# Psycopg is the most popular PostgreSQL database adapter for Python
# https://www.psycopg.org/psycopg3/docs/basic/usage.html for method usages

#### Installation for Mac ####
# python3 -m venv .venv
# source .venv/bin/activate
# python -m pip install "psycopg[binary]"
# python -c "import psycopg; print(psycopg.__version__)" // Verify it's properly installed
##############################

def get_db_connection():
    return psycopg.connect(
        host="localhost",
        dbname="event",
        user="postgres",
        password="Your_Postgres_Password" # Modify it before testing
    )


def add_events(event_name, country, city, time, date):
    conn = get_db_connection()

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO events (event_name, country, city, time, date) VALUES (%s, %s, %s, %s, %s)", (event_name, country, city, time, date))
 
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
    
