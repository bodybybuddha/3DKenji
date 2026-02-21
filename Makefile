.PHONY: venv install install-edit dev test compose-up compose-down clean

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

test: install
	@echo "Running tests..."
	. .venv/bin/activate && $(PYTHON) -m pytest -q

compose-up:
	@echo "Running docker-compose up (builds images)..."
	docker-compose up --build

compose-down:
	@echo "Stopping docker-compose services..."
	docker-compose down

clean:
	@echo "Removing .venv (if present)..."
	rm -rf .venv
