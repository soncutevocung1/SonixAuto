"""SonixDangVideo — bấm đúp biểu tượng là chạy (không hiện cửa sổ đen).

  SonixDangVideo.pyw         bật bộ đăng tự động + giao diện, mở cửa sổ app
  SonixDangVideo.pyw --nen   chỉ chạy nền (dùng khi tự bật lúc mở máy), không mở cửa sổ
"""
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


if __name__ == "__main__":
    start_runner()
    ok = start_ui()
    if "--nen" not in sys.argv:
        if ok:
            desktop.open_app_window()
        else:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, "Không mở được giao diện. Xem file data\\logs\\giao_dien.log",
                                             "SonixDangVideo", 0x10)
