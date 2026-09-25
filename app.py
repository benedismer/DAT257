import os
import threading
import time as time_module
from datetime import date, time

from flask import Flask, jsonify, render_template, request

from database.database import add_events, delete_old_events, get_events

from database.database import get_db_connection

app = Flask(__name__, template_folder="templates")


def cleanup_old_events_daily():
    while True:
        try:
            deleted_count = delete_old_events()
            app.logger.info("Deleted %s old events", deleted_count)
        except Exception:
            app.logger.exception("Could not delete old events")
        time_module.sleep(24 * 60 * 60)


def start_cleanup_scheduler():
    cleanup_thread = threading.Thread(
        target=cleanup_old_events_daily,
        name="old-event-cleanup",
        daemon=True,
    )
    cleanup_thread.start()


@app.route("/")
def index():
    return render_template("index.html", events=get_events())

@app.route("/List")
def event_list():
    return render_template("List.html", events=get_events())


@app.post("/events")
def create_event():
    data = request.get_json(silent=True) or request.form
    required_fields = ("event_name", "time", "date", "latitude", "longitude")
    missing_fields = [field for field in required_fields if not str(data.get(field, "")).strip()]
    if missing_fields:
        return jsonify(error="Missing fields: " + ", ".join(missing_fields)), 400

    try:
        country = str(data.get("country", "")).strip() or None
        city = str(data.get("city", "")).strip() or None
        event_id = add_events(
            data["event_name"].strip(),
            country,
            city,
            time.fromisoformat(data["time"]),
            date.fromisoformat(data["date"]),
            float(data["latitude"]),
            float(data["longitude"]),
        )
    except (TypeError, ValueError) as exc:
        return jsonify(error=f"Invalid event data: {exc}"), 400

    return jsonify(id=event_id), 201


@app.route("/health")
def health():
    """Simple health check that also verifies the DB is reachable.

    Handy for confirming the whole suite is wired up correctly: if you can hit
    /health and get {"database": "ok"}, the Flask container is talking to the
    Postgres container.
    """
    db_status = "ok"
    db_version = None
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                db_version = cur.fetchone()[0]
    except Exception as exc:  # noqa: BLE001 - surface any connection error
        db_status = f"error: {exc}"

    return jsonify(
        app="ok",
        database=db_status,
        database_version=db_version,
        map_api_key_configured=bool(os.environ.get("MAP_API_KEY")),
    )


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        start_cleanup_scheduler()
    app.run(host="0.0.0.0", port=5000, debug=True)
