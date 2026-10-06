# Uses docker compose if available, otherwise podman compose.
COMPOSE ?= $(shell command -v docker >/dev/null 2>&1 && echo "docker compose" || echo "podman compose")

.PHONY: install lint format test db-up db-down ingest

install:
	uv python install
	uv sync

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

# Unit + database tests. Slow end-to-end tests are excluded.
test:
	uv run pytest -m "not slow"

db-up:
	$(COMPOSE) up -d --wait db

db-down:
	$(COMPOSE) down

# Download the pinned legi-data version and (re)load the articles table.
ingest:
	uv run python -m alinea.ingest
