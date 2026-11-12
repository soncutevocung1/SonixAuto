"""Biến tool thành 'app' trên máy tính: biểu tượng ngoài màn hình, menu Start, tự bật khi mở máy,
mở giao diện trong cửa sổ riêng (không thanh địa chỉ), địa chỉ để mở trên điện thoại cùng Wi-Fi."""
import os
import socket
import subprocess
import sys
from pathlib import Path

from .config import APP_NAME, BASE_DIR, DATA_DIR, ensure_dirs

PORT = 8501
ICON = BASE_DIR / "assets" / "sonix.ico"
LAUNCHER = BASE_DIR / "SonixDangVideo.pyw"
LAUNCHER_EXE = BASE_DIR / "Sonix Auto.exe"   # file bấm mở app (gọi Python chạy SonixDangVideo.pyw)

BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    str(Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def browser_exe():
    return next((b for b in BROWSERS if Path(b).exists()), "")


def local_ip() -> str:
    """Địa chỉ IP của máy trong mạng Wi-Fi/LAN (để mở tool trên điện thoại)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def open_app_window(url=f"http://localhost:{PORT}"):
    """Mở giao diện trong cửa sổ riêng như 1 phần mềm (Chrome/Edge chế độ app)."""
    exe = browser_exe()
    if exe:
        prof = DATA_DIR / "app_window"
        prof.mkdir(parents=True, exist_ok=True)
        subprocess.Popen([exe, f"--app={url}", f"--user-data-dir={prof}", "--window-size=1440,920",
                          "--no-first-run", "--no-default-browser-check"])
    else:
        import webbrowser
        webbrowser.open(url)


def _python_w():
    exe = Path(sys.executable)
    w = exe.with_name("pythonw.exe")
    return str(w if w.exists() else exe)


def _q(text) -> str:
    """Đưa chữ vào chuỗi PowerShell '...' an toàn."""
    return str(text).replace("'", "''")


def run_ps(script: str):
    """Chạy lệnh PowerShell. Trả về (thành công, kết quả, lỗi) — không bao giờ sập vì mã hoá tiếng Việt."""
    ensure_dirs()
    f = DATA_DIR / "tam_lenh.ps1"
    f.write_text("$ErrorActionPreference='Stop'\n[Console]::OutputEncoding=[Text.Encoding]::UTF8\n" + script,
                 encoding="utf-8-sig")
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(f)],
                           capture_output=True, timeout=90, creationflags=no_window_flags())
    except Exception as e:
        return False, "", f"{type(e).__name__}: {e}"
    out = (p.stdout or b"").decode("utf-8", "ignore").strip()
    err = (p.stderr or b"").decode("utf-8", "ignore").strip()
    return p.returncode == 0, out, err[-400:]


def _make_lnk(link: Path, target, args="", workdir="", icon=""):
    """Tạo file .lnk. WScript chỉ lưu được tên không dấu kiểu cũ, nên tạo tên tạm rồi Python đổi sang tên thật."""
    link = Path(link)
    link.parent.mkdir(parents=True, exist_ok=True)
    tmp = link.parent / f"sonix_tam_{os.getpid()}.lnk"
    ok, _, err = run_ps(
        f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{_q(tmp)}');$s.TargetPath='{_q(target)}';"
        f"$s.Arguments='{_q(args)}';" + (f"$s.WorkingDirectory='{_q(workdir)}';" if workdir else "")
        + (f"$s.IconLocation='{_q(icon)}';" if icon else "") + "$s.Description='SonixDangVideo';$s.Save()")
    if not ok:
        return False, err
    try:
        if link.exists():
            link.unlink()
        tmp.replace(link)
        return True, ""
    except Exception as e:
        return False, f"Không đổi được tên biểu tượng: {e}"


SHORTCUT_NAME = "Sonix Auto"  # tên biểu tượng (thư mục, file exe vẫn giữ tên SonixDangVideo để cập nhật không lỗi)


def _shortcut(path: Path, args: str = "", desc: str = APP_NAME):
    """Tạo file .lnk mở app SonixDangVideo (trỏ vào SonixDangVideo.exe; chưa có exe thì trỏ vào Python)."""
    if LAUNCHER_EXE.exists():
        return _make_lnk(path, LAUNCHER_EXE, args, BASE_DIR, icon_path())
    return _make_lnk(path, _python_w(), f'"{LAUNCHER}" {args}'.strip(), BASE_DIR, icon_path())


def special_folder(name: str) -> Path:
    ok, out, _ = run_ps(f"[Environment]::GetFolderPath('{name}')")
    if ok and out:
        return Path(out.splitlines()[-1].strip())
    return Path.home() / ("Desktop" if name == "Desktop" else "")


def channel_shortcut(channel: str, pdir, chrome: str):
    """Biểu tượng mở trình duyệt riêng của 1 kênh (để vào TikTok/Gmail bằng tay)."""
    if sys.platform != "win32" or not chrome:
        return False, "Chỉ tạo được trên Windows có cài Google Chrome."
    link = special_folder("Desktop") / f"{APP_NAME} - {channel}.lnk"
    return _make_lnk(link, chrome, f'--user-data-dir="{pdir}" https://www.tiktok.com/tiktokstudio', "", f"{chrome},0")


def create_shortcuts():
    """Biểu tượng ngoài màn hình + trong menu Start."""
    if sys.platform != "win32":
        return False, "Chỉ tạo được trên Windows"
    out = []
    for folder in (special_folder("Desktop"), special_folder("Programs")):
        ok, err = _shortcut(folder / f"{SHORTCUT_NAME}.lnk")
        out.append(ok)
        if not ok:
            return False, err
        old = folder / f"{APP_NAME}.lnk"  # biểu tượng tên cũ (SonixDangVideo) -> bỏ, tránh 2 biểu tượng
        try:
            if old.exists():
                old.unlink()
        except OSError:
            pass
    return all(out), ""


def startup_link() -> Path:
    return special_folder("Startup") / f"{APP_NAME} (chạy nền).lnk"


def set_autostart(on: bool):
    """Tự bật tool (chạy nền, không mở cửa sổ) mỗi khi mở máy, để tới giờ vẫn đăng."""
    if sys.platform != "win32":
        return False, "Chỉ dùng được trên Windows"
    link = startup_link()
    if on:
        return _shortcut(link, "--nen", f"{APP_NAME} chạy nền")
    if link.exists():
        link.unlink()
    return True, ""


def is_autostart() -> bool:
    try:
        return sys.platform == "win32" and startup_link().exists()
    except Exception:
        return False


def no_window_flags():
    return 0x08000000 if sys.platform == "win32" else 0   # CREATE_NO_WINDOW


def is_up(port=PORT) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except Exception:
        return False


def stop_all():
    """Ghi cờ dừng cho bộ đăng tự động (nó tự thoát ở vòng kế tiếp)."""
    (DATA_DIR / "stop_runner.flag").write_text("stop", encoding="utf-8")


def env():
    e = dict(os.environ)
    e["PYTHONUTF8"] = "1"
    e["PYTHONIOENCODING"] = "utf-8"
    return e


# ---------- biểu tượng app: cố định assets/sonix.ico (đã bỏ chức năng đổi ảnh riêng) ----------
def icon_path() -> Path:
    return ICON


def low_priority():
    """Cho tool chạy ở mức ưu tiên dưới bình thường: máy bận việc khác thì tool nhường CPU,
    máy rảnh thì vẫn chạy hết tốc độ. Chrome, ffmpeg do tool mở ra cũng nhường theo (Windows tự kế thừa)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        k = ctypes.windll.kernel32
        k.SetPriorityClass(k.GetCurrentProcess(), 0x00004000)  # BELOW_NORMAL_PRIORITY_CLASS
    except Exception:
        pass
