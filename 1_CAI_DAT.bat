@echo off
chcp 65001 >nul
cd /d "%~dp0"
title CAI DAT SonixDangVideo
echo ==============================================
echo    CAI DAT SonixDangVideo (lam 1 lan moi may)
echo ==============================================
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY (
  echo Chua co Python. Dang tu cai Python 3.12...
  winget install -e --id Python.Python.3.12 --scope user --accept-source-agreements --accept-package-agreements
  echo.
  echo Neu khong cai duoc: vao https://www.python.org/downloads/ tai ve,
  echo khi cai NHO TICK o "Add python.exe to PATH".
  echo.
  echo Cai Python xong, DONG cua so nay roi bam lai 1_CAI_DAT.bat
  pause
  exit /b
)
echo [1/3] Tao moi truong rieng cho tool...
if not exist .venv\Scripts\python.exe %PY% -m venv .venv
echo [2/3] Cai thu vien (2-5 phut)...
.venv\Scripts\python.exe -m pip install --upgrade pip -q
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 ( echo LOI cai thu vien. Kiem tra mang roi chay lai. & pause & exit /b )
echo [3/3] Tai trinh duyet du phong...
.venv\Scripts\python.exe -m playwright install chromium
echo.
echo Tao bieu tuong SonixDangVideo ngoai man hinh...
set PYTHONUTF8=1
.venv\Scripts\python.exe -c "from core import desktop; desktop.create_shortcuts()"
echo ===== XONG! Bam dup bieu tuong SonixDangVideo ngoai man hinh de dung =====
pause
