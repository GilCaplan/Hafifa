#!/usr/bin/env bash
# Lints and formats the rolling exercise's Python code with Ruff (settings in setup/ruff.toml).
#
# Usage:
#   ./setup/lint.sh           apply every safe lint fix, format the code, then list what still needs fixing by hand
#   ./setup/lint.sh --check   change nothing, only report (e.g. before committing)
set -uo pipefail
# Run from the project root, whatever folder this is started from
cd "$(dirname "$0")/.."

TARGETS=(main.py air_quality_api air_quality_db air_quality_frontend tests)
# Ruff only finds ruff.toml on its own next to the code (or above it), so point it at setup/
RUFF_CONFIG=(--config setup/ruff.toml)

if ! command -v ruff >/dev/null; then
  echo "ruff not found. Activate the virtual environment or run: pip install ruff" >&2
  exit 1
fi

if [[ "${1:-}" == "--check" ]]; then
  status=0
  echo "== Formatting (files that would change)"
  ruff format "${RUFF_CONFIG[@]}" --check "${TARGETS[@]}" || status=1
  echo "== Lint"
  ruff check "${RUFF_CONFIG[@]}" "${TARGETS[@]}" || status=1
  exit $status
fi

echo "== Lint: applying fixes"
ruff check "${RUFF_CONFIG[@]}" --fix --exit-zero --quiet "${TARGETS[@]}" >/dev/null  # what's left is listed by the last step
echo "== Formatting"
ruff format "${RUFF_CONFIG[@]}" "${TARGETS[@]}"
echo "== Lint: left to fix by hand"
ruff check "${RUFF_CONFIG[@]}" "${TARGETS[@]}"
