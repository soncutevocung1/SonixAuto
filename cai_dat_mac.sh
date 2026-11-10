#!/bin/bash
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo "Chưa có Python 3: https://www.python.org/downloads/"; exit 1; }
python3 -m venv .venv && .venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -r requirements.txt && .venv/bin/python -m playwright install chromium
echo "XONG! Chạy: bash mo_tool_mac.sh"
