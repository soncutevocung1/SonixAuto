"""Chrome của kênh: mỗi kênh 1 cửa sổ Chrome thật (hồ sơ riêng của kênh), mở 1 lần rồi để đó.

Tool gắn vào cửa sổ đang mở (cổng điều khiển chỉ mở trên máy này 127.0.0.1), mỗi việc mở 1 tab mới, xong đóng tab,
KHÔNG tắt Chrome. Bác đăng nhập / xem bài / xác minh ngay trong cửa sổ đó như Chrome bình thường.
Chrome (từ bản 136) không cho điều khiển hồ sơ Chrome chính của máy, nên mỗi kênh dùng hồ sơ riêng (thư mục
data/profiles/<kênh>, chính là hồ sơ tool đang dùng, đã có sẵn đăng nhập).
"""
import json
import subprocess
import sys
import time
import urllib.request

from .config import DATA_DIR, profile_dir, slug

PORTS = DATA_DIR / "chrome_kenh.json"
BASE_PORT = 9310
URL_START = "https://www.tiktok.com/tiktokstudio"


def enabled(settings) -> bool:
    return bool(settings.get("chrome_kenh", True))


def port_for(channel) -> int:
    """Mỗi kênh 1 cổng cố định (lưu lại để lần sau vẫn đúng cổng)."""
    try:
        m = json.loads(PORTS.read_text(encoding="utf-8"))
    except Exception:
        m = {}
    key = slug(channel)
    if key not in m:
        used = set(m.values())
        p = BASE_PORT
        while p in used:
            p += 1
        m[key] = p
        PORTS.parent.mkdir(parents=True, exist_ok=True)
        PORTS.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    return int(m[key])


def is_open(channel) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port_for(channel)}/json/version", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def args(settings, channel, url=URL_START) -> list:
    return [f"--remote-debugging-port={port_for(channel)}", f"--user-data-dir={profile_dir(settings, channel)}",
            "--no-first-run", "--no-default-browser-check", "--lang=vi-VN", url]


def open_chrome(settings, channel, chrome, url=URL_START, wait=20) -> bool:
    """Mở cửa sổ Chrome của kênh (nếu chưa mở). True khi cổng điều khiển đã sẵn sàng."""
    if is_open(channel):
        return True
    if not chrome:
        return False
    flags = 0x00000008 | 0x00000200 if sys.platform == "win32" else 0  # chạy riêng, tắt tool không tắt Chrome
    subprocess.Popen([chrome] + args(settings, channel, url), creationflags=flags,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
    end = time.time() + wait
    while time.time() < end:
        if is_open(channel):
            return True
        time.sleep(0.5)
    return False


class CdpCtx:
    """Bọc Chrome đang mở cho giống trình duyệt cũ của tool: chỉ thấy/đóng các tab tool tự mở."""

    def __init__(self, browser):
        self._b = browser
        self._c = browser.contexts[0] if browser.contexts else browser.new_context()
        self._own = []

    @property
    def pages(self):
        return [p for p in self._own if not p.is_closed()]

    def new_page(self):
        p = self._c.new_page()
        self._own.append(p)
        return p

    def close(self):
        for p in self._own:
            try:
                if not p.is_closed():
                    p.close()
            except Exception:
                pass
        try:
            self._b.close()  # chỉ ngắt kết nối, cửa sổ Chrome của kênh vẫn mở
        except Exception:
            pass

    def __getattr__(self, name):
        return getattr(self._c, name)


def connect(p, settings, channel, chrome):
    """Gắn vào Chrome của kênh (tự mở nếu chưa mở). Trả về CdpCtx hoặc None (dùng cách cũ)."""
    if not enabled(settings) or not chrome:
        return None
    if not open_chrome(settings, channel, chrome):
        return None
    try:
        return CdpCtx(p.chromium.connect_over_cdp(f"http://127.0.0.1:{port_for(channel)}", timeout=20000))
    except Exception:
        return None
