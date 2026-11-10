@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe ( echo Chua cai dat. Bam 1_CAI_DAT.bat truoc. & pause & exit /b )
set PYTHONUTF8=1
.venv\Scripts\python.exe -c "from core import desktop; ok, err = desktop.create_shortcuts(); print('Da tao bieu tuong SonixDangVideo ngoai man hinh va menu Start' if ok else 'Loi: ' + err)"
echo Tu gio bam dup bieu tuong SonixDangVideo de mo tool.
pause
