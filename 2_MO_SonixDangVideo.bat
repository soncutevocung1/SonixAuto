@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\pythonw.exe (
  echo Chua cai dat. Bam 1_CAI_DAT.bat truoc.
  pause
  exit /b
)
start "" .venv\Scripts\pythonw.exe "%~dp0SonixDangVideo.pyw"
