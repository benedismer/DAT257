import os
from datetime import date, timedelta

import psycopg
from werkzeug.security import generate_password_hash, check_password_hash
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



def add_events(event_name, country, city, event_time, event_date, latitude, longitude, username):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO events
                    (event_name, country, city, time, date, latitude, longitude, username)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (event_name, country, city, event_time, event_date, latitude, longitude, username),
            )
            event_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO EventAttendance (eventid, username)
                VALUES (%s, %s)
                ON CONFLICT (eventid, username) DO NOTHING
                """,
                (event_id, username),
            )
            return event_id

def get_events(
    sort_by="date_asc",
    search=None,
    subscriber_id=None,
    attending_username=None,
    past_attending=False,
):
    order_by = {
        "date_asc": "date ASC, time ASC, id ASC",
        "date_desc": "date DESC, time DESC, id DESC",
        "name_asc": "event_name ASC, date ASC, time ASC, id ASC",
        "name_desc": "event_name DESC, date DESC, time DESC, id DESC",
        "city_asc": "city ASC NULLS LAST, date ASC, time ASC, id ASC",
    }.get(sort_by, "date ASC, time ASC, id ASC")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            conditions = []
            parameters = []
            subscription_join = ""
            if subscriber_id is not None:
                subscription_join = (
                    "JOIN Subscriptions s ON "
                    "s.organizer_id = a.id"
                )
                conditions.append("s.subscriber_id = %s")
                parameters.append(subscriber_id)
            if past_attending and attending_username is not None:
                conditions.append(
                    "(EXISTS ("
                    "SELECT 1 FROM EventAttendance ea "
                    "WHERE ea.eventid = e.id AND ea.username = %s"
                    ") OR e.username = %s)"
                )
                parameters.extend([attending_username, attending_username])
                conditions.append(
                    "(e.date < CURRENT_DATE OR "
                    "(e.date = CURRENT_DATE AND e.time < CURRENT_TIME))"
                )
            else:
                conditions.append(
                    "(e.date > CURRENT_DATE OR "
                    "(e.date = CURRENT_DATE AND e.time >= CURRENT_TIME))"
                )
            if search:
                conditions.append(
                    "(e.event_name ILIKE %s OR e.country ILIKE %s OR e.city ILIKE %s "
                    "OR a.username ILIKE %s)"
                )
                search_value = f"%{search}%"
                parameters.extend([search_value] * 4)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            qualified_order = (
                order_by.replace("date", "e.date")
                .replace("time", "e.time")
                .replace("id", "e.id")
                .replace("event_name", "e.event_name")
                .replace("city", "e.city")
            )
            cur.execute(
                f"""
                  SELECT e.id, e.event_name, e.country, e.city,
                      e.time::text AS time, e.date::text AS date,
                      e.latitude, e.longitude, e.username
                  FROM events e
                  LEFT JOIN accounts a ON a.username = e.username
                  {subscription_join}
                  {where_clause}
                  ORDER BY {qualified_order}
                """,
                parameters,
            )
            return cur.fetchall()


def get_attending_event_ids(username):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT eventid
                FROM EventAttendance
                WHERE username = %s
                UNION
                SELECT id
                FROM Events
                WHERE username = %s
                """,
                (username, username),
            )
            return {row[0] for row in cur.fetchall()}


def attend_event(event_id, username):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO EventAttendance (eventid, username)
                SELECT %s, username FROM Accounts WHERE username = %s
                ON CONFLICT (eventid, username) DO NOTHING
                RETURNING id
                """,
                (event_id, username),
            )
            return cur.fetchone() is not None


def stop_attending_event(event_id, username):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM EventAttendance
                WHERE eventid = %s AND username = %s
                """,
                (event_id, username),
            )
            return cur.rowcount > 0


def get_created_events_with_attendees(username):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT e.id, e.event_name, e.country, e.city,
                       e.time::text AS time, e.date::text AS date,
                       e.username,
                       ARRAY(
                           SELECT attendee_username
                           FROM (
                               SELECT e.username AS attendee_username
                               UNION
                               SELECT ea.username
                               FROM EventAttendance ea
                               WHERE ea.eventid = e.id
                           ) attendees
                           ORDER BY attendee_username
                       ) AS attendees
                       , e.latitude, e.longitude
                FROM Events e
                WHERE e.username = %s
                ORDER BY e.date ASC, e.time ASC, e.id ASC
                """,
                (username,),
            )
            return cur.fetchall()


def update_event(
    event_id,
    username,
    event_name,
    country,
    city,
    event_time,
    event_date,
    latitude,
    longitude,
):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE Events
                SET event_name = %s, country = %s, city = %s,
                    time = %s, date = %s, latitude = %s, longitude = %s
                WHERE id = %s AND username = %s
                RETURNING id
                """,
                (
                    event_name,
                    country,
                    city,
                    event_time,
                    event_date,
                    latitude,
                    longitude,
                    event_id,
                    username,
                ),
            )
            row = cur.fetchone()
            return row[0] if row else None


def delete_event(event_id, username):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM Events WHERE id = %s AND username = %s RETURNING id",
                (event_id, username),
            )
            row = cur.fetchone()
            return row is not None


def subscribe_to_user(subscriber_id, organizer_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO Subscriptions
                    (subscriber_id, organizer_id)
                SELECT %s, id FROM Accounts
                WHERE id = %s AND id <> %s
                ON CONFLICT DO NOTHING
                RETURNING id
                """,
                (subscriber_id, organizer_id, subscriber_id),
            )
            return cur.fetchone() is not None


def get_users(search=None, subscriber_id=None):
    """Return accounts matching a username search and their subscription state."""
    conditions = []
    parameters = []
    subscription_join = ""

    if subscriber_id is not None:
        conditions.append("a.id <> %s")
        subscription_join = "LEFT JOIN Subscriptions s ON s.organizer_id = a.id AND s.subscriber_id = %s"
        parameters.extend([subscriber_id, subscriber_id])
    if search:
        conditions.append("a.username ILIKE %s")
        parameters.append(f"%{search}%")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    subscription_column = "(s.id IS NOT NULL)" if subscriber_id is not None else "FALSE"

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                    SELECT a.id, a.username, {subscription_column} AS subscribed
                    FROM Accounts a
                    {subscription_join}
                    {where_clause}
                    ORDER BY a.username ASC
                """,
                parameters,
            )
            return cur.fetchall()


def unsubscribe_from_user(subscriber_id, organizer_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                                DELETE FROM Subscriptions
                                WHERE subscriber_id = %s
                                    AND organizer_id = %s
                """,
                                (subscriber_id, organizer_id),
            )
            return cur.rowcount > 0

def delete_events(event_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM events WHERE id = %s", (event_id,))

def delete_old_events():
    cutoff_date = date.today() - timedelta(days=365)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM EventAttendance ea
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM Events e
                    WHERE e.id = ea.eventid
                )
                OR EXISTS (
                    SELECT 1
                    FROM Events e
                    WHERE e.id = ea.eventid AND e.date < %s
                )
                """,
                (cutoff_date,),
            )
            cur.execute("DELETE FROM events WHERE date < %s", (cutoff_date,))
            return cur.rowcount

def signup_for_account(username, password):
    password_hash = generate_password_hash(password)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO Accounts (username, password_hash, isOrganiser)
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
