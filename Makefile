.PHONY: venv install install-edit dev test test-fast test-validation test-e2e test-e2e-smoke test-full test-coverage test-security qa-check compose-up compose-down mcp-bootstrap clean

PYTHON=python
UV=uv

venv:
	@if [ -d .venv ]; then \
		echo "Using existing .venv"; \
	else \
		echo "Creating uv venv (.venv) using Python 3.11..."; \
		$(UV) venv --python 3.11; \
	fi

install: venv
	@echo "Syncing dependencies into .venv from uv.lock..."
	. .venv/bin/activate && $(UV) sync --frozen

install-edit: install
	@echo "Project is installed editable via uv sync."

dev: install-edit
	@echo "Starting dev server (uvicorn) with reload..."
	. .venv/bin/activate && $(UV) run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Standard test commands
test: install
	@echo "Running standard tests (contract + integration)..."
	. .venv/bin/activate && bash scripts/run-qa-tests.sh standard

test-fast: install
	@echo "Running fast tests (contract only)..."
	. .venv/bin/activate && bash scripts/run-qa-tests.sh fast

test-validation: install
	@echo "Running validation tests..."
	. .venv/bin/activate && bash scripts/run-qa-tests.sh validation

test-e2e: install
	@echo "Running E2E tests..."
	. .venv/bin/activate && bash scripts/run-qa-tests.sh e2e

test-e2e-smoke: install
	@echo "Running E2E smoke tests..."
	. .venv/bin/activate && bash scripts/run-qa-tests.sh e2e-smoke

test-full: install
	@echo "Running full test suite..."
	. .venv/bin/activate && bash scripts/run-qa-tests.sh full

test-coverage: install
	@echo "Running tests with coverage..."
	. .venv/bin/activate && bash scripts/run-qa-tests.sh coverage

test-security: install
	@echo "Running security tests..."
	. .venv/bin/activate && bash scripts/run-qa-tests.sh security

qa-check: test-full
	@echo "Opening QA checklist..."
	@echo "See tests/manual/qa-checklist.md for manual QA items"

compose-up:
	@echo "Running docker-compose up (builds images)..."
	docker-compose up --build

compose-down:
	@echo "Stopping docker-compose services..."
	docker-compose down

mcp-bootstrap:
	@echo "Bootstrapping MCP dependencies (env, package cache, browsers)..."
	bash scripts/bootstrap-mcp.sh --ensure-env

clean:
	@echo "Removing .venv (if present)..."
	rm -rf .venv
