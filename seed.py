"""
seed.py — populate the database with realistic fake data for development.

Run inside the web container:
    docker exec dat257-web-1 python seed.py

Or locally (if you have psycopg + env vars set):
    python seed.py

Pass --reset to wipe all existing rows before inserting:
    docker exec dat257-web-1 python seed.py --reset
"""

import sys
from datetime import date, time, timedelta
from pathlib import Path
from shutil import copy2

from werkzeug.security import generate_password_hash

from database.database import get_db_connection

PICTURE_SEED_FOLDER = Path(__file__).resolve().parent / "Picture_Seed"
PICTURE_FOLDER = Path(__file__).resolve().parent / "pictures"
PICTURE_SUFFIXES = {".gif", ".jpeg", ".jpg", ".png", ".webp"}

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

# password is "password" for every account so it's easy to log in
PASSWORD_HASH = generate_password_hash("password")

# (username, isTeam)
ACCOUNTS = [
    ("frank", False),
    ("alice",      False),
    ("bob",        False),
    ("charlie",    False),
    ("diana",      False),
    ("eve",        False),
    ("GreenCrew",  True),
    ("CleanCoast", True),
    ("EcoRiders",  True),       # addded more test accounts for leaderboard scrolling
    ("OceanHeroes", True),
    ("TrashBusters", True),
    ("NatureSquad", True),
    ("CityCleaners", True),
    ("GreenSteps", True),
]

# (account username, team name, city, country)
TEAMS = [
    ("GreenCrew",  "Green Crew",   "Gothenburg", "Sweden"),
    ("CleanCoast", "Clean Coast",  "Malmö",      "Sweden"),
    ("EcoRiders",  "Eco Riders",   None,         None),         
    ("OceanHeroes", "Ocean Heroes", "Gothenburg", "Sweden"),    # added more test accounts
    ("TrashBusters", "Trash Busters", "Stockholm", "Sweden"),
    ("NatureSquad", "Nature Squad", "Malmö", "Sweden"),
    ("CityCleaners", "City Cleaners", "Uppsala", "Sweden"),
    ("GreenSteps", "Green Steps", "Lund", "Sweden"),
]

today = date.today()

# (event_name, country, city, time, date, latitude, longitude, organiser_username)
EVENTS = [
    ("River cleanup",          "Sweden", "Gothenburg", time(10, 0),  today + timedelta(days=3),   57.7089, 11.9746, "GreenCrew"),
    ("Park sorting session",   "Sweden", "Gothenburg", time(14, 30), today + timedelta(days=10),  57.6969, 11.9750, "alice"),
    ("Canal cleanup morning",  "Sweden", "Gothenburg", time(9, 0),   today + timedelta(days=17),  57.7065, 11.9684, "GreenCrew"),
    ("Beach sweep",            "Sweden", "Malmö",      time(11, 0),  today + timedelta(days=5),   55.6050, 13.0038, "CleanCoast"),
    ("Harbour rubbish run",    "Sweden", "Malmö",      time(8, 30),  today + timedelta(days=12),  55.6125, 12.9998, "CleanCoast"),
    ("Forest trail cleanup",   None,     None,         time(9, 0),   today + timedelta(days=20),  57.7209, 12.0320, "EcoRiders"),
    ("Neighbourhood recycling","Sweden", "Gothenburg", time(12, 0),  today + timedelta(days=21),  57.7155, 11.9694, "alice"),
    ("Old town sweep",         "Sweden", "Gothenburg", time(15, 0),  today + timedelta(days=2),   57.7042, 11.9672, "bob"),
    ("Autumn park cleanup",    "Sweden", "Gothenburg", time(13, 0),  today - timedelta(days=7),   57.7010, 11.9710, "GreenCrew"),
    ("Spring canal run",       "Sweden", "Gothenburg", time(10, 30), today - timedelta(days=30),  57.7080, 11.9730, "alice"),
    ("Ocean cleanup",          "Sweden", "Gothenburg", time(10, 0),  today + timedelta(days=4),   57.7089, 11.9746, "OceanHeroes"),
]

# (latitude, longitude, creator_username)
TRASH_LOCATIONS = [
    (57.7118, 11.9624, "alice"),       # under the Älvsborg bridge
    (57.6984, 11.9872, "bob"),         # near the river path
    (55.6171, 12.9915, "diana"),       # Malmö waterfront
    (57.7245, 12.0142, "GreenCrew"),   # forest trail outside the city
]

