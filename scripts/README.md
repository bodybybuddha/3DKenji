# Scripts Directory

This directory contains utility scripts for development, testing, and QA workflows.

## Testing Scripts

### run-qa-tests.sh
Comprehensive test runner with multiple test levels.

**Usage:**
```bash
./scripts/run-qa-tests.sh [level]
```

**Test Levels:**
- `fast` - Contract tests only (~30s)
- `standard` - Contract + integration (~2min)
- `validation` - Input validation tests (~5min)
- `e2e` - Browser end-to-end tests (~10min)
- `full` - Complete test suite (~15min)
- `coverage` - With coverage report
- `security` - Security-focused tests only
- `smoke` - Critical path tests only

**Examples:**
```bash
# Quick sanity check
./scripts/run-qa-tests.sh fast

# Before committing
./scripts/run-qa-tests.sh standard

# Before release
./scripts/run-qa-tests.sh full

# Check coverage
./scripts/run-qa-tests.sh coverage
```

### pre-commit.sh
Pre-commit hook that runs fast tests before allowing commit.

**Installation:**
```bash
# Create symlink to enable pre-commit hook
ln -s ../../scripts/pre-commit.sh .git/hooks/pre-commit
```

**What it does:**
1. Runs fast tests (contract tests)
2. Checks for print() statements (warning only)
3. Checks for TODO comments (warning only)
4. Prevents commit if tests fail

**Skip if needed:**
```bash
# Skip pre-commit hook (not recommended)
git commit --no-verify -m "message"
```

## Existing Scripts

### bootstrap-mcp.sh
Bootstraps VS Code MCP prerequisites for local/devcontainer development.

**Usage:**
```bash
bash scripts/bootstrap-mcp.sh --ensure-env
```

What it does:
1. Creates `.env` from `.env.example` if missing
2. Validates `MCP_POSTGRES_URL`
3. Warms npm package cache for configured MCP servers
4. Installs Playwright Chromium browser for frontend/browser testing

### run-mcp-postgres.sh
Launches the VS Code Postgres MCP server reliably in devcontainer sessions.

What it does:
1. Loads `.env` from the workspace root
2. Validates `MCP_POSTGRES_URL` format
3. Starts `@modelcontextprotocol/server-postgres` with the resolved URL

### check-task-prerequisites.sh
Checks prerequisites before running tasks.

### clean-host-venv.sh
Cleans host virtual environment.

### common.sh
Common utilities used by other scripts.

### create-dummy-users.py
Creates test users in the database.

**Usage:**
```bash
python scripts/create-dummy-users.py
```

### create-new-feature.sh
Scaffolds a new feature with boilerplate.

### get-feature-paths.sh
Gets paths for a specific feature.

### log-rotate.sh
Rotates application logs.

### setup-plan.sh
Sets up planning documents for features.

### update-agent-context.sh
Updates agent context (if using AI assistants).

## Quick Reference

### Run tests via scripts
```bash
# Via script (shows colored output)
./scripts/run-qa-tests.sh validation

# Via Makefile (cleaner)
make test-validation
```

### Install pre-commit hook
```bash
ln -s ../../scripts/pre-commit.sh .git/hooks/pre-commit
```

### Test the scripts
```bash
# Make sure they're executable
chmod +x scripts/*.sh

# Test the QA runner
./scripts/run-qa-tests.sh fast

# Test pre-commit (without committing)
./scripts/pre-commit.sh
```

## Adding New Scripts

1. Create script with `.sh` extension
2. Add shebang: `#!/bin/bash`
3. Make executable: `chmod +x scripts/your-script.sh`
4. Document usage in this README
5. Add to Makefile if appropriate

## Best Practices

### Script Structure
```bash
#!/bin/bash
#
# Script description
#
# Usage: ./script.sh [args]
#

set -e  # Exit on error

# Your code here
```

### Error Handling
```bash
# Check prerequisites
if [[ ! -f .venv/bin/activate ]]; then
    echo "Error: Virtual environment not found"
    exit 1
fi

# Capture errors
if ! pytest tests/; then
    echo "Tests failed"
    exit 1
fi
```

### Colors for Output
```bash
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Success${NC}"
echo -e "${RED}Error${NC}"
echo -e "${YELLOW}Warning${NC}"
```

## Troubleshooting

### Permission Denied
```bash
chmod +x scripts/your-script.sh
```

### Script not found
```bash
# Make sure you're in project root
cd /workspace

# Or use absolute path
/workspace/scripts/run-qa-tests.sh fast
```

### Virtual environment issues
```bash
# Activate manually first
source .venv/bin/activate

# Then run script
./scripts/run-qa-tests.sh fast
```
