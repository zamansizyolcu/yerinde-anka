#!/usr/bin/env bash
# YERINDE — CachyOS (Arch Linux) başlatma betiği
cd "$(dirname "$0")"

if [ -d "venv" ]; then
    source venv/bin/activate
fi

python main.py
