# DAT257
Agile software project management

A web application built with **Flask** (Python) and **PostgreSQL**. Everything
runs in **Docker** containers. Each developer runs the whole
stack locally on their own computer.

---

## What you get

Docker is broadly speaking made up out of images, containers and volumes. An image is the blueprint of
your project and can be found in the Dockerfile. A container is the blueprint having been built and is now running the project. Containers are meant to be able to be teared up and down as you develop and change your project. It is really useful but the problem is that no data from the previous container is saved anywhere, all database data would dissapear on a teardown. Thats why databases is not only a container but also has a volume. A volume is storage that can be built and teared down individually from the containers so that a developer wanting to change one thing in the project doesnt mean the users of the webpage has to create a new account or similar thing like that. 

Two containers that run side by side:

| Container | What it is | Where you reach it |
|-----------|------------|--------------------|
| `web`     | The Flask app | http://localhost:5000 |
| `db`      | PostgreSQL 16 database | used by `web` internally |

The app has two routes to start with:

- `GET /` → `Hello, World!`
- `GET /health` → JSON showing whether the app can reach the database

Your source code is mounted into the `web` container, so when you edit a `.py`
file the server **reloads automatically** — no rebuild needed.

---

## Using Docker 

- **`docker-compose.yml`** defines the two containers (`web` and `db`) and wires
  them together on a private network. The app finds the database at the hostname
  `db` (that's why `POSTGRES_HOST=db` in `.env`).
- **`Dockerfile`** describes to docker how to build the `web` image (Python + our
  dependencies + the app code). It describes all the tools in the toolbox and how it is used.
- **`requirements.txt`** pins the exact Python packages. 
- **`.env`** (yours, local, git-ignored) holds credentials and the map API key. You can not 
   commit your login information to the database or things like that where everyone can see it
   but since docker controls everything abot the setup docker needs to know these things. The 
   .env file tells docker how to access all the things it needs on your individual computer
   without letting people on git or people inspecting your web page code know. 
  **`.env.example`** (committed) is the template. You can look here to see what docker needs 
  you to fill in into your personal .env file
- **`Makefile`** is just shortcuts for the `docker compose` commands above.
- The database's data lives in a Docker **volume** (`pgdata`) so it survives
  `make down`. Only `make teardown` deletes it.

---

## Docker installation guide

### Windows

1. Docker on Windows needs **WSL2** (a lightweight Linux layer). Open
   **PowerShell as Administrator** and run:
   ```powershell
   wsl --install
   ```
   Restart your computer if it asks you to.
2. Download and install **Docker Desktop** from
   https://www.docker.com/products/docker-desktop/ (choose the WSL2 backend when
   prompted — it's the default).
3. Launch **Docker Desktop** and wait until it says "Engine running".
4. **Recommended:** the `make` command doesn't exist in plain Windows. Either:
   - Run all project commands **inside a WSL2 Ubuntu terminal** (where `make`
     works — install it with `sudo apt update && sudo apt install make`), **or**
   - Use the raw `docker compose` commands from
     [Without make](#without-make-raw-docker-compose) in PowerShell.

Verify it works (in your terminal of choice):
```bash
docker --version
docker compose version
```

### macOS

1. Install **Docker Desktop**:
   - Apple Silicon (M1/M2/M3) or Intel: download from
     https://www.docker.com/products/docker-desktop/ and open the `.dmg`, **or**
   - With Homebrew: `brew install --cask docker`
2. Launch **Docker Desktop** (from Applications) and wait for "Engine running".
3. `make` is already available on macOS. If not, install the Xcode command line
   tools: `xcode-select --install`.

Verify:
```bash
docker --version
docker compose version
make --version
```

### Linux

1. Install **Docker Engine** using your distro's instructions:
   https://docs.docker.com/engine/install/
   (Ubuntu users: follow the "Install using the apt repository" section.)
2. Install the Compose plugin and `make` if you don't have them. On Ubuntu:
   ```bash
   sudo apt update
   sudo apt install docker-compose-plugin make
   ```
3. (Optional but recommended) run Docker without `sudo`:
   ```bash
   sudo usermod -aG docker $USER
   ```
   Then log out and back in.

Verify:
```bash
docker --version
docker compose version
make --version
```

---

## First-time setup

Do this once, after cloning the repo.

1. **Create your local environment file** from the template:
   ```bash
   cp .env.example .env       # macOS / Linux / WSL
   ```
   ```powershell
   copy .env.example .env     # Windows PowerShell / CMD
   ```
   `.env` holds your database credentials and the map API key. It is
   **git-ignored** — never commit it. The committed `.env.example` is just a
   template listing which variables exist.

2. **(Later) add your map API key.** When we've picked a map provider, paste your
   key into `.env`:
   ```
   MAP_API_KEY=your-key-here
   ```
   You can leave it blank for now.

3. **Start everything:**
   ```bash
   make up-build
   ```
   The first run downloads images and builds the app, so it takes a few minutes.
   When it's done, open http://localhost:5000 — you should see `Hello, World!`.

---

## Everyday usage

### Using make (recommended)

Run `make help` at any time to see every available command.

| Command | What it does |
|---------|--------------|
| `make up` | Start the whole project (app + database) in the background |
| `make up-build` | Same, but rebuild images first (use after changing `requirements.txt` or the `Dockerfile`) |
| `make down` | Stop and remove the containers, **keeping** your database data |
| `make teardown` | Stop and remove containers **and delete the database data** (fresh start) |
| `make restart` | `down` then `up` |
| `make ps` / `make status` | Show whether containers are running |
| `make logs` | Watch the logs from all containers (Ctrl-C to stop watching) |

A normal day: `make up`, do your work (edits reload automatically), then
`make down` when you're finished.

> **Only have the old `docker-compose` (with a hyphen)?** Add
> `DC="docker-compose"` to any command, e.g. `make up DC="docker-compose"`.

### Without make (raw docker compose)

If you can't use `make` (e.g. plain Windows PowerShell), run these directly.
Every `make` target maps to one of these:

| Instead of | Run |
|------------|-----|
| `make up` | `docker compose up -d` |
| `make up-build` | `docker compose up -d --build` |
| `make down` | `docker compose down` |
| `make teardown` | `docker compose down -v` |
| `make restart` | `docker compose down && docker compose up -d` |
| `make build` | `docker compose build` |
| `make rebuild` | `docker compose build --no-cache` |
| `make ps` | `docker compose ps` |
| `make logs` | `docker compose logs -f` |

---

## Tearing things up and down

This is the core of the dev workflow. The difference between `down` and
`teardown` matters:

- **`make down`** — stops and removes the containers but **keeps your database
  data** (stored in a Docker volume called `pgdata`). Next `make up` picks up
  where you left off. Use this most of the time.
- **`make teardown`** — removes the containers **and deletes the database
  volume**, giving you a completely fresh database next time. Use this when you
  want a clean slate or something got into a weird state.

```bash
make up          # tear up: start everything
make down        # tear down: stop, but remember the data
make teardown    # full tear down: stop AND wipe the database
```

Raw equivalents: `docker compose up -d`, `docker compose down`,
`docker compose down -v`.

---

## Working on individual containers

You can start or stop the app and the database separately.

| Command | Raw equivalent | What it does |
|---------|----------------|--------------|
| `make up-db` | `docker compose up -d db` | Start only the database |
| `make up-web` | `docker compose up -d web` | Start only the Flask app |
| `make stop-web` | `docker compose stop web` | Stop only the app (don't delete it) |
| `make stop-db` | `docker compose stop db` | Stop only the database (don't delete it) |

Example: restart just the app without touching the database:
```bash
make stop-web
make up-web
```

---

## Troubleshooting

**"Cannot connect to the Docker daemon" / "Is the docker daemon running?"**
Start Docker Desktop (Windows/macOS) and wait for "Engine running", or start the
service on Linux: `sudo systemctl start docker`.

**Port 5000 is already in use.**
Something else is using the port. Stop it, or change the mapping in
`docker-compose.yml` from `"5000:5000"` to e.g. `"5001:5000"`, then use
http://localhost:5001.

**`make: command not found` (Windows).**
Use a WSL2 Ubuntu terminal, or use the raw `docker compose` commands from
[Without make](#without-make-raw-docker-compose).

**`docker compose` says "no such command" but `docker-compose` works.**
You have the older standalone version. Add `DC="docker-compose"` to make
commands (e.g. `make up DC="docker-compose"`) or just run `docker-compose ...`
directly.

**The app can't reach the database right after `make up`.**
The database takes a few seconds to become ready. The app is configured to wait
for it, but if you started them separately, give `db` a moment, then check
`make logs-db`.

**I changed `requirements.txt` but nothing updated.**
Rebuild the image: `make up-build` (or `docker compose up -d --build`).

**I want a completely fresh database.**
`make teardown` then `make up` (this deletes all database data).
