.PHONY: venv install install-edit dev test docker-build compose-up compose-down clean

PYTHON=python
UV=uv

venv:
	@echo "Creating uv venv (.venv) using Python 3.11..."
	$(UV) venv --python 3.11

install: venv
	@echo "Syncing dependencies into .venv..."
	. .venv/bin/activate && $(UV) pip sync

install-edit: install
	@echo "Installing project in editable mode into .venv..."
	. .venv/bin/activate && pip install --no-deps -e /workspace || . .venv/bin/activate && pip install --no-deps -e .

dev: install-edit
	@echo "Starting dev server (uvicorn) with reload..."
	. .venv/bin/activate && $(UV) run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

test: install
	@echo "Running tests..."
	. .venv/bin/activate && $(PYTHON) -m pytest -q

docker-build:
	@echo "Building backend Docker image..."
	docker build -t 3d-kenji-backend -f backend/Dockerfile backend

compose-up:
	@echo "Running docker-compose up (builds images)..."
	docker-compose up --build

compose-down:
	@echo "Stopping docker-compose services..."
	docker-compose down

clean:
	@echo "Removing .venv (if present)..."
	rm -rf .venv
