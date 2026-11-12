"""Cửa sổ app riêng của Sonix Đăng Video (dùng WebView2 có sẵn trong Windows, giống Kid TE).

- Mở lên là màn hình chờ, giao diện sẵn sàng thì tự vào.
- Giao diện mất kết nối (vd đang khởi động lại sau cập nhật) thì quay về màn hình chờ, có lại thì tự vào lại.
- Chỉ 1 cửa sổ: bấm mở lần nữa thì đưa cửa sổ đang mở lên trước.
- Tắt cửa sổ: bộ đăng tự động và giao diện vẫn chạy nền, tới giờ hẹn vẫn đăng.
"""
import sys
import threading
import time

from . import desktop
from .config import DATA_DIR

TITLE = "Sonix Auto"
APP_ID = "Sonix.DangVideo"
URL = f"http://127.0.0.1:{desktop.PORT}"

SPLASH = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;height:100%;font-family:'Segoe UI',system-ui,sans-serif;display:flex;align-items:center;
justify-content:center;background:linear-gradient(135deg,#eef2ff 0%,#f3eeff 55%,#e8f0ff 100%);color:#1e1b4b}
@media (prefers-color-scheme: dark){html,body{background:linear-gradient(135deg,#0b0d16 0%,#17112e 60%,#0d1630 100%);color:#e0e7ff}}
.b{text-align:center}
.t{font-size:34px;font-weight:800;letter-spacing:.2px;background:linear-gradient(90deg,#2563eb,#7c3aed);
-webkit-background-clip:text;background-clip:text;color:transparent}
.s{margin-top:10px;font-style:italic;font-weight:300;opacity:.8}
.d{width:44px;height:44px;margin:28px auto 0;border-radius:50%;border:4px solid rgba(124,58,237,.2);
border-top-color:#7c3aed;animation:r .9s linear infinite}
@keyframes r{to{transform:rotate(360deg)}}
</style></head><body><div class="b"><div class="t">Sonix Auto</div><div class="s">__MSG__</div>
<div class="d"></div></div></body></html>"""


def _splash(msg):
    return SPLASH.replace("__MSG__", msg)


# ------------------------------- Windows: 1 cửa sổ, biểu tượng riêng -------------------------------
def _win():
    return sys.platform == "win32"


def _find():
    import ctypes
    return ctypes.windll.user32.FindWindowW(None, TITLE)


def bring_existing() -> bool:
    """Đã có cửa sổ đang mở thì đưa nó lên trước, trả về True."""
    if not _win():
        return False
    import ctypes
    k = ctypes.windll.kernel32
    globals()["_MUTEX"] = k.CreateMutexW(None, False, "SonixDangVideo_CuaSo")
    if k.GetLastError() != 183:  # ERROR_ALREADY_EXISTS
        return False
    for _ in range(20):
        h = _find()
        if h:
            u = ctypes.windll.user32
            u.ShowWindow(h, 9)  # SW_RESTORE
            u.ShowWindow(h, 5)  # SW_SHOW (cửa sổ đang ẩn cũng hiện ra)
            u.SetForegroundWindow(h)
            return True
        time.sleep(0.25)
    return True


def _app_id():
    if _win():
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except Exception:
            pass


def _set_icon():
    """Đặt biểu tượng Sonix cho cửa sổ + thanh tác vụ (mặc định sẽ là biểu tượng Python)."""
    if not _win():
        return
    import ctypes
    u = ctypes.windll.user32
    u.LoadImageW.restype = ctypes.c_void_p
    u.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
    ico = str(desktop.icon_path())
    for _ in range(40):
        h = _find()
        if h:
            if not u.IsWindowVisible(h):  # mở bằng file .exe bản cũ: cửa sổ bị ẩn -> cho hiện ra
                u.ShowWindow(h, 9)  # SW_RESTORE
                u.ShowWindow(h, 5)  # SW_SHOW
                u.SetForegroundWindow(h)
            for which, size in ((1, 256), (0, 32)):  # ICON_BIG, ICON_SMALL
                hi = u.LoadImageW(None, ico, 1, size, size, 0x10)  # IMAGE_ICON, LR_LOADFROMFILE
                if hi:
                    u.SendMessageW(h, 0x80, which, hi)  # WM_SETICON
            return
        time.sleep(0.25)


# ------------------------------- canh giao diện -------------------------------
def _watch(win, start_ui):
    _set_icon()
    threading.Thread(target=start_ui, daemon=True).start()
    shown, down_since = False, None
    while True:
        up = desktop.is_up()
        if up:
            down_since = None
            if not shown:
                time.sleep(0.8)  # chờ giao diện nạp xong mã
                win.load_url(URL)
                shown = True
        else:
            if shown:
                win.load_html(_splash("Đang kết nối lại…"))
                shown = False
            down_since = down_since or time.time()
            if time.time() - down_since > 45:  # giao diện tắt hẳn: bật lại
                threading.Thread(target=start_ui, daemon=True).start()
                down_since = time.time()
        time.sleep(4 if shown else 1)


def run(start_ui) -> bool:
    """Mở cửa sổ app. Trả về False nếu máy không mở được kiểu này hoặc bác chọn mở bằng Chrome
    (khi đó dùng cửa sổ Chrome như cũ)."""
    try:
        from .config import load_settings
        if load_settings().get("ui_window") == "chrome":  # bộ gõ tiếng Việt lỗi trong cửa sổ app -> dùng Chrome
            return False
    except Exception:
        pass
    try:
        import webview
    except Exception:
        return False
    if bring_existing():
        return True
    _app_id()
    try:
        webview.settings["ALLOW_DOWNLOADS"] = True
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
    except Exception:
        pass
    try:
        win = webview.create_window(TITLE, html=_splash("Đang khởi động…"), width=1440, height=920,
                                    min_size=(980, 640), background_color="#eef2ff", text_select=True)
        store = DATA_DIR / "cua_so"
        store.mkdir(parents=True, exist_ok=True)
        webview.start(_watch, (win, start_ui), gui="edgechromium" if _win() else None, private_mode=False,
                      storage_path=str(store))
        return True
    except Exception as e:
        try:
            (DATA_DIR / "logs").mkdir(parents=True, exist_ok=True)
            with open(DATA_DIR / "logs" / "giao_dien.log", "a", encoding="utf-8") as f:
                f.write(f"Không mở được cửa sổ app riêng, dùng Chrome: {type(e).__name__}: {e}\n")
        except Exception:
            pass
        return False
