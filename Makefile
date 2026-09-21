# =============================================================================
# EphemeralShield — Makefile
# =============================================================================
# This Makefile provides the standard developer workflow commands.
# All targets are designed to work in a fully-dockerized environment.
#
# Usage:
#   make setup          — First-time setup (install deps, generate secrets)
#   make dev-up         — Start all Docker services
#   make migrate        — Run database migrations
#   make lint           — Run linter
#   make typecheck      — Run mypy strict type checking
#   make test-unit      — Run unit tests
#   make dev-down       — Stop all Docker services
#
# For Windows without make, see the equivalent commands below each target.
# =============================================================================

# Use bash for consistent behavior across systems
SHELL := /bin/bash

# Docker Compose file location
COMPOSE_FILE := deploy/compose.dev.yaml
DC := docker compose -f $(COMPOSE_FILE)

# Python runner via uv (ensures we use the project's virtual environment)
UV_RUN := uv run

# Default target — show help
.DEFAULT_GOAL := help

# ---------------------------------------------------------------------------
# help — Print available targets
# ---------------------------------------------------------------------------
.PHONY: help
help:
	@echo "EphemeralShield Development Commands"
	@echo "====================================="
	@echo ""
	@echo "  make setup        — Install dependencies and generate local secrets"
	@echo "  make dev-up       — Start Docker services (broker-db, test-target-db, redis)"
	@echo "  make dev-down     — Stop Docker services"
	@echo "  make dev-restart  — Restart Docker services"
	@echo "  make migrate      — Run Alembic migrations on broker-db"
	@echo "  make lint         — Run Ruff linter"
	@echo "  make fmt          — Auto-format code with Ruff"
	@echo "  make typecheck    — Run mypy strict type checking"
	@echo "  make test-unit    — Run unit tests"
	@echo "  make test-all     — Run all tests"
	@echo "  make check        — Run lint + typecheck + unit tests"
	@echo "  make clean        — Remove build artifacts and caches"
	@echo ""

# ---------------------------------------------------------------------------
# setup — First-time project setup
# ---------------------------------------------------------------------------
# WHY uv sync? It reads pyproject.toml + uv.lock and installs the exact
# dependency versions. --frozen ensures it fails if uv.lock is out of date
# rather than silently updating it.
#
# PowerShell equivalent:
#   uv sync
#   Copy-Item .env.example .env  (then edit .env)
#   powershell -File scripts/generate-secrets.ps1
# ---------------------------------------------------------------------------
.PHONY: setup
setup:
	uv sync
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env from .env.example — edit it with your local values."; \
	fi
	@if [ ! -d secrets ]; then \
		bash scripts/generate-secrets.sh; \
	fi
	@echo "Setup complete. Run 'make dev-up' to start services."

# ---------------------------------------------------------------------------
# dev-up — Start all development Docker services
# ---------------------------------------------------------------------------
# --build: Rebuild images if Dockerfile changed
# --wait:  Block until all health checks pass (not just containers started)
# -d:      Run in background (detached mode)
#
# PowerShell equivalent:
#   docker compose -f deploy/compose.dev.yaml up -d --build --wait
# ---------------------------------------------------------------------------
.PHONY: dev-up
dev-up:
	$(DC) up -d --build --wait
	@echo "All services are up and healthy."
	@echo "  broker-db:      localhost:5433"
	@echo "  test-target-db: localhost:5434"
	@echo "  redis:          localhost:6379"
	@echo "  API:            localhost:8000"

# ---------------------------------------------------------------------------
# dev-down — Stop all Docker services
# ---------------------------------------------------------------------------
# -v is intentionally NOT used — we want to keep database volumes between
# restarts. Use 'make clean-volumes' to destroy data.
#
# PowerShell equivalent:
#   docker compose -f deploy/compose.dev.yaml down
# ---------------------------------------------------------------------------
.PHONY: dev-down
dev-down:
	$(DC) down
	@echo "All services stopped. Data volumes preserved."

.PHONY: dev-restart
dev-restart: dev-down dev-up

# ---------------------------------------------------------------------------
# migrate — Run Alembic migrations against broker-db
# ---------------------------------------------------------------------------
# WHY separate from dev-up? Migrations should be an explicit, auditable step.
# Never auto-migrate on container start — that's how you get schema drift
# between environments.
#
# PowerShell equivalent:
#   $env:BROKER_DB_URL="postgresql+psycopg://ephemeralshield:password@localhost:5433/ephemeralshield"
#   uv run alembic upgrade head
# ---------------------------------------------------------------------------
.PHONY: migrate
migrate:
	$(UV_RUN) alembic upgrade head
	@echo "Migrations complete."

# ---------------------------------------------------------------------------
# lint — Check code style and potential bugs
# ---------------------------------------------------------------------------
# Ruff replaces flake8 + isort + pycodestyle. It's ~100x faster because
# it's written in Rust.
#
# PowerShell equivalent:
#   uv run ruff check src/ tests/
# ---------------------------------------------------------------------------
.PHONY: lint
lint:
	$(UV_RUN) ruff check src/ tests/
	@echo "Lint passed."

# ---------------------------------------------------------------------------
# fmt — Auto-format code
# ---------------------------------------------------------------------------
# PowerShell equivalent:
#   uv run ruff format src/ tests/
#   uv run ruff check --fix src/ tests/
# ---------------------------------------------------------------------------
.PHONY: fmt
fmt:
	$(UV_RUN) ruff format src/ tests/
	$(UV_RUN) ruff check --fix src/ tests/

# ---------------------------------------------------------------------------
# typecheck — Run mypy in strict mode
# ---------------------------------------------------------------------------
# Strict mode catches a LOT of bugs that tests miss: wrong argument types,
# missing return types, Any leakage, etc. It's annoying at first but saves
# hours of debugging later.
#
# PowerShell equivalent:
#   uv run mypy src/
# ---------------------------------------------------------------------------
.PHONY: typecheck
typecheck:
	$(UV_RUN) mypy src/
	@echo "Type check passed."

# ---------------------------------------------------------------------------
# test-unit — Run unit tests only (fast, no Docker services needed)
# ---------------------------------------------------------------------------
# PowerShell equivalent:
#   uv run pytest tests/unit/ -v
# ---------------------------------------------------------------------------
.PHONY: test-unit
test-unit:
	$(UV_RUN) pytest tests/unit/ -v

# ---------------------------------------------------------------------------
# test-all — Run all tests
# ---------------------------------------------------------------------------
.PHONY: test-all
test-all:
	$(UV_RUN) pytest tests/ -v

# ---------------------------------------------------------------------------
# check — Run everything: lint + typecheck + unit tests
# ---------------------------------------------------------------------------
# This is what CI runs. If this passes locally, CI will pass too.
# ---------------------------------------------------------------------------
.PHONY: check
check: lint typecheck test-unit
	@echo "All checks passed."

# ---------------------------------------------------------------------------
# clean — Remove Python build artifacts and caches
# ---------------------------------------------------------------------------
.PHONY: clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ htmlcov/ .coverage
	@echo "Cleaned."

# ---------------------------------------------------------------------------
# clean-volumes — DESTRUCTIVE: Remove Docker volumes (database data)
# ---------------------------------------------------------------------------
.PHONY: clean-volumes
clean-volumes:
	$(DC) down -v
	@echo "Docker volumes destroyed. Run 'make dev-up' to recreate."
