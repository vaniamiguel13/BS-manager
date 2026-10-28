#!/usr/bin/env bash
# Arranca a plataforma neste PC. Na primeira vez prepara o ambiente Python.
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
    echo "A preparar o ambiente pela primeira vez..."
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
fi
exec .venv/bin/python serve.py
