"""
Flask application entrypoint.

Kept intentionally simple (single-file) so teammates new to Flask can read it
top-to-bottom. It builds on the basic example and adds a database connection to PostgreSQL, configured entirely through
environment variables (see .env.example). Nothing secret is hard-coded here.
"""

import os

from flask import Flask, jsonify, render_template

from event import create_sample_events

# TODO for 1.1
# To display List.html, import render_template and call it from a route.
# The template expects one variable named "events": a list of event objects.
# Each event should have these names, matching database/schema.sql:
# event.id, event.event_name, event.country, event.city, event.time, event.date
# Example: render_template("List.html", events=events)

# The database connection lives in the database package (database/database.py), so the
# connection details are defined in exactly one place. Feature/CRUD functions
# should also live in the database package and import get_db_connection there.
from database.database import get_db_connection

# Flask searches the templates/ directory relative to this application file.
app = Flask(__name__, template_folder="templates")


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/List")
def event_list():
    # render_template looks for List.html in the folder configured above.
    # For now, `events` contains Python objects instead of database results.
    events = create_sample_events()
    return render_template("List.html", events=events)


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
    # Bind to 0.0.0.0 so the container port is reachable from the host.
    # debug=True enables the auto-reloader, which pairs with the volume mount
    # in docker-compose.yml to give live code reloading during development.
    app.run(host="0.0.0.0", port=5000, debug=True)
