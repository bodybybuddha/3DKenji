FROM python:3.11-slim

# Install build essentials (make, gcc, etc.)
RUN apt-get update && apt-get install -y make

# Install a pinned uv (Astral) to manage venvs and fast installs
RUN python -m pip install --no-cache-dir --upgrade pip && \
	pip install --no-cache-dir uv==0.8.15

WORKDIR /workspace

# Copy project metadata and source into the image
COPY pyproject.toml uv.lock Makefile pytest.ini /workspace/
# COPY src /workspace/app/src. - shouldn't need of this with volume mount

ENV PATH="/workspace/.venv/bin:$PATH"
EXPOSE 8000
CMD ["sleep", "infinity"]