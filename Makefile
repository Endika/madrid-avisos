CONFIG ?= ~/.config/madrid-avisos/config.toml
RUN := uv run --locked

.PHONY: install lint format format-check types test check run dry-run

install:
	uv sync --locked

lint:
	$(RUN) ruff check .

format:
	$(RUN) ruff check --fix .
	$(RUN) ruff format .

format-check:
	$(RUN) ruff format --check .

types:
	$(RUN) mypy

test:
	$(RUN) pytest -q

check: lint format-check types test

run:
	$(RUN) madrid-avisos --config $(CONFIG)

dry-run:
	$(RUN) madrid-avisos --config $(CONFIG) --dry-run
