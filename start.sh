#!/usr/bin/env bash
# Launchpad Pro TAB Edition – Start unter Linux/macOS.
# Beim ersten Start wird eine Python-Umgebung (.venv) angelegt.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
    echo "Erster Start: Python-Umgebung wird eingerichtet …"
    python3 -m venv .venv
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -r requirements.txt
fi

exec .venv/bin/python -m launchpad_pro_tab "$@"
