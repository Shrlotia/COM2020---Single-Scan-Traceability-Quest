#!/bin/bash

set -euo pipefail

if [ ! -x ".venv/bin/python" ]; then
    echo "Missing .venv. Run ./run.sh first."
    exit 1
fi

.venv/bin/python -m pytest -v
