import os
import threading
import time as time_module
from uuid import uuid4
from datetime import date, time
import psycopg
from user_info import UserInfo
from werkzeug.utils import secure_filename

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_from_directory,
    session,
    redirect,
    url_for,
)
from picture import PICTURE_FOLDER

from database.database import (
    add_events,
    add_picture,
    attend_event,
    change_password,
    create_team,
    delete_team,
    delete_event,
    delete_old_events,
    delete_old_pictures,
    get_old_event_picture_paths,
    get_db_connection,
    get_events,
    get_events_by_team,
    get_events_by_username,
    get_event_by_id,
    get_attending_event_ids,
    get_bio_by_id,
    get_team_members,
    get_team_profile,
    get_team_event_ids,
    get_team_leaderboard,
    get_created_events_with_attendees,
    get_teams,
    get_users,
    join_team,
    leave_team,
    get_username_by_id,
    get_user_profile,
    login_to_account,
    signup_for_account,
    stop_attending_event,
    subscribe_to_user,
    update_event,
    update_bio,
    unsubscribe_from_user,
    add_trash,
    get_trash,
    get_trash_by_event,
    add_trash_location,
    get_trash_locations,
    delete_old_trash_locations,
    create_event_from_trash_location,
    pictures_for_event,
    pictures_for_team,
    pictures_for_user,
)

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
    is_team_leader = False
    user_id = session.get("user_id")
    if user_id is not None:
        try:
            username = get_username_by_id(user_id)
            is_team_leader = bool(get_team_members(user_id))
        except Exception:
            username = None
    return {
        "current_username": username,
        "is_team_leader": is_team_leader,
    }


def cleanup_old_events_daily():
    while True:
        try:
            old_event_picture_paths = get_old_event_picture_paths()
            old_picture_paths = delete_old_pictures()
            deleted_count = delete_old_events()
            deleted_locations = delete_old_trash_locations()
            for picture_path in set(old_event_picture_paths + old_picture_paths):
                (PICTURE_FOLDER / picture_path).unlink(missing_ok=True)
            app.logger.info(
                "Deleted %s old events, %s old trash locations, and %s old pictures",
                deleted_count,
                deleted_locations,
                len(set(old_event_picture_paths + old_picture_paths)),
            )
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
    user_id = session.get("user_id")
    username = get_username_by_id(user_id)
    attending_event_ids = get_attending_event_ids(username) if username else set()
    return render_template(
        "index.html",
        events=get_events(),
        trash_locations=[
            location.as_dict() for location in get_trash_locations()
        ],
        attending_event_ids=attending_event_ids,
        team_event_ids=get_team_event_ids(user_id) if user_id else set(),
        leaderboard=get_team_leaderboard(),
    )

@app.route("/profile", methods=["GET", "POST"]) # GET requests data from the server, without changing anything, POST: sends data to the server, to create or update something
def organizer_profile():
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    username = get_username_by_id(user_id)
    if username is None:
        session.pop("user_id", None)
        return redirect(url_for("login"))

    if request.method == "POST":
        if request.form.get("form_action") == "change_password": #database method
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            password_error = None

            if not current_password:
                password_error = "Enter your current password."
            elif not new_password:
                password_error = "Enter a new password."
            elif len(new_password) > 20:
                password_error = "Your new password must be 20 characters or fewer."
            elif login_to_account(username, current_password) != user_id:
                password_error = "Your current password is incorrect."

            if password_error:
                return render_template(
                    "Profile.html",
                    user=UserInfo(id=user_id, username=username),
                    bio=get_bio_by_id(user_id) or "",
                    password_error=password_error,
                    teams=_get_teams("", user_id),
                    users=get_users("", user_id),
                ), 400

            if change_password(username, new_password) is None:
                return render_template(
                    "Profile.html",
                    user=UserInfo(id=user_id, username=username),
                    bio=get_bio_by_id(user_id) or "",
                    password_error="Your password could not be changed. Please try again.",
                    teams=_get_teams("", user_id),
                    users=get_users("", user_id),
                ), 500
            return redirect(url_for("organizer_profile", password_saved="1"))

        bio = request.form.get("bio", "")
        if len(bio) > 500:
            return render_template(
                "Profile.html",
                user=UserInfo(id=user_id, username=username),
                bio=bio,
                bio_error="Your bio must be 500 characters or fewer.",
                teams=_get_teams("", user_id),
                users=get_users("", user_id),
            ), 400
        update_bio(user_id, bio.strip())
        return redirect(url_for("organizer_profile", saved="1"))

    team_search = request.args.get("team_q", "").strip() #Strip() removes whitespace
    user_search = request.args.get("user_q", "").strip()
    return render_template(
        "Profile.html",
        user=UserInfo(id=user_id, username=username),
        bio=get_bio_by_id(user_id) or "",
        bio_saved=request.args.get("saved") == "1",
        password_saved=request.args.get("password_saved") == "1",
        teams=_get_teams(team_search, user_id),
        team_search=team_search,
        users=get_users(user_search, user_id),
        user_search=user_search,
    )