# (subscriber_username, team_username)  — users following teams
SUBSCRIPTIONS = [
    ("alice",   "GreenCrew"),
    ("alice",   "CleanCoast"),
    ("bob",     "GreenCrew"),
    ("charlie", "EcoRiders"),
    ("diana",   "CleanCoast"),
    ("eve",     "GreenCrew"),
    ("eve",     "EcoRiders"),
]

# (member_username, team_username) — users who have joined teams
TEAM_MEMBERS = [
    ("alice", "GreenCrew"),
    ("bob", "GreenCrew"),
    ("charlie", "EcoRiders"),
    ("diana", "CleanCoast"),
    ("eve", "GreenCrew"),
    ("frank", "OceanHeroes"),
]

# (event index from EVENTS list above, attendee_username)
ATTENDANCE = [
    (0, "alice"),
    (0, "bob"),
    (0, "eve"),
    (1, "charlie"),
    (1, "diana"),
    (2, "alice"),
    (2, "eve"),
    (3, "diana"),
    (3, "bob"),
    (4, "charlie"),
    (6, "bob"),
    (7, "alice"),
    (7, "charlie"),
    (8, "alice"),   # past event
    (8, "bob"),     # past event
    (9, "bob"),     # past event
]

# (event index from EVENTS list above, contributor_username, amount, type)
# Bag entries are converted to 10 kg by get_trash_by_event().
TRASH = [
    (0, "alice",   3, "bags"),
    (0, "bob",     8, "plastic"),
    (1, "charlie", 2, "bags"),
    (1, "diana",   5, "glass"),
    (2, "eve",     12, "plastic"),
    (3, "diana",   4, "bags"),
    (3, "bob",     7, "metal"),
    (4, "charlie", 9, "plastic"),
    (5, "EcoRiders", 3, "bags"),
    (6, "bob",     6, "glass"),
    (7, "alice",   2, "bags"),
    (8, "alice",   5, "plastic"),
    (8, "bob",     3, "bags"),
    (9, "bob",     4, "glass"),
    (10, "frank",   6, "plastic"),
]

