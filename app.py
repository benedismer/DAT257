import os
import threading
import time as time_module
from datetime import date, time
import psycopg

from flask import Flask, jsonify, render_template, request, session, redirect, url_for

from database.database import add_events, delete_old_events, get_events, signup_for_account, login_to_account, get_username_by_id, get_db_connection, change_password

app = Flask(__name__, template_folder="templates")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me") # login session


@app.context_processor
def inject_current_username():
    """Runs before every template render and makes `current_username`
    available in ALL templates (so base.html's banner works everywhere
    without each route passing it in).

    Reads the logged-in user's id from the session and looks up their name.
    Returns None when nobody is logged in, or if the lookup fails (e.g. the
    database is unreachable) so a DB hiccup never breaks page rendering.
    """
    username = None
    user_id = session.get("user_id")
    if user_id is not None:
        try:
            username = get_username_by_id(user_id)
        except Exception:
            username = None
    return {"current_username": username}


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

@app.route("/login", methods=['GET', 'POST'])
def login():
    # GET -> just render page
    if request.method == "GET": 
        return render_template("login.html")
    # POST -> login button or sign up button has been pressed
    data = request.get_json(silent=True) or request.form
    required_fields = ("username", "password", "action")
    missing_fields = [field for field in required_fields if not str(data.get(field, "")).strip()]
    if missing_fields:
        return jsonify(error="Missing fields: " + ", ".join(missing_fields)), 400
    try:
        username = str(data.get("username", "")).strip() 
        password = str(data.get("password", "")) 
        action = str(data.get("action", "")).strip()
        if action == "login":
            account_id = login_to_account(username, password)
        elif action == "signup":
            account_id = signup_for_account(username, password)
            if account_id:
                account_id = login_to_account(username, password)
        elif action == "change_pw":
            if username == get_username_by_id(session.get("user_id")):
                account_id = change_password(username, password)    
            else:
                return render_template("unsuccessful_pw_change.html")
        else:
            return jsonify(error="Invalid action"), 400
        if account_id: # successful login
            session["user_id"] = account_id          # remembers the user
            if action == "login":
                return render_template("successful_login.html")
            if action == "signup":
                return render_template("successful_signup.html")
            if action == "change_pw":
                return render_template("successful_pw_change.html")
    except (psycopg.Error) as exc:
        return jsonify(error=f"Invalid login data: {exc}"), 401

    return render_template("login.html") # FIX: is this correct?

@app.route("/logout")
def logout():
    # Remove the logged-in user's id from the session. pop(..., None) avoids a
    # KeyError if they weren't logged in. After this the banner shows "guest".
    session.pop("user_id", None)
    # Send them back to the home page.
    return redirect(url_for("index"))

@app.post("/events")
def create_event():
    data = request.get_json(silent=True) or request.form
    required_fields = ("event_name", "time", "date", "latitude", "longitude")
    missing_fields = [field for field in required_fields if not str(data.get(field, "")).strip()]
    if missing_fields:
        return jsonify(error="Missing fields: " + ", ".join(missing_fields)), 400
    if get_username_by_id(session.get("user_id")) == None:
        # u r only allowed to create an event if you are logged in
        return jsonify(error="You must be logged in to create an event."), 401
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