@app.route("/List")
def event_list():
    sort_by = request.args.get("sort", "date_asc")
    sort_options = {
        "date_asc": "Date: soonest first",
        "date_desc": "Date: latest first",
        "name_asc": "Name: A-Z",
        "name_desc": "Name: Z-A",
        "city_asc": "City: A-Z",
    }
    if sort_by not in sort_options:
        sort_by = "date_asc"
    search = request.args.get("q", "").strip()
    subscribed_only = request.args.get("view") == "subscribed"
    team_only = request.args.get("view") == "teams"
    attending_only = request.args.get("view") == "attending"
    past_attending = request.args.get("view") == "past-attending"
    user_id = session.get("user_id")
    if (subscribed_only or team_only or attending_only or past_attending) and user_id is None:
        return redirect(url_for("login"))
    username = get_username_by_id(user_id) if user_id is not None else None
    attending_event_ids = get_attending_event_ids(username) if username else set()
    events = get_events(
        sort_by,
        search,
        user_id if subscribed_only else None,
        username if past_attending else None,
        past_attending,
        team_member_id=user_id if team_only else None,
    )
    if attending_only:
        events = [event for event in events if event[0] in attending_event_ids]
    return render_template(
        "List.html",
        events=events,
        sort_by=sort_by,
        sort_options=sort_options,
        search=search,
        subscribed_only=subscribed_only,
        team_only=team_only,
        attending_only=attending_only,
        past_attending=past_attending,
        attending_event_ids=attending_event_ids,
    )


@app.route("/events/<int:event_id>")
def event_detail(event_id):
    event = get_event_by_id(event_id)
    if event is None:
        return render_template("Event.html", event=None), 404
    username = get_username_by_id(session.get("user_id"))
    attending_event_ids = get_attending_event_ids(username) if username else set()
    return render_template(
        "Event.html",
        event=event,
        is_attending=event_id in attending_event_ids,
        pictures=pictures_for_event(event_id),
        trash=get_trash_by_event(event_id),
    )


@app.get("/users/<int:user_id>")
def user_detail(user_id):
    profile = get_user_profile(user_id)
    if profile is None:
        return render_template("User.html", profile=None), 404
    return render_template(
        "User.html",
        profile=profile,
        events=get_events_by_username(profile[1]),
        pictures=pictures_for_user(profile[0]),
    )


@app.get("/teams/<int:team_id>")
def team_detail(team_id):
    team, members = get_team_profile(team_id)
    if team is None:
        return render_template("Team.html", team=None), 404
    return render_template(
        "Team.html",
        team=team,
        members=members,
        events=get_events_by_team(team_id),
        pictures=pictures_for_team(team_id),
    )


@app.post("/events/<int:event_id>/pictures")
def upload_event_picture(event_id): 
    user_id = session.get("user_id") 
    username = get_username_by_id(user_id) if user_id is not None else None
    if username is None: 
        return redirect(url_for("login")) 
    event = get_event_by_id(event_id)
    if event is None:
        return render_template("Event.html", event=None), 404
    if event_id not in get_attending_event_ids(username):
        return redirect(url_for("event_detail", event_id=event_id))

    upload = request.files.get("picture")
    filename = secure_filename(upload.filename) if upload else ""
    if not upload or not filename:
        return redirect(url_for("event_detail", event_id=event_id))
    extension = os.path.splitext(filename)[1].lower()
    if extension not in {".gif", ".jpeg", ".jpg", ".png", ".webp"}:
        return redirect(url_for("event_detail", event_id=event_id))

    PICTURE_FOLDER.mkdir(exist_ok=True)
    filename = f"event-{event_id}-{uuid4().hex}{extension}"
    picture_path = PICTURE_FOLDER / filename
    upload.save(picture_path)
    try:
        add_picture(filename, user_id, event_id)
    except psycopg.Error:
        picture_path.unlink(missing_ok=True)
        raise
    return redirect(url_for("event_detail", event_id=event_id))


