#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Error: $ENV_FILE not found. Run: bash scripts/bootstrap-mcp.sh --ensure-env" >&2
    exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

if [[ -z "${MCP_POSTGRES_URL:-}" ]]; then
    echo "Error: MCP_POSTGRES_URL is not set in $ENV_FILE" >&2
    exit 1
fi

case "$MCP_POSTGRES_URL" in
    postgres://*|postgresql://*)
        ;;
    *)
        echo "Error: MCP_POSTGRES_URL must start with postgres:// or postgresql://" >&2
        exit 1
        ;;
esac

exec /usr/bin/npx -y @modelcontextprotocol/server-postgres@0.6.2 "$MCP_POSTGRES_URL"