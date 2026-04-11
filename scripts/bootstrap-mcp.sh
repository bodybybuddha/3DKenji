#!/usr/bin/env bash
# Bootstrap MCP server prerequisites for this workspace.
# - Ensures .env exists (optional copy from .env.example)
# - Validates MCP_POSTGRES_URL shape
# - Warms MCP npm packages
# - Installs Playwright Chromium for browser testing/MCP usage

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"
ENV_EXAMPLE_FILE="$ROOT_DIR/.env.example"

ensure_env=false
skip_browser_install=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ensure-env)
            ensure_env=true
            shift
            ;;
        --skip-browser-install)
            skip_browser_install=true
            shift
            ;;
        --help|-h)
            cat <<'EOF'
Usage: scripts/bootstrap-mcp.sh [--ensure-env] [--skip-browser-install]

Options:
  --ensure-env           Create .env from .env.example if missing.
  --skip-browser-install Skip Playwright browser installation.
EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

if ! command -v npx >/dev/null 2>&1; then
    echo "Error: npx is not installed. Install Node.js/npm in the devcontainer." >&2
    exit 1
fi

if [[ "$ensure_env" == "true" && ! -f "$ENV_FILE" && -f "$ENV_EXAMPLE_FILE" ]]; then
    cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
    echo "Created .env from .env.example"
fi

if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    set -a
    source "$ENV_FILE"
    set +a
fi

if [[ -z "${MCP_POSTGRES_URL:-}" ]]; then
    echo "Warning: MCP_POSTGRES_URL is not set. Postgres MCP will fail to start until it is configured in .env."
else
    case "$MCP_POSTGRES_URL" in
        postgresql://*|postgres://*)
            ;;
        *)
            echo "Error: MCP_POSTGRES_URL must use postgres:// or postgresql:// (not SQLAlchemy driver URLs)." >&2
            exit 1
            ;;
    esac
fi

echo "Warming MCP package cache..."
npx -y @playwright/mcp@0.0.70 --version >/dev/null
npx -y chrome-devtools-mcp@0.21.0 --version >/dev/null
if [[ -n "${MCP_POSTGRES_URL:-}" ]]; then
    timeout 3s npx -y @modelcontextprotocol/server-postgres@0.6.2 "$MCP_POSTGRES_URL" >/dev/null 2>&1 || true
fi

if [[ "$skip_browser_install" == "false" ]]; then
    echo "Installing Playwright Chromium browser..."
    npx -y playwright@1.59.1 install --with-deps chromium
fi

echo "MCP bootstrap complete."
