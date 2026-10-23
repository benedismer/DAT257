# Rubby

Rubby is a Flask and PostgreSQL web application for organizing community
trash-picking events. It runs as two Docker Compose services:

- `web`: the Flask application
- `db`: PostgreSQL 16

The application is available at
[http://localhost:5000](http://localhost:5000).

## Quick start

Docker Desktop (or Docker Engine), Docker Compose, and `make` are required.
See [docker/README.md](docker/README.md) for platform-specific installation
instructions.

```bash
cp docker/.env.example .env
make up-build
make seed-reset
```

Open [http://localhost:5000](http://localhost:5000). Seed accounts all use the
password `password`.

The seed data includes extra pictures for testing pagination:

- `River cleanup` has more than three pictures.
- Alice's user profile has more than three pictures.
- Clean Coast's team profile has more than three pictures.

## Current features

### Accounts and profiles

- Sign up, log in, log out, and change password.
- Edit a profile bio with a 500-character limit.
- Delete the currently logged-in account only.
- Account deletion removes the account's events, pictures, attendance,
  subscriptions, trash records, team membership, and owned team data.

### Events

- Create events by clicking the map.
- Create events from a saved trash location.
- Edit or delete events created by the current user.
- Join and leave events.
- Upload pictures when participating in an event.
- Log collected trash after an event has taken place.
- Event bios have a 500-character limit.
- Event pages show collected kilograms and paginate pictures three per page.

### Map

- OpenStreetMap tiles are used on the home page.
- Event popups show the event name, date, time, location when available,
  organizer, and attendance status.
- Event creation forms remain bounded inside the map when zooming.
- Users can mark a trashy location and later turn it into a cleanup event.

### Teams and subscriptions

- Create a team with an optional 500-character bio.
- Search for teams and users from the profile page.
- Join or leave a team.
- Team owners can delete their own team.
- Team pages show members, events, team bio, and paginated pictures.
- Subscribe to users/teams and view subscribed event feeds.

### Leaderboard

The home page ranks teams by average attendance percentage. It also shows
**average kilograms per person per event**, calculated as:

```text
total collected kilograms
--------------------------------
team members × team events
```

Trash entries whose type contains `bag` count as 10 kg per bag; other entries
count their stored amount directly as kilograms.

## Development commands

Run these from the project root:

| Command | Description |
|---------|-------------|
| `make up` | Start the application and database |
| `make up-build` | Build images and start the stack |
| `make down` | Stop containers and keep database data |
| `make teardown` | Stop containers and delete database/picture data |
| `make seed` | Add development seed data |
| `make seed-reset` | Clear and recreate development seed data |
| `make test` | Run tests inside a disposable web container |
| `make logs` | Follow logs from both services |
| `make db-shell` | Open a PostgreSQL shell |

Application files are mounted into the web container, so application edits reload
automatically in development.

## Database and schema

The schema is defined in [database/tables.sql](database/tables.sql). PostgreSQL
only runs the mounted initialization SQL when the database volume is empty.
After changing the schema during development, recreate the database:

```bash
make teardown
make up
```

This deletes local database data. The seed script also adds the team bio column
to existing development databases when needed.

## Testing

Tests are in [App/test.py](App/test.py) and use Python's `unittest` framework. The
recommended command is:

```bash
make test
```

Running `python3 -m unittest App/test.py` directly requires the dependencies in
`docker/requirements.txt`, including `psycopg`.

## Known limitations

- There is no production deployment configuration; Docker Compose is for local
  development.
- Account deletion is permanent and has no recovery workflow.
- Schema changes require a manual migration or a local database reset.
- The Flask development server and debug reloader should not be used in
  production.
- The map depends on the public OpenStreetMap tile service.
