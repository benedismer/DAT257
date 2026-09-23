# ============================================================================
#  Root Makefile — convenience forwarder.
#
#  The real Makefile lives in docker/ (alongside the Docker config). This thin
#  wrapper lets you keep running `make up`, `make down`, etc. from the PROJECT
#  ROOT, exactly as the README describes. Every target is passed straight
#  through to docker/Makefile.
#
#  Run `make help` to see all available targets.
# ============================================================================

# Forward ANY target (and the default no-arg invocation) to docker/Makefile.
# -C changes into docker/ so its paths and compose file resolve correctly.
MAKECMDGOALS ?= help

.DEFAULT_GOAL := help

# Catch-all: forward every goal to the docker/ Makefile.
%:
	@$(MAKE) --no-print-directory -C docker $@

# `make` with no target -> help (also forwarded).
help:
	@$(MAKE) --no-print-directory -C docker help
