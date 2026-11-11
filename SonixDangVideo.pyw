"""SonixDangVideo — bấm đúp biểu tượng là chạy (không hiện cửa sổ đen).

  SonixDangVideo.pyw         bật bộ đăng tự động + giao diện, mở cửa sổ app
  SonixDangVideo.pyw --nen   chỉ chạy nền (dùng khi tự bật lúc mở máy), không mở cửa sổ
"""
import os
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from core import desktop  # noqa: E402
from core.config import DATA_DIR, HEARTBEAT_FILE, ensure_dirs, load_settings  # noqa: E402

ensure_dirs()
PY = str(Path(sys.executable).with_name("python.exe")) if sys.platform == "win32" else sys.executable
if not Path(PY).exists():
    PY = sys.executable


def runner_alive():
    try:
        return time.time() - float(HEARTBEAT_FILE.read_text()) < 90
    except Exception:
        return False


def start_runner():
    (DATA_DIR / "stop_runner.flag").unlink(missing_ok=True)
    if not runner_alive():
        subprocess.Popen([PY, str(BASE / "runner.py")], cwd=str(BASE), env=desktop.env(),
                         creationflags=desktop.no_window_flags(),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def start_ui():
    if desktop.is_up():
        return True
    S = load_settings()
    addr = "0.0.0.0" if S.get("lan_access") else "127.0.0.1"
    log = open(DATA_DIR / "logs" / "giao_dien.log", "a", encoding="utf-8")
    subprocess.Popen([PY, "-m", "streamlit", "run", str(BASE / "app.py"), "--server.port", str(desktop.PORT),
                      "--server.address", addr, "--server.headless", "true"],
                     cwd=str(BASE), env=desktop.env(), creationflags=desktop.no_window_flags(),
                     stdout=log, stderr=log)
    for _ in range(60):
        if desktop.is_up():
            return True
        time.sleep(0.5)
    return False


def refresh_shortcuts_once():
    """Bản cũ: biểu tượng trỏ vào Python. Có SonixDangVideo.exe rồi thì làm lại biểu tượng 1 lần cho trỏ vào exe."""
    flag = DATA_DIR / "bieu_tuong_exe.flag"
    if sys.platform != "win32" or flag.exists() or not desktop.LAUNCHER_EXE.exists():
        return
    try:
        desktop.create_shortcuts()
        if desktop.is_autostart():
            desktop.set_autostart(True)
        flag.write_text("ok", encoding="utf-8")
    except Exception:
        pass


if __name__ == "__main__":
    start_runner()
    if "--nen" in sys.argv:
        start_ui()
        sys.exit(0)
    import threading
    threading.Thread(target=refresh_shortcuts_once, daemon=True).start()
    from core import cua_so
    if cua_so.run(start_ui):
        os._exit(0)
    # máy không mở được cửa sổ riêng: dùng cửa sổ Chrome như trước
    if start_ui():
        desktop.open_app_window()
    else:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, "Không mở được giao diện. Xem file data\\logs\\giao_dien.log",
                                         "SonixDangVideo", 0x10)
