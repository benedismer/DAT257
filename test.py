import unittest
from datetime import date, time
from unittest.mock import MagicMock, patch

import app as app_module
from database import database


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
        self.assertEqual(cursor.executed[0][1], (7, "Green Gothenburg", "Gothenburg", "Sweden"))
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

    @patch.object(
        app_module,
        "_get_teams",
        return_value=[(12, "Chess Club", "Oslo", "Norway", True, False)],
    )
    @patch.object(app_module, "get_users", return_value=[(8, "bob", False)])
    @patch.object(app_module, "get_bio_by_id", return_value="I like cleanups.")
    @patch.object(app_module, "get_username_by_id", return_value="alice")
    def test_logged_in_user_can_open_profile(
        self, get_username, get_bio, get_users, get_teams
    ):
        self.login_session()

        response = self.client.get("/profile")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"alice's Profile", response.data)
        self.assertIn(b"I like cleanups.", response.data)
        self.assertIn(b'class="bio-display"', response.data)
        self.assertIn(b'>Edit bio</button>', response.data)
        self.assertIn(b'id="bio-edit-form"', response.data)
        self.assertIn(b"hidden", response.data)
        self.assertIn(b"Chess Club", response.data)
        self.assertIn(b"bob", response.data)
        get_users.assert_called_once_with("", 7)
        get_teams.assert_called_once_with("", 7)

    @patch.object(app_module, "update_bio", return_value=True)
    @patch.object(app_module, "get_username_by_id", return_value="alice")
    def test_logged_in_user_can_update_bio(self, get_username, update_bio):
        self.login_session()

        response = self.client.post("/profile", data={"bio": "New bio"})

        self.assertEqual(response.status_code, 302)
        self.assertIn("/profile?saved=1", response.headers["Location"])
        update_bio.assert_called_once_with(7, "New bio")

    @patch.object(app_module, "change_password")
    @patch.object(app_module, "login_to_account", return_value=None)
    @patch.object(app_module, "_get_teams", return_value=[])
    @patch.object(app_module, "get_users", return_value=[])
    @patch.object(app_module, "get_bio_by_id", return_value="")
    @patch.object(app_module, "get_username_by_id", return_value="alice")
    def test_password_change_requires_correct_current_password(
        self, get_username, get_bio, get_users, get_teams, login, change_password
    ):
        self.login_session()

        response = self.client.post(
            "/profile",
            data={
                "form_action": "change_password",
                "current_password": "wrong",
                "new_password": "new-password",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Your current password is incorrect.", response.data)
        login.assert_called_once_with("alice", "wrong")
        change_password.assert_not_called()

    @patch.object(app_module, "change_password", return_value=7)
    @patch.object(app_module, "login_to_account", return_value=7)
    @patch.object(app_module, "get_username_by_id", return_value="alice")
    def test_logged_in_user_can_change_password(
        self, get_username, login, change_password
    ):
        self.login_session()

        response = self.client.post(
            "/profile",
            data={
                "form_action": "change_password",
                "current_password": "old-password",
                "new_password": "new-password",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/profile?password_saved=1", response.headers["Location"])
        login.assert_called_once_with("alice", "old-password")
        change_password.assert_called_once_with("alice", "new-password")

    @patch.object(app_module, "_get_teams", return_value=[])
    @patch.object(app_module, "get_users", return_value=[])
    @patch.object(app_module, "update_bio")
    @patch.object(app_module, "get_username_by_id", return_value="alice")
    def test_profile_rejects_bio_over_500_characters(
        self, get_username, update_bio, get_users, get_teams
    ):
        self.login_session()

        response = self.client.post("/profile", data={"bio": "x" * 501})

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"500 characters or fewer", response.data)
        update_bio.assert_not_called()

    def test_guest_is_redirected_from_profile(self):
        response = self.client.get("/profile")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

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
        get_users.assert_called_once_with("ali", 7)

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

    @patch.object(app_module, "create_team", return_value=1)
    def test_logged_in_user_can_create_team(self, mock_create_team):
        self.login_session(7)
        response = self.client.post(
            "/create-team",
            data={"team_name": "Green Squad", "city": "Gothenburg", "country": "Sweden"},
        )

        self.assertEqual(response.status_code, 302)  # redirect to home
        mock_create_team.assert_called_once_with(7, "Green Squad", "Gothenburg", "Sweden")

    @patch.object(app_module, "create_team", return_value=1)
    def test_create_team_without_location_is_allowed(self, mock_create_team):
        self.login_session(7)
        response = self.client.post(
            "/create-team",
            data={"team_name": "Wanderers", "city": "", "country": ""},
        )

        self.assertEqual(response.status_code, 302)
        mock_create_team.assert_called_once_with(7, "Wanderers", None, None)

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
    def test_create_team_returns_409_if_account_already_has_team(self, mock_create_team):
        self.login_session(7)
        response = self.client.post(
            "/create-team",
            data={"team_name": "Second Team", "city": "", "country": ""},
        )

        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main(verbosity=2)