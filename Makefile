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
	$(DC) up -d

up-build: ## Start the whole project, rebuilding images first (after dependency changes)
	$(DC) up -d --build

down: ## TEAR DOWN: stop & remove containers, but KEEP the database data
	$(DC) down

teardown: ## FULL TEAR DOWN: stop & remove containers AND delete database data (fresh start)
	$(DC) down -v

restart: ## Restart the whole project (down then up)
	$(DC) down
	$(DC) up -d

## ----------------------------------------------------------------------------
## Building
## ----------------------------------------------------------------------------

build: ## Build (or rebuild) images without starting containers
	$(DC) build

rebuild: ## Rebuild images from scratch, ignoring the cache
	$(DC) build --no-cache

## ----------------------------------------------------------------------------
## Individual parts (start/stop one container at a time)
## ----------------------------------------------------------------------------

up-db: ## Start ONLY the database container
	$(DC) up -d db

up-web: ## Start ONLY the web (Flask) container
	$(DC) up -d web

stop-web: ## Stop ONLY the web container (leave it around, don't delete)
	$(DC) stop web

stop-db: ## Stop ONLY the database container (leave it around, don't delete)
	$(DC) stop db

## ----------------------------------------------------------------------------
## Inspecting / debugging
## ----------------------------------------------------------------------------

ps: ## Show the status of the project's containers
	$(DC) ps

status: ps ## Alias for `ps`

logs: ## Follow logs from all containers (Ctrl-C to stop watching)
	$(DC) logs -f

logs-web: ## Follow logs from only the web (Flask) container
	$(DC) logs -f web

logs-db: ## Follow logs from only the database container
	$(DC) logs -f db

shell: ## Open a shell inside the running web container
	$(DC) exec web /bin/bash

db-shell: ## Open a psql prompt inside the running database container
	$(DC) exec db psql -U $${POSTGRES_USER:-appuser} -d $${POSTGRES_DB:-appdb}

## ----------------------------------------------------------------------------
## Housekeeping
## ----------------------------------------------------------------------------

clean: ## Remove dangling Docker images/build cache to reclaim disk (project-agnostic)
	docker system prune -f
