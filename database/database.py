import os
from datetime import date, timedelta

import psycopg
# Psycopg is the most popular PostgreSQL database adapter for Python
# https://www.psycopg.org/psycopg3/docs/basic/usage.html for method usages

from werkzeug.security import generate_password_hash, check_password_hash


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

def signup_for_account(username, password):
    password_hash = generate_password_hash(password)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO Accounts (username, password_hash, isAdmin)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (username, password_hash, False),
                )
                # fetchone() returns the single RETURNING row as a tuple, e.g. (5,);
                # [0] pulls out the integer id. (fetchall() would give [(5,)], a list.)
                return cur.fetchone()[0]
            except psycopg.errors.UniqueViolation: # if a unique constaint raises and error (like duplicate username inserted)
                return None # signals that a signup was unable to be made

def login_to_account(username, password):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, password_hash FROM accounts WHERE username = %s",
                (username,),
            )
            row = cur.fetchone()
    if row is None: # if no matching username
        return None # return login was unable to complete
    account_id, password_hash = row
    if check_password_hash(password_hash, password):
        return account_id # correct password
    return None # wrong password

def change_password(username, password):
    password_hash = generate_password_hash(password)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    UPDATE Accounts 
                    SET password_hash = %s
                    WHERE username = %s
                    RETURNING id
                    """,
                    (password_hash, username),
                )
                # fetchone() returns the single RETURNING row as a tuple, e.g. (5,);
                # [0] pulls out the integer id. (fetchall() would give [(5,)], a list.)
                return cur.fetchone()[0]
            except psycopg.errors.UniqueViolation: # if a unique constaint raises and error (like duplicate username inserted)
                return None # signals that a signup was unable to be made



def get_username_by_id(account_id):
    """Look up a username from an account id (used to show who is logged in).

    Returns the username string, or None if the id doesn't exist.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT username FROM accounts WHERE id = %s",
                (account_id,),
            )
            row = cur.fetchone()
    if row is None:
        return None
    return row[0]