@app.get("/pictures/<path:filename>")
def serve_picture(filename):
    """Serve local dummy pictures without involving the database."""
    return send_from_directory(PICTURE_FOLDER, filename)


@app.route("/created-events")
def created_events():
    username = get_username_by_id(session.get("user_id"))
    if username is None:
        return redirect(url_for("login"))
    return render_template(
        "CreatedEvents.html",
        events=get_created_events_with_attendees(username),
    )


def get_authenticated_username():
    return get_username_by_id(session.get("user_id"))


@app.put("/events/<int:event_id>")
def edit_event(event_id):
    username = get_authenticated_username()
    if username is None:
        return jsonify(error="You must be logged in to edit an event."), 401

    data = request.get_json(silent=True) or request.form
    required_fields = ("event_name", "time", "date", "latitude", "longitude")
    missing_fields = [field for field in required_fields if not str(data.get(field, "")).strip()]
    if missing_fields:
        return jsonify(error="Missing fields: " + ", ".join(missing_fields)), 400

    try:
        event_id = update_event(
            event_id,
            username,
            str(data["event_name"]).strip(),
            str(data.get("country", "")).strip() or None,
            str(data.get("city", "")).strip() or None,
            time.fromisoformat(str(data["time"])),
            date.fromisoformat(str(data["date"])),
            float(data["latitude"]),
            float(data["longitude"]),
            str(data.get("bio", "")).strip() or None,
        )
    except (TypeError, ValueError):
        return jsonify(error="Invalid event data."), 400

    if event_id is None:
        return jsonify(error="Event not found or you are not its Team."), 404
    return jsonify(id=event_id), 200


@app.delete("/events/<int:event_id>")
def remove_event(event_id):
    username = get_authenticated_username()
    if username is None:
        return jsonify(error="You must be logged in to delete an event."), 401
    if not delete_event(event_id, username):
        return jsonify(error="Event not found or you are not its Team."), 404
    return jsonify(deleted=True), 200

@app.route("/events/<int:event_id>/log", methods=["PUT", "GET"])
def log_trash(event_id):
    username = get_authenticated_username()
    amount = request.args['amount']
    type = request.args['type']
    if username is None:
         return jsonify(error="You must be logged in to log trash."), 401
    event = get_event_by_id(event_id)
    if event is None:
        return jsonify(error="Event not found."), 404
    event_date = date.fromisoformat(event[5])
    if event_date > date.today():
        return jsonify(error="You can only log trash for events that have already taken place."), 400
    if amount is '':
        return jsonify(error="Amount must not be NULL"), 400
    if int(amount) < 1:
        return jsonify(error="Amount must be greater than 1"), 400
    if type is '':
        return jsonify(error="Type must not be NULL"), 400
    if not add_trash(event_id, username, amount, type):
        return jsonify(error="Could not log trash."), 401
    return '', 204

@app.post("/events/<int:event_id>/attendance")
def join_event(event_id):
    username = get_username_by_id(session.get("user_id"))
    if username is None:
        return jsonify(error="You must be logged in to attend an event."), 401
    if not attend_event(event_id, username):
        return jsonify(error="The event does not exist or you are already attending it."), 400
    return jsonify(attending=True), 201


@app.delete("/events/<int:event_id>/attendance")
def leave_event(event_id):
    username = get_username_by_id(session.get("user_id"))
    if username is None:
        return jsonify(error="You must be logged in to leave an event."), 401
    stop_attending_event(event_id, username)
    return jsonify(attending=False)


def _get_teams(search, current_user_id):
    """Return teams with the current account's membership state."""
    return get_teams(search, current_user_id)


@app.post("/teams/<int:team_id>/membership")
def join_team_route(team_id):
    member_id = session.get("user_id")
    if member_id is None:
        return jsonify(error="You must be logged in to join a team."), 401
    if not join_team(team_id, member_id):
        return jsonify(error="The team does not exist, or you already joined it."), 400
    return jsonify(joined=True), 201


@app.delete("/teams/<int:team_id>/membership")
def leave_team_route(team_id):
    member_id = session.get("user_id")
    if member_id is None:
        return jsonify(error="You must be logged in to leave a team."), 401
    leave_team(team_id, member_id)
    return jsonify(joined=False)


@app.delete("/teams/<int:team_id>")
def delete_team_route(team_id):
    admin_id = session.get("user_id")
    if admin_id is None:
        return jsonify(error="You must be logged in to delete a team."), 401
    if not delete_team(team_id, admin_id):
        return jsonify(error="Team not found or you are not its owner."), 404
    return jsonify(deleted=True)


