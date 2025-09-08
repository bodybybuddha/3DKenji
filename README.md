# 3DKenji
Self-hosted knowledge keeper for 3D printing projects.

## Development with uv

This project supports Astral's `uv` as an optional project manager. If you have `uv` installed locally, you can create a `.venv` and install the pinned dependencies used by CI and the devcontainer:

```bash
uv venv --python 3.11
. .venv/bin/activate
uv pip sync
uv lock    # generate `uv.lock` and commit it for reproducible installs
```

The devcontainer and CI are configured to install `uv==0.8.15`. Dependencies are declared in `pyproject.toml` and locked with `uv.lock`.
