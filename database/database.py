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
    team_member_id=None,
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
            team_join = ""
            if subscriber_id is not None:
                subscription_join = (
                    "JOIN Subscriptions s ON "
                    "s.team_id = a.id"
                )
                conditions.append("s.subscriber_id = %s")
                parameters.append(subscriber_id)
            if team_member_id is not None:
                team_join = (
                    "JOIN Teams t ON t.admin_id = a.id "
                    "LEFT JOIN TeamMembers tm ON tm.team_id = t.id "
                    "AND tm.member_id = %s"
                )
                conditions.append("(t.admin_id = %s OR tm.member_id IS NOT NULL)")
                parameters.extend([team_member_id, team_member_id])
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
                  {team_join}
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


def get_team_event_ids(member_id):
    """Return events created by the team this account belongs to."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT e.id
                FROM Events e
                JOIN Accounts a ON a.username = e.username
                JOIN Teams t ON t.admin_id = a.id
                LEFT JOIN TeamMembers tm
                    ON tm.team_id = t.id AND tm.member_id = %s
                WHERE t.admin_id = %s OR tm.member_id IS NOT NULL
                """,
                (member_id, member_id),
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


def subscribe_to_user(subscriber_id, team_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO Subscriptions
                    (subscriber_id, team_id)
                SELECT %s, id FROM Accounts
                WHERE id = %s AND id <> %s
                ON CONFLICT DO NOTHING
                RETURNING id
                """,
                (subscriber_id, team_id, subscriber_id),
            )
            return cur.fetchone() is not None


def get_teams(search=None, member_id=None):
    """Return teams and whether the account has joined each team."""
    conditions = []
    parameters = []
    if search:
        conditions.append("(t.name ILIKE %s OR admin.username ILIKE %s)")
        search_value = f"%{search}%"
        parameters.extend([search_value, search_value])

    membership_column = "FALSE"
    membership_join = ""
    if member_id is not None:
        membership_join = (
            "LEFT JOIN teammembers tm ON tm.team_id = t.id "
            "AND tm.member_id = %s"
        )
        parameters.insert(0, member_id)
        membership_column = "(t.admin_id = %s OR tm.member_id IS NOT NULL)"
        parameters.insert(1, member_id)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                    SELECT t.id, t.name, t.city, t.country,
                           admin.username AS leader,
                           {membership_column} AS joined
                    FROM teams t
                    JOIN accounts admin ON admin.id = t.admin_id
                    {membership_join}
                    {where_clause}
                    ORDER BY t.name ASC
                """,
                parameters,
            )
            return cur.fetchall()


def get_team_leaderboard():
    """Return teams ranked by average member attendance percentage."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH team_members AS (
                    SELECT id AS team_id, admin_id AS member_id
                    FROM Teams
                    UNION
                    SELECT team_id, member_id
                    FROM TeamMembers
                ),
                member_counts AS (
                    SELECT team_id, COUNT(*) AS member_count
                    FROM team_members
                    GROUP BY team_id
                ),
                event_counts AS (
                    SELECT t.id AS team_id, COUNT(e.id) AS event_count
                    FROM Teams t
                    LEFT JOIN Accounts admin ON admin.id = t.admin_id
                    LEFT JOIN Events e ON e.username = admin.username
                    GROUP BY t.id
                ),
                event_attendance AS (
                    SELECT t.id AS team_id,
                           e.id AS event_id,
                           COUNT(DISTINCT ea.username) AS attendee_count
                    FROM Teams t
                    JOIN Accounts admin ON admin.id = t.admin_id
                    JOIN Events e ON e.username = admin.username
                    JOIN EventAttendance ea ON ea.eventid = e.id
                    JOIN Accounts attendee ON attendee.username = ea.username
                    JOIN team_members tm
                        ON tm.team_id = t.id AND tm.member_id = attendee.id
                    GROUP BY t.id, e.id
                )
                SELECT t.id, t.name,
                       COALESCE(SUM(ea.attendee_count), 0)::numeric
                           / NULLIF(mc.member_count * ec.event_count, 0) * 100
                           AS score,
                       mc.member_count, ec.event_count
                FROM Teams t
                JOIN member_counts mc ON mc.team_id = t.id
                JOIN event_counts ec ON ec.team_id = t.id
                LEFT JOIN event_attendance ea ON ea.team_id = t.id
                GROUP BY t.id, t.name, mc.member_count, ec.event_count
                ORDER BY score DESC NULLS LAST, t.name ASC
                """
            )
            return cur.fetchall()


