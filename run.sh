#!/usr/bin/env bash
set -euo pipefail
app_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -x "$app_root/.venv/bin/python" ]]; then
    exec "$app_root/.venv/bin/python" "$app_root/run_analyzer.py" "$@"
else
    exec python3 "$app_root/run_analyzer.py" "$@"
fi
