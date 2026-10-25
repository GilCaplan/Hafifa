#!/usr/bin/env bash
# Lints and formats the rolling exercise's Python code with Ruff (settings in ruff.toml).
#
# Usage:
#   ./lint.sh           apply every safe lint fix, format the code, then list what still needs fixing by hand
#   ./lint.sh --check   change nothing, only report (e.g. before committing)
set -uo pipefail
cd "$(dirname "$0")"

TARGETS=(main.py air_quality_api air_quality_db tests)

if ! command -v ruff >/dev/null; then
  echo "ruff not found. Activate the virtual environment or run: pip install ruff" >&2
  exit 1
fi

if [[ "${1:-}" == "--check" ]]; then
  status=0
  echo "== Formatting (files that would change)"
  ruff format --check "${TARGETS[@]}" || status=1
  echo "== Lint"
  ruff check "${TARGETS[@]}" || status=1
  exit $status
fi

echo "== Lint: applying fixes"
ruff check --fix --exit-zero --quiet "${TARGETS[@]}" >/dev/null  # what's left is listed by the last step
echo "== Formatting"
ruff format "${TARGETS[@]}"
echo "== Lint: left to fix by hand"
ruff check "${TARGETS[@]}"
