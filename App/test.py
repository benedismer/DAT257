from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import sys
from datetime import date, time
from unittest.mock import MagicMock, patch

import app as app_module
from database import database
from picture import PICTURE_FOLDER, Picture, add_picture


class FakeCursor:
    def __init__(self, rows=None, returned_id=None, fetchone_sequence=None):
        self.rows = rows or []
        self.returned_id = returned_id
        # fetchone_sequence: list of values returned by successive fetchone()
        # calls (each element is either a tuple or None). Takes priority over
        # returned_id when provided.
        self._fetchone_seq = list(fetchone_sequence) if fetchone_sequence else None
        self.executed = []
        self.rowcount = 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, parameters=None):
        self.executed.append((query, parameters))

    def fetchone(self):
        if self._fetchone_seq is not None:
            return self._fetchone_seq.pop(0) if self._fetchone_seq else None
        if self.returned_id is not None:
            returned_id, self.returned_id = self.returned_id, None
            return (returned_id,)
        return self.rows.pop(0) if self.rows else None

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, cursor):
        self.cursor_instance = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def cursor(self):
        return self.cursor_instance


def database_connection(cursor):
    return patch.object(
        database,
        "get_db_connection",
        return_value=FakeConnection(cursor),
    )


class DatabaseTests(unittest.TestCase):
    def test_add_picture_inserts_picture_metadata(self):
        cursor = FakeCursor(returned_id=19)

        with database_connection(cursor):
            picture_id = database.add_picture(
                PICTURE_FOLDER / "event-19.jpg", 7, 3, 4
            )

        self.assertEqual(picture_id, 19)
        query, parameters = cursor.executed[0]
        self.assertIn("INSERT INTO Pictures", query)
        self.assertEqual(
            parameters,
            (str(PICTURE_FOLDER / "event-19.jpg"), 7, 3, 4),
        )

    def test_picture_queries_return_picture_objects_for_the_requested_owner(self):
        row = (13, "event-3-photo.png", 7, 3, 4)
        queries = (
            (database.pictures_for_event, 3, "p.event_id"),
            (database.pictures_for_user, 7, "p.uploader_id"),
            (database.pictures_for_team, 4, "p.team_id"),
        )

        for picture_query, identifier, filter_column in queries:
            with self.subTest(filter_column=filter_column):
                cursor = FakeCursor(rows=[row])

                with database_connection(cursor):
                    pictures = picture_query(identifier)

                self.assertEqual(len(pictures), 1)
                self.assertEqual(pictures[0].file_path, Path(row[1]))
                self.assertEqual(pictures[0].id, row[0])
                query, parameters = cursor.executed[0]
                self.assertIn(filter_column + " = %s", query)
                self.assertEqual(parameters, (identifier,))

    def test_add_events_inserts_event_and_creator_attendance(self):
        cursor = FakeCursor(returned_id=17)

        with database_connection(cursor):
            event_id = database.add_events(
                "Study night", "Sweden", "Gothenburg", time(18), date(2026, 10, 3),
                57.7, 11.97, "alice",
            )

        self.assertEqual(event_id, 17)
        self.assertEqual(len(cursor.executed), 2)
        self.assertIn("INSERT INTO events", cursor.executed[0][0])
        self.assertIn("EventAttendance", cursor.executed[1][0])
        self.assertEqual(cursor.executed[1][1], (17, "alice"))

    def test_get_events_defaults_to_future_events(self):
        cursor = FakeCursor(rows=[])

        with database_connection(cursor):
            database.get_events()

        query, parameters = cursor.executed[0]
        self.assertIn("e.date > CURRENT_DATE", query)
        self.assertIn("e.time >= CURRENT_TIME", query)
        self.assertEqual(parameters, [])

    def test_get_events_past_attending_uses_attendance_and_creator(self):
        cursor = FakeCursor(rows=[])

        with database_connection(cursor):
            database.get_events(attending_username="alice", past_attending=True)

        query, parameters = cursor.executed[0]
        self.assertIn("EventAttendance ea", query)
        self.assertIn("e.date < CURRENT_DATE", query)
        self.assertEqual(parameters, ["alice", "alice"])

    def test_get_events_search_is_parameterized(self):
        cursor = FakeCursor(rows=[])

        with database_connection(cursor):
            database.get_events(search="concert")

        query, parameters = cursor.executed[0]
        self.assertIn("ILIKE %s", query)
        self.assertEqual(parameters, ["%concert%"] * 4)

    def test_get_events_subscribed_view_joins_subscriptions(self):
        cursor = FakeCursor(rows=[])

        with database_connection(cursor):
            database.get_events(subscriber_id=4)

        query, parameters = cursor.executed[0]
        self.assertIn("JOIN Subscriptions s", query)
        self.assertIn("s.subscriber_id = %s", query)
        self.assertEqual(parameters, [4])

    def test_get_events_rejects_unknown_sort_by_using_default(self):
        cursor = FakeCursor(rows=[])

        with database_connection(cursor):
            database.get_events("date_asc; DROP TABLE Events")

        query, _ = cursor.executed[0]
        self.assertIn("ORDER BY e.date ASC", query)
        self.assertNotIn("DROP TABLE", query)

    def test_get_attending_event_ids_includes_explicit_and_created_events(self):
        cursor = FakeCursor(rows=[(2,), (9,)])

        with database_connection(cursor):
            event_ids = database.get_attending_event_ids("alice")

        self.assertEqual(event_ids, {2, 9})
        self.assertIn("UNION", cursor.executed[0][0])
        self.assertEqual(cursor.executed[0][1], ("alice", "alice"))

    def test_attend_event_returns_true_for_inserted_attendance(self):
        cursor = FakeCursor(returned_id=33)

        with database_connection(cursor):
            attended = database.attend_event(33, "alice")

        self.assertTrue(attended)
        self.assertEqual(cursor.executed[0][1], (33, "alice"))

    def test_attend_event_returns_false_for_existing_attendance(self):
        cursor = FakeCursor()

        with database_connection(cursor):
            attended = database.attend_event(33, "alice")

        self.assertFalse(attended)

    def test_stop_attending_event_returns_deleted_row_count(self):
        cursor = FakeCursor()
        cursor.rowcount = 1

        with database_connection(cursor):
            removed = database.stop_attending_event(33, "alice")

        self.assertTrue(removed)
        self.assertEqual(cursor.executed[0][1], (33, "alice"))

    def test_created_events_query_includes_creator_and_attendees(self):
        cursor = FakeCursor(rows=[])

        with database_connection(cursor):
            database.get_created_events_with_attendees("alice")

        query, parameters = cursor.executed[0]
        self.assertIn("e.username AS attendee_username", query)
        self.assertIn("EventAttendance ea", query)
        self.assertEqual(parameters, ("alice",))

    def test_get_users_excludes_current_user(self):
        cursor = FakeCursor(rows=[])

        with database_connection(cursor):
            database.get_users(subscriber_id=7)

        query, parameters = cursor.executed[0]
        self.assertIn("a.id <> %s", query)
        self.assertEqual(parameters, [7, 7])

    def test_get_users_search_and_subscription_state_are_parameterized(self):
        cursor = FakeCursor(rows=[])

        with database_connection(cursor):
            database.get_users("ali", 7)

        query, parameters = cursor.executed[0]
        self.assertIn("LEFT JOIN Subscriptions", query)
        self.assertIn("a.username ILIKE %s", query)
        self.assertEqual(parameters, [7, 7, "%ali%"])

    def test_subscribe_to_user_prevents_self_subscription_in_sql(self):
        cursor = FakeCursor(returned_id=1)

        with database_connection(cursor):
            database.subscribe_to_user(7, 8)

        query, parameters = cursor.executed[0]
        self.assertIn("id <> %s", query)
        self.assertEqual(parameters, (7, 8, 7))

    def test_unsubscribe_from_user_deletes_only_pair(self):
        cursor = FakeCursor()

        with database_connection(cursor):
            database.unsubscribe_from_user(7, 8)

        self.assertEqual(
            cursor.executed[0][1],
            (7, 8),
        )

    def test_delete_old_events_cleans_attendance_before_events(self):
        cursor = FakeCursor()

        with database_connection(cursor):
            database.delete_old_events()

        self.assertEqual(len(cursor.executed), 2)
        self.assertIn("DELETE FROM EventAttendance", cursor.executed[0][0])
        self.assertIn("DELETE FROM events", cursor.executed[1][0])
        self.assertEqual(cursor.executed[0][1], cursor.executed[1][1])

    # ---- Teams ----

    def test_create_team_inserts_team_and_sets_is_team_flag(self):
        # fetchone_sequence: first call returns the new team id, second (UPDATE)
        # returns nothing (UPDATE does not call fetchone in our code).
        cursor = FakeCursor(fetchone_sequence=[(42,)])

        with database_connection(cursor):
            team_id = database.create_team(7, "Green Gothenburg", "Gothenburg", "Sweden")

        self.assertEqual(team_id, 42)
        self.assertEqual(len(cursor.executed), 2)
        self.assertIn("INSERT INTO Teams", cursor.executed[0][0])
        self.assertIn("FROM TeamMembers", cursor.executed[0][0])
        self.assertEqual(
            cursor.executed[0][1],
            (7, "Green Gothenburg", "Gothenburg", "Sweden", None, 7),
        )
        self.assertIn("UPDATE Accounts", cursor.executed[1][0])
        self.assertIn("isTeam = TRUE", cursor.executed[1][0])
        self.assertEqual(cursor.executed[1][1], (7,))

    def test_create_team_strips_empty_city_and_country_to_none(self):
        cursor = FakeCursor(fetchone_sequence=[(5,)])

        with database_connection(cursor):
            team_id = database.create_team(3, "Team X", "", "")

        self.assertEqual(team_id, 5)
        _, city, country = cursor.executed[0][1][2], cursor.executed[0][1][2], cursor.executed[0][1][3]
        self.assertIsNone(cursor.executed[0][1][2])
        self.assertIsNone(cursor.executed[0][1][3])

    def test_create_team_returns_none_on_duplicate(self):
        import psycopg

        cursor = FakeCursor()

        def raise_unique_violation(query, parameters=None):
            cursor.executed.append((query, parameters))
            raise psycopg.errors.UniqueViolation()

        cursor.execute = raise_unique_violation

        with database_connection(cursor):
            team_id = database.create_team(7, "Duplicate Team", None, None)

        self.assertIsNone(team_id)

    def test_create_team_returns_none_for_existing_team_member(self):
        cursor = FakeCursor(fetchone_sequence=[None])

        with database_connection(cursor):
            team_id = database.create_team(7, "Another Team", None, None)

        self.assertIsNone(team_id)
        self.assertIn("WHERE member_id = %s", cursor.executed[0][0])
        self.assertEqual(cursor.executed[0][1], (7, "Another Team", None, None, None, 7))

    def test_delete_team_removes_owned_team_and_clears_team_flag(self):
        cursor = FakeCursor(fetchone_sequence=[(7,)])

        with database_connection(cursor):
            deleted = database.delete_team(42, 7)

        self.assertTrue(deleted)
        self.assertEqual(len(cursor.executed), 6)
        self.assertIn("SELECT admin_id", cursor.executed[0][0])
        self.assertEqual(cursor.executed[0][1], (42, 7))
        self.assertIn("DELETE FROM Subscriptions", cursor.executed[1][0])
        self.assertEqual(cursor.executed[1][1], (7,))
        self.assertIn("DELETE FROM TeamMembers", cursor.executed[2][0])
        self.assertEqual(cursor.executed[2][1], (42,))
        self.assertIn("DELETE FROM Pictures", cursor.executed[3][0])
        self.assertEqual(cursor.executed[3][1], (42,))
        self.assertIn("DELETE FROM Teams", cursor.executed[4][0])
        self.assertEqual(cursor.executed[4][1], (42,))
        self.assertIn("isTeam = FALSE", cursor.executed[5][0])
        self.assertEqual(cursor.executed[5][1], (7,))

    def test_delete_team_returns_false_for_non_owner(self):
        cursor = FakeCursor(fetchone_sequence=[None])

        with database_connection(cursor):
            deleted = database.delete_team(42, 7)

        self.assertFalse(deleted)
        self.assertEqual(len(cursor.executed), 1)
        self.assertNotIn("DELETE FROM", cursor.executed[0][0])

    def test_delete_account_cleans_id_and_username_references(self):
        cursor = FakeCursor(fetchone_sequence=[("alice",)])

        with database_connection(cursor):
            deleted = database.delete_account(7)

        self.assertTrue(deleted)
        self.assertEqual(len(cursor.executed), 5)
        self.assertIn("SELECT username FROM Accounts", cursor.executed[0][0])
        self.assertEqual(cursor.executed[0][1], (7,))
        self.assertIn("DELETE FROM Subscriptions", cursor.executed[1][0])
        self.assertEqual(cursor.executed[1][1], (7, 7))
        self.assertIn("DELETE FROM Trash", cursor.executed[2][0])
        self.assertEqual(cursor.executed[2][1], ("alice", "alice"))
        self.assertIn("DELETE FROM Events", cursor.executed[3][0])
        self.assertEqual(cursor.executed[3][1], ("alice",))
        self.assertIn("DELETE FROM Accounts", cursor.executed[4][0])
        self.assertEqual(cursor.executed[4][1], (7,))

    def test_delete_account_returns_false_without_deleting_missing_account(self):
        cursor = FakeCursor(fetchone_sequence=[None])

        with database_connection(cursor):
            deleted = database.delete_account(404)

        self.assertFalse(deleted)
        self.assertEqual(len(cursor.executed), 1)

    def test_join_team_allows_only_accounts_without_existing_team_membership(self):
        cursor = FakeCursor(returned_id=12)

        with database_connection(cursor):
            joined = database.join_team(4, 7)

        self.assertTrue(joined)
        query, parameters = cursor.executed[0]
        self.assertIn("NOT EXISTS (", query)
        self.assertIn("FROM Teams", query)
        self.assertIn("FROM TeamMembers", query)
        self.assertEqual(parameters, (4, 7, 4, 7, 7))

    def test_get_users_can_filter_to_current_team(self):
        cursor = FakeCursor(rows=[])

        with database_connection(cursor):
            database.get_users("ali", 7, 7)

        query, parameters = cursor.executed[0]
        self.assertIn("EXISTS", query)
        self.assertIn("current_membership.member_id = %s", query)
        self.assertIn("a.username ILIKE %s", query)
        self.assertEqual(parameters, [7, 7, "%ali%", 7, 7])

    def test_get_team_leaderboard_aggregates_attendance_per_member(self):
        cursor = FakeCursor(rows=[])

        with database_connection(cursor):
            database.get_team_leaderboard()

        query, parameters = cursor.executed[0]
        self.assertIn("COUNT(DISTINCT ea.username)", query)
        self.assertIn("JOIN Accounts attendee", query)
        self.assertIn("tm.member_id = attendee.id", query)
        self.assertIn("COUNT(e.id) AS event_count", query)
        self.assertIn("mc.member_count * ec.event_count", query)
        self.assertIn("* 100", query)
        self.assertIn("SUM(ea.attendee_count)", query)
        self.assertIn("mc.member_count", query)
        self.assertIn("kg_per_person_per_event", query)
        self.assertIn("NULLIF(mc.member_count * ec.event_count, 0)", query)
        self.assertIn("tr.amount * 10", query)
        self.assertIn("ORDER BY score DESC NULLS LAST", query)
        self.assertEqual(parameters, [])

    def test_get_team_profile_returns_team_and_leader_and_members(self):
        team = (4, "Book Club", "Gothenburg", "Sweden", 7, "alice", None)
        members = [(7, "alice", True), (9, "bob", False)]
        cursor = FakeCursor(rows=members, fetchone_sequence=[team])

        with database_connection(cursor):
            profile, team_members = database.get_team_profile(4)

        self.assertEqual(profile, team)
        self.assertEqual(team_members, members)
        self.assertEqual(len(cursor.executed), 2)
        team_query, team_parameters = cursor.executed[0]
        self.assertIn("t.id, t.name, t.city, t.country, t.admin_id", team_query)
        self.assertIn("t.admin_id = a.id", team_query)
        self.assertEqual(team_parameters, (4,))
        members_query, members_parameters = cursor.executed[1]
        self.assertIn("FROM TeamMembers tm", members_query)
        self.assertEqual(members_parameters, (4, 4))

    def test_get_team_profile_returns_empty_result_for_missing_team(self):
        cursor = FakeCursor(fetchone_sequence=[None])

        with database_connection(cursor):
            profile, members = database.get_team_profile(404)

        self.assertIsNone(profile)
        self.assertEqual(members, [])
        self.assertEqual(len(cursor.executed), 1)

    def test_get_event_by_id_returns_event_row(self):
        event = (
            12, "Book swap", "Sweden", "Gothenburg",
            "18:30:00", "2026-10-14", 57.7, 11.97, "alice",
        )
        cursor = FakeCursor(fetchone_sequence=[event])

        with database_connection(cursor):
            result = database.get_event_by_id(12)

        self.assertEqual(result, event)
        query, parameters = cursor.executed[0]
        self.assertIn("FROM Events e", query)
        self.assertIn("WHERE e.id = %s", query)
        self.assertEqual(parameters, (12,))

    def test_get_event_by_id_returns_none_for_missing_event(self):
        cursor = FakeCursor(fetchone_sequence=[None])

        with database_connection(cursor):
            result = database.get_event_by_id(404)

        self.assertIsNone(result)


class RouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app_module.app.config.update(TESTING=True)
        cls.client = app_module.app.test_client()

    def setUp(self):
        self.client.get("/logout")

    def login_session(self, user_id=7):
        with self.client.session_transaction() as session:
            session["user_id"] = user_id

    @patch.object(app_module, "get_attending_event_ids", return_value={5})
    @patch.object(app_module, "get_event_by_id", return_value=(5, "Event"))
    @patch.object(app_module, "get_username_by_id", return_value="alice")
    @patch.object(app_module, "add_picture")
    def test_event_picture_upload_saves_file_and_records_relative_path(
        self, add_picture_mock, get_username, get_event, get_attending
    ):
        with TemporaryDirectory() as directory:
            picture_folder = Path(directory)
            with patch.object(app_module, "PICTURE_FOLDER", picture_folder):
                self.login_session()
                response = self.client.post(
                    "/events/5/pictures",
                    data={"picture": (BytesIO(b"image data"), "photo.png")},
                    content_type="multipart/form-data",
                )

            self.assertEqual(response.status_code, 302)
            add_picture_mock.assert_called_once()
            filename, uploader_id, event_id = add_picture_mock.call_args.args
            self.assertTrue(filename.startswith("event-5-"))
            self.assertTrue(filename.endswith(".png"))
            self.assertEqual(uploader_id, 7)
            self.assertEqual(event_id, 5)
            self.assertTrue((picture_folder / filename).is_file())

    @patch.object(app_module, "_get_teams", return_value=[])
    @patch.object(app_module, "get_users", return_value=[])
    @patch.object(app_module, "get_bio_by_id", return_value="A profile bio.")
    @patch.object(app_module, "get_username_by_id", return_value="alice")
    def test_logged_in_user_can_open_profile(
        self, get_username, get_bio, get_users, get_teams
    ):
        self.login_session()

        response = self.client.get("/profile")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"alice's Profile", response.data)
        self.assertIn(b"A profile bio.", response.data)

    @patch.object(app_module, "get_team_leaderboard", return_value=[])
    @patch.object(app_module, "get_team_event_ids", return_value=set())
    @patch.object(app_module, "get_events", return_value=[])
    @patch.object(app_module, "get_attending_event_ids", return_value=set())
    @patch.object(app_module, "get_username_by_id", return_value=None)
    def test_home_page_includes_team_leaderboard(
        self,
        get_username,
        get_attending,
        get_events,
        get_team_events,
        get_leaderboard,
    ):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        get_leaderboard.assert_called_once_with()

    @patch.object(app_module, "get_events", return_value=[])
    @patch.object(app_module, "get_attending_event_ids", return_value=set())
    @patch.object(app_module, "get_username_by_id", return_value=None)
    def test_guest_can_open_event_list(self, get_username, get_attending, get_events):
        response = self.client.get("/List")

        self.assertEqual(response.status_code, 200)
        get_events.assert_called_once()

    @patch.object(app_module, "get_username_by_id", return_value=None)
    def test_guest_is_redirected_from_attending_view(self, get_username):
        response = self.client.get("/List?view=attending")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    @patch.object(app_module, "get_events", return_value=[])
    @patch.object(app_module, "get_attending_event_ids", return_value={3})
    @patch.object(app_module, "get_username_by_id", return_value="alice")
    def test_attending_view_requires_user_and_filters_events(
        self, get_username, get_attending, get_events
    ):
        get_events.return_value = [
            (3, "Mine", None, None, "12:00", "2026-10-03"),
            (4, "Other", None, None, "12:00", "2026-10-03"),
        ]

        self.login_session()
        response = self.client.get("/List?view=attending")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Mine", response.data)
        self.assertNotIn(b"Other", response.data)

    @patch.object(app_module, "get_events", return_value=[])
    @patch.object(app_module, "get_attending_event_ids", return_value=set())
    @patch.object(app_module, "get_username_by_id", return_value="alice")
    def test_past_attending_view_passes_past_flag(
        self, get_username, get_attending, get_events
    ):
        self.login_session()
        response = self.client.get("/List?view=past-attending")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(get_events.call_args.args[-1])
        self.assertEqual(get_events.call_args.args[-2], "alice")

    @patch.object(app_module, "get_username_by_id", return_value=None)
    def test_guest_cannot_join_event(self, get_username):
        response = self.client.post("/events/3/attendance")

        self.assertEqual(response.status_code, 401)

    @patch.object(app_module, "attend_event", return_value=True)
    @patch.object(app_module, "get_username_by_id", return_value="alice")
    def test_logged_in_user_can_join_event(self, get_username, attend_event):
        self.login_session()
        response = self.client.post("/events/3/attendance")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, {"attending": True})
        attend_event.assert_called_once_with(3, "alice")

    @patch.object(app_module, "stop_attending_event", return_value=True)
    @patch.object(app_module, "get_username_by_id", return_value="alice")
    def test_logged_in_user_can_leave_event(self, get_username, stop_attending):
        self.login_session()
        response = self.client.delete("/events/3/attendance")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"attending": False})
        stop_attending.assert_called_once_with(3, "alice")

    @patch.object(app_module, "get_username_by_id", return_value=None)
    def test_guest_cannot_subscribe(self, get_username):
        response = self.client.post("/subscriptions/8")

        self.assertEqual(response.status_code, 401)

    @patch.object(app_module, "subscribe_to_user", return_value=True)
    def test_logged_in_user_can_subscribe(self, subscribe_to_user):
        self.login_session(7)
        response = self.client.post("/subscriptions/8")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, {"subscribed": True})
        subscribe_to_user.assert_called_once_with(7, 8)

    @patch.object(app_module, "unsubscribe_from_user", return_value=True)
    def test_logged_in_user_can_unsubscribe(self, unsubscribe_from_user):
        self.login_session(7)
        response = self.client.delete("/subscriptions/8")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"subscribed": False})
        unsubscribe_from_user.assert_called_once_with(7, 8)

    @patch.object(app_module, "get_users", return_value=[])
    def test_user_directory_passes_search_and_current_user(self, get_users):
        self.login_session(7)
        response = self.client.get("/users?q=ali")

        self.assertEqual(response.status_code, 200)
        get_users.assert_called_once_with("ali", 7, None)

    @patch.object(app_module, "get_users", return_value=[])
    def test_user_directory_can_filter_to_current_team(self, get_users):
        self.login_session(7)
        response = self.client.get("/users?q=ali&view=team")

        self.assertEqual(response.status_code, 200)
        get_users.assert_called_once_with("ali", 7, 7)

    @patch.object(app_module, "add_events", return_value=21)
    @patch.object(app_module, "get_username_by_id", return_value="alice")
    def test_create_event_adds_event_for_logged_in_user(self, get_username, add_events):
        self.login_session(7)
        response = self.client.post(
            "/events",
            json={
                "event_name": "Meetup",
                "country": "Sweden",
                "city": "Gothenburg",
                "time": "18:30",
                "date": "2026-10-03",
                "latitude": "57.7",
                "longitude": "11.97",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, {"id": 21})
        self.assertEqual(add_events.call_args.args[-1], "alice")

    @patch.object(app_module, "get_username_by_id", return_value=None)
    def test_guest_cannot_create_event(self, get_username):
        response = self.client.post("/events", json={})

        self.assertEqual(response.status_code, 400)

    # ---- Create Team route ----

    def test_guest_cannot_create_team(self):
        response = self.client.post(
            "/create-team",
            data={"team_name": "Green Squad", "city": "Gothenburg", "country": "Sweden"},
        )

        self.assertEqual(response.status_code, 401)

    def test_guest_cannot_join_team(self):
        response = self.client.post("/teams/4/membership")

        self.assertEqual(response.status_code, 401)

    @patch.object(app_module, "join_team", return_value=True)
    def test_logged_in_user_can_join_team(self, mock_join_team):
        self.login_session(7)
        response = self.client.post("/teams/4/membership")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, {"joined": True})
        mock_join_team.assert_called_once_with(4, 7)

    @patch.object(app_module, "join_team", return_value=False)
    def test_user_cannot_join_a_second_team(self, mock_join_team):
        self.login_session(7)
        response = self.client.post("/teams/9/membership")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json,
            {"error": "The team does not exist, or you already joined it."},
        )
        mock_join_team.assert_called_once_with(9, 7)

    def test_guest_cannot_delete_team(self):
        response = self.client.delete("/teams/4")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json,
            {"error": "You must be logged in to delete a team."},
        )

    def test_guest_cannot_delete_account(self):
        response = self.client.delete("/account")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json,
            {"error": "You must be logged in to delete your account."},
        )

    @patch.object(app_module, "delete_account", return_value=True)
    def test_logged_in_user_can_delete_only_their_session_account(self, mock_delete_account):
        self.login_session(23)

        response = self.client.delete("/account")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"deleted": True})
        mock_delete_account.assert_called_once_with(23)
        with self.client.session_transaction() as session:
            self.assertNotIn("user_id", session)

    @patch.object(app_module, "delete_account", return_value=False)
    def test_account_delete_returns_not_found_when_database_delete_fails(
        self, mock_delete_account
    ):
        self.login_session(23)

        response = self.client.delete("/account")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json,
            {"error": "Account not found or could not be deleted."},
        )
        mock_delete_account.assert_called_once_with(23)

    @patch.object(app_module, "delete_team", return_value=True)
    def test_team_owner_can_delete_team(self, mock_delete_team):
        self.login_session(7)
        response = self.client.delete("/teams/4")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"deleted": True})
        mock_delete_team.assert_called_once_with(4, 7)

    @patch.object(app_module, "delete_team", return_value=False)
    def test_user_cannot_delete_team_they_do_not_own(self, mock_delete_team):
        self.login_session(7)
        response = self.client.delete("/teams/4")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json,
            {"error": "Team not found or you are not its owner."},
        )
        mock_delete_team.assert_called_once_with(4, 7)

    @patch.object(app_module, "delete_team", return_value=True)
    def test_team_delete_uses_team_id_from_url(self, mock_delete_team):
        self.login_session(23)

        response = self.client.delete("/teams/987")

        self.assertEqual(response.status_code, 200)
        mock_delete_team.assert_called_once_with(987, 23)

    @patch.object(app_module, "create_team", return_value=1)
    def test_logged_in_user_can_create_team(self, mock_create_team):
        self.login_session(7)
        response = self.client.post(
            "/create-team",
            data={"team_name": "Green Squad", "city": "Gothenburg", "country": "Sweden"},
        )

        self.assertEqual(response.status_code, 302)  # redirect to home
        mock_create_team.assert_called_once_with(
            7, "Green Squad", "Gothenburg", "Sweden", ""
        )

    @patch.object(app_module, "create_team", return_value=1)
    def test_create_team_without_location_is_allowed(self, mock_create_team):
        self.login_session(7)
        response = self.client.post(
            "/create-team",
            data={"team_name": "Wanderers", "city": "", "country": ""},
        )

        self.assertEqual(response.status_code, 302)
        mock_create_team.assert_called_once_with(7, "Wanderers", None, None, "")

    @patch.object(app_module, "create_team", return_value=1)
    def test_create_team_requires_team_name(self, mock_create_team):
        self.login_session(7)
        response = self.client.post(
            "/create-team",
            data={"team_name": "", "city": "Gothenburg", "country": "Sweden"},
        )

        self.assertEqual(response.status_code, 400)
        mock_create_team.assert_not_called()

    @patch.object(app_module, "create_team", return_value=None)
    def test_create_team_renders_error_if_account_already_has_team(self, mock_create_team):
        self.login_session(7)
        response = self.client.post(
            "/create-team",
            data={"team_name": "Second Team", "city": "", "country": ""},
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn(b"Your account already has a team.", response.data)
        self.assertNotIn(b'"error"', response.data)


def test_category(test_case):
    name = test_case._testMethodName.lower()
    if "team" in name:
        return "Teams"
    if "subscr" in name:
        return "User subscriptions"
    if "event" in name or "attend" in name:
        return "Events"
    if "user" in name:
        return "Users"
    return "Database and general behavior"


def run_categorized_tests():
    discovered = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    categorized = {}

    def iter_test_cases(suite):
        for test in suite:
            if isinstance(test, unittest.TestSuite):
                yield from iter_test_cases(test)
            else:
                yield test

    for test_case in iter_test_cases(discovered):
        category = test_category(test_case)
        categorized.setdefault(category, unittest.TestSuite()).addTest(test_case)

    all_successful = True
    for category, suite in categorized.items():
        print(f"\n=== {category} ===", flush=True)
        result = unittest.TextTestRunner(
            stream=sys.stdout,
            verbosity=2,
        ).run(suite)
        all_successful = all_successful and result.wasSuccessful()

    return 0 if all_successful else 1


if __name__ == "__main__":
    raise SystemExit(run_categorized_tests())