@app.post("/subscriptions/<int:user_id>")
def subscribe(user_id):
    subscriber_id = session.get("user_id")
    if subscriber_id is None:
        return jsonify(error="You must be logged in to subscribe."), 401
    if not subscribe_to_user(subscriber_id, user_id):
        return jsonify(error="That account cannot be subscribed to."), 400
    return jsonify(subscribed=True), 201


@app.delete("/subscriptions/<int:user_id>")
def unsubscribe(user_id):
    subscriber_id = session.get("user_id")
    if subscriber_id is None:
        return jsonify(error="You must be logged in to unsubscribe."), 401
    unsubscribe_from_user(subscriber_id, user_id)
    return jsonify(subscribed=False)

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
        else:
            return jsonify(error="Invalid action"), 400
        if account_id:
            session["user_id"] = account_id
            if action == "login":
                return render_template(
                    "login.html",
                    message="You successfully logged in. Welcome back!",
                    message_type="success",
                )
            if action == "signup":
                return render_template(
                    "login.html",
                    message="Account created! Welcome to Rubby.",
                    message_type="success",
                )
        else:
            if action == "login":
                return render_template(
                    "login.html",
                    message="Incorrect username or password. Please try again.",
                    message_type="error",
                )
            if action == "signup":
                return render_template(
                    "login.html",
                    message="That username is already taken. Please choose another.",
                    message_type="error",
                )
    except (psycopg.Error) as exc:
        return render_template(
            "login.html",
            message=f"Something went wrong: {exc}",
            message_type="error",
        )

    return render_template("login.html")

@app.post("/create-team")
def create_team_route():
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify(error="You must be logged in to create a team."), 401

    data = request.get_json(silent=True) or request.form
    team_name = str(data.get("team_name", "")).strip()
    if not team_name:
        return jsonify(error="Team name is required."), 400

    city = str(data.get("city", "")).strip() or None
    country = str(data.get("country", "")).strip() or None

    team_id = create_team(user_id, team_name, city, country)
    if team_id is None:
        return render_template(
            "login.html",
            message="Your account already has a team.",
            message_type="error",
            create_team_error=True,
        ), 409

    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    # Remove the logged-in user's id from the session. pop(..., None) avoids a
    # KeyError if they weren't logged in. After this the banner shows "guest".
    session.pop("user_id", None)
    # Send them back to the home page.
    return redirect(url_for("login"))

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
            get_username_by_id(session["user_id"]),
        )
    except (TypeError, ValueError) as exc:
        return jsonify(error=f"Invalid event data: {exc}"), 400

    return jsonify(id=event_id), 201


def _coordinates_from_request(data):
    try:
        latitude = float(data["latitude"])
        longitude = float(data["longitude"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("Coordinates must be numbers.") from None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("Coordinates are outside the valid range.")
    return latitude, longitude


@app.post("/trash-locations")
def create_trash_location():
    username = get_authenticated_username()
    if username is None:
        return jsonify(error="You must be logged in to create a trash location."), 401
    data = request.get_json(silent=True) or request.form
    try:
        latitude, longitude = _coordinates_from_request(data)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    location = add_trash_location(latitude, longitude, username)
    return jsonify(location=location.as_dict()), 201


@app.post("/trash-locations/<int:location_id>/events")
def create_event_at_trash_location(location_id):
    username = get_authenticated_username()
    if username is None:
        return jsonify(error="You must be logged in to create an event."), 401
    data = request.get_json(silent=True) or request.form
    required_fields = ("event_name", "time", "date")
    missing_fields = [field for field in required_fields if not str(data.get(field, "")).strip()]
    if missing_fields:
        return jsonify(error="Missing fields: " + ", ".join(missing_fields)), 400
    try:
        event_id = create_event_from_trash_location(
            location_id,
            str(data["event_name"]).strip(),
            str(data.get("country", "")).strip() or None,
            str(data.get("city", "")).strip() or None,
            time.fromisoformat(str(data["time"])),
            date.fromisoformat(str(data["date"])),
            username,
            str(data.get("bio", "")).strip() or None,
        )
    except (TypeError, ValueError) as exc:
        return jsonify(error=f"Invalid event data: {exc}"), 400
    if event_id is None:
        return jsonify(error="Trash location not found or expired."), 404
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

@app.route("/debug/trash")
def debug_trash():
	return jsonify(get_trash()), 200


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        start_cleanup_scheduler()
    app.run(host="0.0.0.0", port=5000, debug=True)
