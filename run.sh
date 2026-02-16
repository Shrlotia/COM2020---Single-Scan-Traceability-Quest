#!/bin/bash

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
python3 ./src/sstq/main.py
