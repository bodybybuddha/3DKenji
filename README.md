# 3DKenji
Self-hosted knowledge keeper for 3D printing projects.

## Development

Use the devcontainer for local development. It sets up the virtual environment and dependencies automatically.

If you are running locally without the devcontainer:

```bash
make install
make dev
```

Run tests with:

```bash
make test
```

Tests start the FastAPI app automatically for contract checks.
## Resuming Development

See [PROGRESS.md](PROGRESS.md) for detailed implementation status and architecture notes.

**Quick start for next session**:
```bash
# Activate environment
source /workspace/.venv/bin/activate

# Check progress
cat PROGRESS.md

# Verify tests still pass
make test

# Check git log for recent work
git log --oneline -n 5

# See detailed task status
cat specs/001-title-3d-kenji/tasks.md | head -50
```

Current focus: Services layer (T021-T023) – see PROGRESS.md for details.