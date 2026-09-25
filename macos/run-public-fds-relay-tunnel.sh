#!/bin/zsh
set -euo pipefail
ROOT="${0:A:h:h}"
exec "$ROOT/.venv/bin/python" -u "$ROOT/ap01_relay_supervisor.py"
