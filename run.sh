#!/bin/bash

set -euo pipefail

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Missing required command: $1"
        exit 1
    fi
}

echo "Checking runtime environment..."
require_cmd python3
require_cmd node
require_cmd npm

if [ ! -x ".venv/bin/python" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi

echo "Checking Python dependencies..."
if ! .venv/bin/python -c "import flask, flask_sqlalchemy, flask_login, flask_cors" >/dev/null 2>&1; then
    echo "Installing Python dependencies..."
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -r requirements.txt
    .venv/bin/python -m pip install -e .
fi

echo "Checking Node.js dependencies..."
if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm ci
else
    if ! npm ls --depth=0 >/dev/null 2>&1; then
        echo "Reinstalling incomplete Node.js dependencies..."
        npm ci
    fi
fi

if [ ! -f "src/sstq/static/js/scan_barcode.bundle.js" ]; then
    echo "Building frontend bundle..."
    npm run build:scan-barcode
fi

echo "Starting application..."
.venv/bin/python ./src/sstq/main.py
