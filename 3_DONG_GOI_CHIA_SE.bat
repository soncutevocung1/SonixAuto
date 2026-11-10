@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist .venv\Scripts\python.exe ( .venv\Scripts\python.exe dong_goi.py ) else ( python dong_goi.py )
pause
