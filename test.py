import unittest
from datetime import date, time
from unittest.mock import MagicMock, patch

import app as app_module
from database import database


class FakeCursor:
    def __init__(self, rows=None, returned_id=None):
        self.rows = rows or []
        self.returned_id = returned_id
        self.executed = []
        self.rowcount = 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, parameters=None):
        self.executed.append((query, parameters))

    def fetchone(self):
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
        self.assertIn("s.user_subscribed = %s", query)
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

    def test_get_bio_by_id(self):
        cursor = FakeCursor(rows=[("I like organizing cleanups.",)])

        with database_connection(cursor):
            bio = database.get_bio_by_id(7)

        self.assertEqual(bio, "I like organizing cleanups.")
        self.assertEqual(cursor.executed[0][1], (7,))

    def test_update_bio_by_id(self):
        cursor = FakeCursor()

        with database_connection(cursor):
            updated = database.update_bio(7, "I like cleanups.")

        self.assertTrue(updated)
        self.assertEqual(cursor.executed[0][1], ("I like cleanups.", 7))


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

    @patch.object(app_module, "get_bio_by_id", return_value="I like cleanups.")
    @patch.object(app_module, "get_username_by_id", return_value="alice")
    def test_logged_in_user_can_open_profile(self, get_username, get_bio):
        self.login_session()

        response = self.client.get("/profile")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"alice's Profile", response.data)
        self.assertIn(b"I like cleanups.", response.data)

    @patch.object(app_module, "update_bio", return_value=True)
    @patch.object(app_module, "get_username_by_id", return_value="alice")
    def test_logged_in_user_can_update_bio(self, get_username, update_bio):
        self.login_session()

        response = self.client.post("/profile", data={"bio": "New bio"})

        self.assertEqual(response.status_code, 302)
        self.assertIn("/profile?saved=1", response.headers["Location"])
        update_bio.assert_called_once_with(7, "New bio")

    @patch.object(app_module, "update_bio")
    @patch.object(app_module, "get_username_by_id", return_value="alice")
    def test_profile_rejects_bio_over_500_characters(self, get_username, update_bio):
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


if __name__ == "__main__":
    unittest.main(verbosity=2)