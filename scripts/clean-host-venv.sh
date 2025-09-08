#!/usr/bin/env bash
set -euo pipefail

# Remove the host .venv directory for this project.
# Usage:
#   ./scripts/clean-host-venv.sh        # interactive confirmation
#   ./scripts/clean-host-venv.sh --yes  # non-interactive

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PATH="$REPO_ROOT/.venv"

if [ ! -d "$VENV_PATH" ]; then
  echo "No .venv found at $VENV_PATH — nothing to remove."
  exit 0
fi

if [ "${1:-}" = "--yes" ] || [ "${1:-}" = "-y" ]; then
  rm -rf "$VENV_PATH"
  echo "Removed $VENV_PATH"
  exit 0
fi

printf "WARNING: This will permanently delete the host venv at:\n  %s\n" "$VENV_PATH"
read -r -p "Continue and remove it? [y/N] " ans
case "$ans" in
  y|Y)
    rm -rf "$VENV_PATH"
    echo "Removed $VENV_PATH"
    ;;
  *)
    echo "Aborted. No changes made."
    exit 1
    ;;
esac
