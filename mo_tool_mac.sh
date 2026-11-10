#!/bin/bash
cd "$(dirname "$0")"; export PYTHONUTF8=1
.venv/bin/python runner.py & R=$!; trap "kill $R 2>/dev/null" EXIT
(sleep 6; open http://localhost:8501 2>/dev/null || xdg-open http://localhost:8501) &
.venv/bin/python -m streamlit run app.py