PHOTOS = [
    # (event index, uploader username, team username, filename)
    (0, "alice", "GreenCrew", "river-cleanup-alice.png"),
    (0, "bob", "GreenCrew", "river-cleanup-bob.png"),
    (1, "charlie", "EcoRiders", "park-sorting-session-charlie.png"),
    (3, "diana", "CleanCoast", "beach-sweep-diana.png"),
    (4, "bob", "CleanCoast", "harbour-rubbish-run-bob.png"),
    (6, "eve", "GreenCrew", "neighbourhood-recycling-eve.png"),
    (8, "alice", "GreenCrew", "autumn-park-cleanup-alice.png"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def reset(cur):
    """Delete all rows in dependency order."""
    cur.execute("DELETE FROM pictures")
    cur.execute("DELETE FROM eventattendance")
    cur.execute("DELETE FROM trash")
    cur.execute("DELETE FROM trashlocations")
    cur.execute("DELETE FROM teammembers")
    cur.execute("DELETE FROM events")
    cur.execute("DELETE FROM subscriptions")
    cur.execute("DELETE FROM teams")
    cur.execute("DELETE FROM accounts")
    print("  ✓ existing data cleared")


def insert_accounts(cur):
    ids = {}
    for username, is_team in ACCOUNTS:
        cur.execute(
            """
            INSERT INTO accounts (username, password_hash, isteam)
            VALUES (%s, %s, %s)
            ON CONFLICT (username) DO UPDATE
                SET password_hash = EXCLUDED.password_hash,
                    isTeam        = EXCLUDED.isTeam
            RETURNING id
            """,
            (username, PASSWORD_HASH, is_team),
        )
        ids[username] = cur.fetchone()[0]
    print(f"  ✓ {len(ACCOUNTS)} accounts")
    return ids


def insert_teams(cur, admin_ids):
    team_ids = {}
    for username, name, city, country in TEAMS:
        admin_id = admin_ids[username]
        cur.execute(
            """
            INSERT INTO teams (admin_id, name, city, country)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (admin_id) DO UPDATE
                SET name    = EXCLUDED.name,
                    city    = EXCLUDED.city,
                    country = EXCLUDED.country
            """,
            (admin_id, name, city, country),
        )
        cur.execute("SELECT id FROM teams WHERE admin_id = %s", (admin_id,))
        team_ids[username] = cur.fetchone()[0]
    print(f"  ✓ {len(TEAMS)} teams")
    return team_ids


def insert_events(cur):
    event_ids = []
    for event_name, country, city, evt_time, evt_date, lat, lon, organiser in EVENTS:
        cur.execute(
            """
            INSERT INTO events
                (event_name, country, city, time, date, latitude, longitude, username)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (event_name, country, city, evt_time, evt_date, lat, lon, organiser),
        )
        event_ids.append(cur.fetchone()[0])
    print(f"  ✓ {len(EVENTS)} events")
    return event_ids


def insert_trash_locations(cur):
    for latitude, longitude, username in TRASH_LOCATIONS:
        cur.execute(
            """
            INSERT INTO trashlocations (latitude, longitude, username)
            VALUES (%s, %s, %s)
            """,
            (latitude, longitude, username),
        )
    print(f"  ✓ {len(TRASH_LOCATIONS)} trashy locations")


def insert_subscriptions(cur, account_ids):
    for subscriber, team in SUBSCRIPTIONS:
        cur.execute(
            """
            INSERT INTO subscriptions (subscriber_id, team_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (account_ids[subscriber], account_ids[team]),
        )
    print(f"  ✓ {len(SUBSCRIPTIONS)} subscriptions")


def insert_team_members(cur, account_ids):
    team_ids = {}
    for team_username, team_name, _, _ in TEAMS:
        cur.execute("SELECT id FROM teams WHERE name = %s", (team_name,))
        team_ids[team_username] = cur.fetchone()[0]

    for member, team in TEAM_MEMBERS:
        cur.execute(
            """
            INSERT INTO teammembers (team_id, member_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (team_ids[team], account_ids[member]),
        )
    print(f"  ✓ {len(TEAM_MEMBERS)} team memberships")


def insert_attendance(cur, event_ids, account_ids):
    # Organisers automatically attend their own events
    organiser_pairs = set()
    for idx, (_, _, _, _, _, _, _, organiser) in enumerate(EVENTS):
        organiser_pairs.add((event_ids[idx], organiser))

    extra_pairs = {
        (event_ids[event_idx], username)
        for event_idx, username in ATTENDANCE
    }

    all_pairs = organiser_pairs | extra_pairs

    for event_id, username in all_pairs:
        cur.execute(
            """
            INSERT INTO eventattendance (eventid, username)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (event_id, username),
        )
    print(f"  ✓ {len(all_pairs)} attendance records")


def insert_trash(cur, event_ids):
    for event_index, contributor, amount, trash_type in TRASH:
        cur.execute(
            """
            INSERT INTO trash (event_id, account_name, amount, type)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (event_id, account_name, type) DO UPDATE
                SET amount = EXCLUDED.amount
            """,
            (event_ids[event_index], contributor, amount, trash_type),
        )
    print(f"  ✓ {len(TRASH)} trash records")


def insert_picture(cur, event_id, account_id, team_id, filename):
    cur.execute(
        """
        INSERT INTO pictures (file_path, uploader_id, event_id, team_id)
        VALUES (%s, %s, %s, %s)
        """,
        (filename, account_id, event_id, team_id),
    )


def copy_picture_seed():
    PICTURE_FOLDER.mkdir(exist_ok=True)
    for path in PICTURE_FOLDER.iterdir():
        if path.is_file() and path.suffix.lower() in PICTURE_SUFFIXES:
            path.unlink()

    for source in sorted(PICTURE_SEED_FOLDER.iterdir()):
        if source.is_file() and source.suffix.lower() in PICTURE_SUFFIXES:
            copy2(source, PICTURE_FOLDER / source.name)
    print(f"  ✓ {len(PHOTOS)} picture files copied")


def insert_pictures(cur, event_ids, account_ids, team_ids):
    for event_index, uploader, team, filename in PHOTOS:
        insert_picture(
            cur,
            event_ids[event_index],
            account_ids[uploader],
            team_ids[team],
            filename,
        )
    print(f"  ✓ {len(PHOTOS)} picture records")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    do_reset = "--reset" in sys.argv

    print("Connecting to database...")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE teams ADD COLUMN IF NOT EXISTS bio TEXT")
            if do_reset:
                print("Resetting data...")
                reset(cur)

            print("Inserting seed data...")
            account_ids = insert_accounts(cur)
            team_ids = insert_teams(cur, account_ids)
            event_ids = insert_events(cur)
            insert_trash_locations(cur)
            insert_subscriptions(cur, account_ids)
            insert_team_members(cur, account_ids)
            insert_attendance(cur, event_ids, account_ids)
            insert_trash(cur, event_ids)
            copy_picture_seed()
            insert_pictures(cur, event_ids, account_ids, team_ids)

    print("\nDone! All accounts use password: password")
    print("Accounts:", ", ".join(u for u, _ in ACCOUNTS))


if __name__ == "__main__":
    main()