def get_team_members(leader_id):
    """Return the members of the team owned by the account, if any."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.username, TRUE AS is_leader
                FROM Teams t
                JOIN Accounts a ON a.id = t.admin_id
                WHERE t.admin_id = %s
                UNION ALL
                SELECT member.username, FALSE AS is_leader
                FROM Teams t
                JOIN TeamMembers tm ON tm.team_id = t.id
                JOIN Accounts member ON member.id = tm.member_id
                WHERE t.admin_id = %s AND tm.member_id <> t.admin_id
                ORDER BY is_leader DESC, username ASC
                """,
                (leader_id, leader_id),
            )
            return cur.fetchall()


def join_team(team_id, member_id):
    """Join a team, returning whether a new membership was created."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO TeamMembers (team_id, member_id)
                SELECT %s, %s
                WHERE EXISTS (SELECT 1 FROM Teams WHERE id = %s)
                  AND NOT EXISTS (
                      SELECT 1 FROM Teams
                      WHERE admin_id = %s
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM TeamMembers
                      WHERE member_id = %s
                  )
                ON CONFLICT DO NOTHING
                RETURNING id
                """,
                (team_id, member_id, team_id, member_id, member_id),
            )
            return cur.fetchone() is not None


def leave_team(team_id, member_id):
    """Leave a team; team leaders remain members by virtue of ownership."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM TeamMembers
                WHERE team_id = %s AND member_id = %s
                  AND NOT EXISTS (
                      SELECT 1 FROM Teams
                      WHERE id = %s AND admin_id = %s
                  )
                """,
                (team_id, member_id, team_id, member_id),
            )
            return cur.rowcount > 0


def get_users(search=None, subscriber_id=None, team_member_id=None):
    """Return accounts matching a username search and their subscription state."""
    conditions = []
    parameters = []
    subscription_join = ""

    if subscriber_id is not None:
        conditions.append("a.id <> %s")
        subscription_join = "LEFT JOIN Subscriptions s ON s.team_id = a.id AND s.subscriber_id = %s"
        parameters.extend([subscriber_id, subscriber_id])
    if search:
        conditions.append("a.username ILIKE %s")
        parameters.append(f"%{search}%")
    if team_member_id is not None:
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM Teams account_team
                WHERE (account_team.admin_id = a.id OR EXISTS (
                    SELECT 1
                    FROM TeamMembers account_membership
                    WHERE account_membership.team_id = account_team.id
                      AND account_membership.member_id = a.id
                ))
                  AND (
                      account_team.admin_id = %s OR EXISTS (
                          SELECT 1
                          FROM TeamMembers current_membership
                          WHERE current_membership.team_id = account_team.id
                            AND current_membership.member_id = %s
                      )
                  )
            )
            """
        )
        parameters.extend([team_member_id, team_member_id])

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


def unsubscribe_from_user(subscriber_id, team_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                                DELETE FROM Subscriptions
                                WHERE subscriber_id = %s
                                    AND team_id = %s
                """,
                                (subscriber_id, team_id),
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
                    INSERT INTO Accounts (username, password_hash, isTeam)
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



def create_team(admin_id, team_name, city, country):
    """Create a team for an account and mark the account as isTeam=TRUE.

    Returns the new team id on success, or None if the account already has a
    team (UNIQUE constraint on admin_id) or the account doesn't exist.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO Teams (admin_id, name, city, country)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (admin_id, team_name, city or None, country or None),
                )
                team_id = cur.fetchone()[0]
                cur.execute(
                    "UPDATE Accounts SET isTeam = TRUE WHERE id = %s",
                    (admin_id,),
                )
                return team_id
            except psycopg.errors.UniqueViolation:
                return None  # account already owns a team


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

def add_trash(event_id, username, amount, type):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                # adds new rows
                cur.execute(
                	"""
                	INSERT INTO Trash(event_id, account_name, amount, type)
                	VALUES (%s, %s, %s, %s)
                	ON CONFLICT (event_id, account_name, type) DO UPDATE SET
                	event_id = %s, account_name = %s, amount = Trash.amount + %s, type = %s
                	""",
                	(event_id, username, amount, type, event_id, username, amount, type)
                )
                return True
            except:
                return None
def get_trash():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(" select * from Trash ")
            rows = cur.fetchall()
    return rows
