# ============================================================================
#  Makefile — convenience wrapper around Docker Compose for development.
#
#  New to this project? Run:  make help
#
#  Every target here is just a shortcut for a `docker compose ...` command.
#  If you can't (or don't want to) use `make`, the README lists the exact
#  docker compose command each target runs. On Windows, `make` works inside
#  WSL2; in plain PowerShell/CMD use the docker compose commands directly.
# ============================================================================

# Use `docker compose` (v2, built into modern Docker). If your machine only has
# the older standalone binary, override on the command line:
#     make up DC="docker-compose"
DC ?= docker compose

# Directory this Makefile lives in (the docker/ folder), resolved absolutely so
# targets work whether you run `make` from the project root (via the root
# Makefile) or from inside docker/. The compose file sets `name: dat257`, so the
# stack name is consistent with raw `docker compose` commands too. We pass the
# root .env explicitly so variable substitution works regardless of cwd.
THIS_DIR := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))
COMPOSE  := $(DC) --env-file $(THIS_DIR)../.env -f $(THIS_DIR)docker-compose.yml

# `make` with no target shows help.
.DEFAULT_GOAL := help

# These targets are commands, not files.
.PHONY: help up up-build down teardown restart \
        build rebuild logs logs-web logs-db ps \
        shell db-shell up-db up-web stop-web stop-db clean status

## ----------------------------------------------------------------------------
## Everyday commands
## ----------------------------------------------------------------------------

help: ## Show this help (list of all targets)
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

up: ## TEAR UP: start the whole project (app + database) in the background
	$(COMPOSE) up -d

up-build: ## Start the whole project, rebuilding images first (after dependency changes)
	$(COMPOSE) up -d --build

down: ## TEAR DOWN: stop & remove containers, but KEEP the database data
	$(COMPOSE) down

teardown: ## FULL TEAR DOWN: stop & remove containers AND delete database data (fresh start)
	$(COMPOSE) down -v

restart: ## Restart the whole project (down then up)
	$(COMPOSE) down
	$(COMPOSE) up -d

## ----------------------------------------------------------------------------
## Building
## ----------------------------------------------------------------------------

build: ## Build (or rebuild) images without starting containers
	$(COMPOSE) build

rebuild: ## Rebuild images from scratch, ignoring the cache
	$(COMPOSE) build --no-cache

## ----------------------------------------------------------------------------
## Individual parts (start/stop one container at a time)
## ----------------------------------------------------------------------------

up-db: ## Start ONLY the database container
	$(COMPOSE) up -d db

up-web: ## Start ONLY the web (Flask) container
	$(COMPOSE) up -d web

stop-web: ## Stop ONLY the web container (leave it around, don't delete)
	$(COMPOSE) stop web

stop-db: ## Stop ONLY the database container (leave it around, don't delete)
	$(COMPOSE) stop db

## ----------------------------------------------------------------------------
## Inspecting / debugging
## ----------------------------------------------------------------------------

ps: ## Show the status of the project's containers
	$(COMPOSE) ps

status: ps ## Alias for `ps`

logs: ## Follow logs from all containers (Ctrl-C to stop watching)
	$(COMPOSE) logs -f

logs-web: ## Follow logs from only the web (Flask) container
	$(COMPOSE) logs -f web

logs-db: ## Follow logs from only the database container
	$(COMPOSE) logs -f db

shell: ## Open a shell inside the running web container
	$(COMPOSE) exec web /bin/bash

db-shell: ## Open a psql prompt inside the running database container
	$(COMPOSE) exec db psql -U $${POSTGRES_USER:-appuser} -d $${POSTGRES_DB:-appdb}

## ----------------------------------------------------------------------------
## Housekeeping
## ----------------------------------------------------------------------------

clean: ## Remove dangling Docker images/build cache to reclaim disk (project-agnostic)
	docker system prune -f
