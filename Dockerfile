FROM python:3.11-slim

# Install build essentials (make, gcc, etc.)
RUN apt-get update && apt-get install -y make

WORKDIR /app

# Install a pinned uv (Astral) to manage venvs and fast installs
RUN python -m pip install --no-cache-dir --upgrade pip && \
	pip install --no-cache-dir uv==0.8.15

# Copy project metadata and source into the image
COPY pyproject.toml uv.lock Makefile pytest.ini /app/
COPY src /app/src

# Create a per-project .venv, sync dependencies with uv, and install the package
RUN uv venv --python 3.11 && \
	. .venv/bin/activate && \
	uv sync --frozen
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
