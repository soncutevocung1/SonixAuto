"""Điều khiển TikTok Studio trên web (trình duyệt riêng của từng kênh).

Các bước làm theo đúng giao diện TikTok Studio tiếng Việt:
  Tải video -> Mô tả -> Ảnh bìa -> Thêm liên kết (Sản phẩm -> Trưng bày -> Tên sản phẩm) -> Âm thanh
  -> Người xem -> Khai báo -> Lên lịch -> Đăng.
Bước nào tool không làm được: hiện thanh xanh trên trang nhờ người dùng làm tay rồi bấm TIẾP TỤC.
"""
import random
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

from .config import DEBUG_DIR, LOCK_DIR, SHOWCASE_DIR, SOUNDS_DIR, WORK_DIR, get_channel, norm, profile_dir, slug

UPLOAD_URL = "https://www.tiktok.com/tiktokstudio/upload?from=webapp&lang=vi-VN"
LOGIN_URL = "https://www.tiktok.com/login?lang=vi-VN"


class NeedLogin(Exception):
    """Chưa đăng nhập / đăng nhập sai kênh -> dừng cả kênh, người dùng xử lý tay."""


class BrowserBusy(Exception):
    """Trình duyệt của kênh đang được mở ở chỗ khác."""


class TikTokError(Exception):
    pass


# =============================== Trình duyệt ===============================
CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    str(Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe"),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def chrome_exe():
    return next((p for p in CHROME_PATHS if Path(p).exists()), "")


class ProfileLock:
    """Khoá để 2 việc của tool không mở cùng 1 hồ sơ trình duyệt cùng lúc."""

    def __init__(self, channel):
        self.f = LOCK_DIR / f"{slug(channel)}.lock"
        self.channel = channel

    def __enter__(self):
        LOCK_DIR.mkdir(parents=True, exist_ok=True)
        if self.f.exists() and time.time() - self.f.stat().st_mtime < 30 * 60:
            raise BrowserBusy(f"Tool đang dùng trình duyệt kênh «{self.channel}» cho việc khác, đợi xong rồi thử lại.")
        self.f.write_text(str(time.time()))
        return self

    def touch(self):
        try:
            self.f.write_text(str(time.time()))
        except Exception:
            pass

    def __exit__(self, *a):
        try:
            self.f.unlink()
        except Exception:
            pass


def is_busy(channel) -> bool:
    f = LOCK_DIR / f"{slug(channel)}.lock"
    return f.exists() and time.time() - f.stat().st_mtime < 30 * 60


def launch(p, settings, channel, headless=False):
    opts = dict(user_data_dir=str(profile_dir(settings, channel)), headless=headless,
                viewport={"width": 1440, "height": 900}, locale="vi-VN",
                args=["--disable-blink-features=AutomationControlled", "--lang=vi-VN"],
                ignore_default_args=["--enable-automation"], accept_downloads=True)
    errors = []
    for extra in ({"channel": "chrome", "chromium_sandbox": True}, {"channel": "chrome"}, {}):
        try:
            ctx = p.chromium.launch_persistent_context(**extra, **opts)
            ctx.add_init_script(HIDE_TOURS_JS)  # ẩn hộp hướng dẫn ngay từ khi mở trang
            ctx.on("page", lambda pg: pg.on("dialog", lambda d: d.accept()))
            for pg in ctx.pages:
                pg.on("dialog", lambda d: d.accept())
            return ctx
        except Exception as e:
            errors.append(str(e))
    msg = " | ".join(errors)
    raise BrowserBusy(
        f"Không mở được trình duyệt của kênh «{channel}». Thường là do bác ĐANG MỞ trình duyệt kênh này "
        f"(biểu tượng ngoài màn hình). Tắt cửa sổ đó rồi bấm 'Chạy tiếp'. Chi tiết: {msg[:300]}")


SPEED = 1.0  # 0.5 = đăng nhanh (chờ ngắn hơn giữa các bước), 1 = bình thường


def _sleep(a=0.6, b=1.5):
    time.sleep(random.uniform(a, b) * SPEED)


def dump_debug(page, name):
    """Chụp màn hình + lưu HTML khi có lỗi, để gửi cho người hỗ trợ."""
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    stem = DEBUG_DIR / f"{datetime.now():%m%d_%H%M%S}_{slug(name)}"
    try:
        page.screenshot(path=f"{stem}.png", full_page=False)
        Path(f"{stem}.html").write_text(page.content(), encoding="utf-8")
    except Exception:
        pass
    return f"{stem}.png"


# =============================== Thanh hỏi người dùng ===============================
BANNER_JS = """
([msg, btn]) => {
  window.__sx_continue = false;
  let el = document.getElementById('__sx_banner'); if (el) el.remove();
  el = document.createElement('div'); el.id = '__sx_banner';
  el.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:2147483647;background:#1b5e20;color:#fff;' +
    'font:600 16px/1.45 Arial,sans-serif;padding:12px 16px;display:flex;gap:16px;align-items:center;' +
    'box-shadow:0 2px 10px rgba(0,0,0,.45)';
  const t = document.createElement('div'); t.style.flex = '1'; t.innerText = '[SonixDangVideo] ' + msg;
  const b = document.createElement('button'); b.innerText = btn;
  b.style.cssText = 'background:#ffeb3b;color:#000;border:0;border-radius:6px;padding:10px 18px;font:700 16px Arial;cursor:pointer;white-space:nowrap';
  b.onclick = () => { window.__sx_continue = true; el.remove(); };
  el.appendChild(t); el.appendChild(b); document.body.appendChild(el);
}
"""


def ask_user(page, msg, btn="✅ TIẾP TỤC", timeout_min=20, lock=None):
    page.bring_to_front()
    page.evaluate(BANNER_JS, [msg, btn])
    end = time.time() + timeout_min * 60
    while time.time() < end:
        try:
            if page.evaluate("window.__sx_continue === true"):
                return
            if page.evaluate("!document.getElementById('__sx_banner')"):
                page.evaluate(BANNER_JS, [msg, btn])
        except Exception:
            pass
        if lock:
            lock.touch()
        time.sleep(1)
    raise TikTokError(f"Hết {timeout_min} phút chờ bấm «{btn}»")


# =============================== Tìm & bấm ===============================
def _visible(locator, timeout=0.0, last=False):
    end = time.time() + timeout
    while True:
        try:
            n = min(locator.count(), 30)
            for i in (range(n - 1, -1, -1) if last else range(n)):
                el = locator.nth(i)
                if el.is_visible():
                    return el
        except Exception:
            pass
        if time.time() >= end:
            return None
        time.sleep(0.4)


def _rx(p):
    return re.compile(p, re.I)


def click_text(scope, pattern, timeout=0.0):
    el = _visible(scope.get_by_text(_rx(pattern)), timeout)
    if el:
        try:
            el.click()
            return True
        except Exception:
            pass
    return False


def click_button(scope, pattern, timeout=0.0, enabled=True, last=True):
    """Bấm nút theo chữ. Mặc định lấy nút cuối cùng (nút trong hộp thoại nằm sau nút trên trang)."""
    end = time.time() + timeout
    while True:
        el = _visible(scope.get_by_role("button", name=_rx(pattern)), last=last)
        if el:
            try:
                if not enabled or (el.is_enabled() and el.get_attribute("aria-disabled") != "true"):
                    el.click()
                    return True
            except Exception:
                pass
        if time.time() >= end:
            return False
        time.sleep(0.4)


def top_modal(page):
    """Hộp thoại đang mở trên cùng (hoặc cả trang nếu không thấy)."""
    for sel in ('[role="dialog"]', '[class*="Modal"]', '[class*="modal"]', '[class*="Dialog"]'):
        loc = page.locator(sel)
        try:
            n = loc.count()
            for i in range(n - 1, -1, -1):
                el = loc.nth(i)
                if el.is_visible():
                    box = el.bounding_box()
                    if box and box["width"] > 250 and box["height"] > 120:
                        return el
        except Exception:
            pass
    return page


def wait_modal_text(page, pattern, timeout=15.0):
    end = time.time() + timeout
    while time.time() < end:
        if _visible(page.get_by_text(_rx(pattern))):
            return True
        time.sleep(0.4)
    return False


def set_switch(page, label_pattern, on=True):
    label = _visible(page.get_by_text(_rx(label_pattern)), 3)
    if not label:
        return False
    label.scroll_into_view_if_needed()
    box = label.locator("xpath=ancestor::*[.//*[@role='switch'] or .//input[@type='checkbox']][1]")
    sw = box.locator("[role='switch'], input[type='checkbox']").first
    try:
        st = sw.get_attribute("aria-checked")
        checked = (st == "true") if st is not None else sw.is_checked()
    except Exception:
        checked = None
    if checked == on:
        return True
    try:
        sw.click(force=True)
    except Exception:
        label.click()
    _sleep()
    click_button(page, r"^(Bật|Turn on|Xác nhận|Confirm|OK)$", timeout=2)
    return True


HIDE_CSS = ('#react-joyride-portal,[id^="react-joyride-step"],.react-joyride__overlay,.react-joyride__spotlight'
            '{display:none!important;pointer-events:none!important}')
HIDE_TOURS_JS = """(() => { const add = () => { if (document.getElementById('__sx_hide')) return;
  const s = document.createElement('style'); s.id = '__sx_hide'; s.textContent = '%s';
  (document.head || document.documentElement).appendChild(s); };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', add); else add(); })();""" % HIDE_CSS

POPUP_JS = r"""
() => { let n = 0;
  document.querySelectorAll('.react-joyride__tooltip button, [role=alertdialog] button').forEach(b => {
    const t = (b.innerText || b.getAttribute('aria-label') || '').trim();
    if (/^(Đã hiểu|Got it|Xong|Done|Bỏ qua|Skip|Đóng|Close)$/i.test(t)) { b.click(); n++; } });
  return n; }
"""


def clear_popups(page):
    """Tắt hộp hướng dẫn / giới thiệu tính năng mới (hay hiện với hồ sơ mới đăng nhập)."""
    for _ in range(4):
        if not click_button(page, r"^(Đã hiểu|Got it|Bỏ qua|Skip|Để sau|Not now|Tôi đã hiểu|Tiếp tục chỉnh sửa|Continue editing)$", timeout=0.5):
            break
        _sleep(0.5, 1)
    try:
        page.evaluate(POPUP_JS)
        page.evaluate(HIDE_TOURS_JS)
    except Exception:
        pass


# =============================== Kiểm tra đăng nhập ===============================
def detect_handle(page) -> str:
    js = """async () => { try { const r = await fetch('https://www.tiktok.com/passport/web/account/info/?aid=1988&app_name=tiktok_web',
             {credentials: 'include'}); return await r.text(); } catch (e) { return ''; } }"""
    try:
        m = re.search(r'"username"\s*:\s*"([^"]+)"', page.evaluate(js) or "")
        if m:
            return m.group(1)
    except Exception:
        pass
    try:
        m = re.search(r'"uniqueId"\s*:\s*"([^"]+)"', page.content())
        if m:
            return m.group(1)
    except Exception:
        pass
    return ""


def open_upload(page, settings, channel, log=print):
    page.goto(UPLOAD_URL, wait_until="domcontentloaded", timeout=90000)
    _sleep(3, 5)
    if "login" in page.url:
        raise NeedLogin(f"Trình duyệt kênh «{channel}» CHƯA ĐĂNG NHẬP TikTok. Vào tab Kênh & sản phẩm → "
                        f"bấm 'Đăng nhập' cho kênh này, đăng nhập xong bấm 'Chạy tiếp'.")
    want = ((get_channel(settings, channel) or {}).get("handle") or "").strip().lstrip("@").lower()
    if want:
        got = detect_handle(page).lower()
        if got and got != want:
            raise NeedLogin(f"Trình duyệt kênh «{channel}» đang đăng nhập @{got}, KHÔNG PHẢI @{want}. "
                            f"Bác đăng xuất rồi đăng nhập đúng kênh @{want}.")
        if got:
            log(f"  - Đúng kênh @{got} ✔")


def upload_file(page, video):
    inp = page.locator('input[type="file"]').first
    inp.wait_for(state="attached", timeout=60000)
    inp.set_input_files(video)
    page.locator('div[contenteditable="true"]').first.wait_for(state="visible", timeout=180000)


def post_button(page):
    btn = page.locator('button[data-e2e="post_video_button"]')
    try:
        if btn.count():
            return btn.first
    except Exception:
        pass
    return _visible(page.get_by_role("button", name=_rx(r"^(Đăng|Post|Lên lịch|Schedule)$")))


def _ready(btn):
    try:
        return (btn.is_enabled() and btn.get_attribute("aria-disabled") != "true"
                and btn.get_attribute("data-disabled") != "true")
    except Exception:
        return False


def wait_uploaded(page, minutes=15, lock=None):
    end = time.time() + minutes * 60
    while time.time() < end:
        if _visible(page.get_by_text(_rx(r"(Tải lên thất bại|Upload failed|Không thể tải lên)"))):
            raise TikTokError("TikTok báo tải video lên thất bại (file lỗi hoặc mạng yếu)")
        done = _visible(page.get_by_text(_rx(r"^(Đã tải lên|Uploaded)")))
        btn = post_button(page)
        if done and btn and _ready(btn):
            clear_popups(page)
            return
        if done and btn:
            _sched_error(page, 0)
        if lock:
            lock.touch()
        time.sleep(2)
    raise TikTokError(f"Quá {minutes} phút video chưa tải lên xong")


def type_caption(page, caption, hashtags):
    from .caption import caption_tags
    have = set(caption_tags(caption))
    hashtags = [t for t in hashtags if t not in have]  # tag đã có trong caption thì không gõ lại (tránh lặp 2 lần)
    clear_popups(page)
    ed = page.locator('div[contenteditable="true"]').first
    ed.click()
    page.keyboard.press("ControlOrMeta+a")
    page.keyboard.press("Delete")
    _sleep(0.3, 0.6)
    lines = (caption or "").strip().split("\n")
    for i, line in enumerate(lines):
        if line:
            page.keyboard.type(line, delay=random.randint(3, 8) if SPEED < 1 else random.randint(12, 35))
        if i < len(lines) - 1:
            page.keyboard.press("Shift+Enter")
    if hashtags:
        page.keyboard.press("Shift+Enter")
        page.keyboard.press("Shift+Enter")
        for tag in hashtags:
            page.keyboard.type("#" + tag, delay=random.randint(15, 30) if SPEED < 1 else random.randint(40, 80))
            time.sleep(0.9 if SPEED < 1 else 1.6)  # chờ TikTok hiện gợi ý hashtag rồi mới bấm cách
            page.keyboard.press("Space")
            _sleep(0.3, 0.6)


# =============================== Ảnh bìa ===============================
def set_cover_checked(page, cover_path, log=print):
    """Đặt ảnh bìa rồi đọc lại file ảnh trong ô bìa để chắc đã đổi (đúng bìa ~99 điểm, khung video ~30-55).
    Chưa đổi thì làm lại 1 lần. Sau khi hẹn giờ tool còn kiểm tra lần nữa trên TikTok Studio."""
    set_cover(page, cover_path)
    sc = cover_score(page, cover_path)
    if 0 <= sc < 80:
        log(f"    (ảnh bìa chưa đổi, điểm {sc:.0f}, làm lại)")
        try:
            page.keyboard.press("Escape")
            set_cover(page, cover_path)
        except Exception as e:
            log(f"    (làm lại ảnh bìa lỗi: {str(e)[:100]})")
        sc = cover_score(page, cover_path)
    log(f"    ảnh bìa trên trang: {sc:.0f}/100" if sc >= 0 else "    (không đọc được ô ảnh bìa)")
    if 0 <= sc < 80:
        raise TikTokError(f"ảnh bìa không lên (điểm {sc:.0f})")
    return True


def set_cover(page, cover_path):
    if not cover_path or not Path(cover_path).exists():
        return True
    clear_popups(page)
    if not click_text(page, r"^(Sửa ảnh bìa|Edit cover)$", timeout=4):
        img = _visible(page.get_by_text(_rx(r"^Ảnh bìa$")).locator("xpath=following::img[1]"), 2)
        if not img:
            raise TikTokError("không thấy nút Sửa ảnh bìa")
        img.click()
    _sleep(1.5, 2.5)
    modal = top_modal(page)
    click_text(modal, r"^(Tải lên|Upload|Tải ảnh lên)$", timeout=5)
    _sleep(1, 1.5)
    inp = modal.locator('input[type="file"]')
    if not inp.count():
        inp = page.locator('input[type="file"][accept*="image"]')
    inp.last.set_input_files(cover_path)
    _sleep(2.5, 4)
    if not click_button(modal, r"^(Xác nhận|Lưu|Xong|Áp dụng|Confirm|Save|Done|Apply)$", timeout=10):
        raise TikTokError("không bấm được nút xác nhận ảnh bìa")
    try:  # chờ TikTok tải ảnh bìa lên máy chủ xong rồi mới làm bước khác
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    _sleep(2.5, 3.5)
    return True


def image_similarity(shot, ref_path) -> float:
    """Ảnh TikTok hiển thị (shot: ảnh PIL hoặc bytes) giống file ảnh bìa đến đâu (0-100).
    Cắt ảnh gốc theo đúng tỉ lệ ảnh hiển thị (TikTok hay cắt 3:4) rồi so từng điểm ảnh ở kích thước nhỏ."""
    import io
    from PIL import Image, ImageChops, ImageStat
    if isinstance(shot, (bytes, bytearray)):
        shot = Image.open(io.BytesIO(shot))
    a = shot.convert("L")
    b = Image.open(ref_path).convert("L")
    ra, rb = a.width / a.height, b.width / b.height
    if rb > ra:  # gốc rộng hơn -> cắt 2 bên
        w = int(b.height * ra)
        b = b.crop(((b.width - w) // 2, 0, (b.width - w) // 2 + w, b.height))
    elif rb < ra:  # gốc cao hơn -> cắt trên dưới
        h = int(b.width / ra)
        b = b.crop((0, (b.height - h) // 2, b.width, (b.height - h) // 2 + h))
    size = (32, max(8, int(32 / ra)))
    d = ImageStat.Stat(ImageChops.difference(a.resize(size), b.resize(size))).mean[0]
    return max(0.0, 100 - d / 255 * 100 * 2.5)


BLOB_JS = """async (src) => { const b = await (await fetch(src)).blob();
  return await new Promise(r => { const f = new FileReader(); f.onload = () => r(f.result); f.readAsDataURL(b); }); }"""


def cover_score(page, cover_path) -> float:
    """Ảnh bìa trang đăng đang giữ giống file bìa đến đâu (0-100). Lấy thẳng file ảnh của ô 'Ảnh bìa'
    (không chụp màn hình vì dễ lệch). Trả -1 nếu không đọc được."""
    import base64
    try:
        img = _visible(page.locator('[data-e2e="cover_container"] img'), 3)
        if not img:
            return -1
        src = img.get_attribute("src") or ""
        if src.startswith("blob:") or src.startswith("http"):
            data = page.evaluate(BLOB_JS, src)
            raw = base64.b64decode(data.split(",", 1)[1])
        elif src.startswith("data:"):
            raw = base64.b64decode(src.split(",", 1)[1])
        else:
            return -1
        return image_similarity(raw, cover_path)
    except Exception:
        return -1


# =============================== Gắn sản phẩm (giỏ hàng) ===============================
def _open_add_link(page):
    clear_popups(page)
    label = _visible(page.get_by_text(_rx(r"^(Thêm liên kết|Add link)$")), 5)
    btn = None
    if label:
        label.scroll_into_view_if_needed()
        btn = _visible(label.locator("xpath=following::button[contains(normalize-space(.),'Thêm') or "
                                     "contains(normalize-space(.),'Add')][1]"))
    if not btn:
        btn = _visible(page.get_by_role("button", name=_rx(r"^\+?\s*(Thêm|Add)$")), 3)
    if not btn:
        raise TikTokError("không thấy nút '+ Thêm' ở mục Thêm liên kết")
    btn.click()
    if not wait_modal_text(page, r"^(Loại liên kết|Link type|Thêm liên kết sản phẩm)$", 10):
        raise TikTokError("không mở được hộp Thêm liên kết")
    _sleep()
    modal = top_modal(page)
    if _visible(modal.get_by_text(_rx(r"^(Loại liên kết|Link type)$"))):
        if not _visible(modal.get_by_text(_rx(r"^(Sản phẩm|Products?)$"))):
            click_text(modal, r"(Chọn|Select)", 2)
            click_text(page, r"^(Sản phẩm|Products?)$", 3)
        if not click_button(modal, r"^(Tiếp|Next)$", timeout=8):
            raise TikTokError("không bấm được 'Tiếp' ở hộp Thêm liên kết")
    if not wait_modal_text(page, r"(Trưng bày sản phẩm|Showcase|Tìm kiếm sản phẩm)", 15):
        raise TikTokError("không mở được danh sách Trưng bày sản phẩm")
    _sleep(1, 2)


def _row_of(page, pid):
    el = _visible(page.get_by_text(str(pid), exact=True))
    if not el:
        return None
    return el.locator("xpath=ancestor::*[.//input[@type='radio'] or .//*[@role='radio']][1]")


def _search(page, text):
    box = _visible(page.get_by_placeholder(_rx(r"(Tìm kiếm sản phẩm|Search)")), 5)
    if not box:
        return False
    box.click()
    box.fill("")
    if text:
        box.type(text, delay=30)
    box.press("Enter")
    _sleep(1.8, 2.8)
    return True


def _goto_page(modal, k):
    btn = _visible(modal.locator("button, li").filter(has_text=re.compile(rf"^\s*{k}\s*$")))
    if not btn:
        return False
    btn.click()
    _sleep(1.5, 2.5)
    return True


def _find_product(page, pid, name):
    row = _row_of(page, pid)
    if row:
        return row
    for q in (str(pid), (name or "")[:28]):
        if q and _search(page, q):
            row = _row_of(page, pid)
            if row:
                return row
    _search(page, "")
    modal = top_modal(page)
    for k in range(2, 40):
        if not _goto_page(modal, k):
            break
        row = _row_of(page, pid)
        if row:
            return row
    return None


def _dialog_of(el, *btn_texts):
    """Khung hộp thoại gần nhất chứa phần tử el VÀ chứa nút có chữ btn_texts."""
    xps = []
    if btn_texts:
        cond = " or ".join(f"normalize-space(.)='{t}'" for t in btn_texts)
        xps.append(f"xpath=ancestor::*[.//button[{cond}]][1]")
    xps += ["xpath=ancestor::*[(@role='dialog' or contains(@class,'odal')) and count(.//button)>=2][1]",
            "xpath=ancestor::*[count(.//button)>=2][1]"]
    for xp in xps:
        loc = el.locator(xp)
        try:
            if loc.count():
                return loc.first
        except Exception:
            pass
    return el.page


NAME_HINT = r"^(Tên sản phẩm sẽ hiển thị|Product name will|The product name will)"
LIST_HINT = r"^(Trưng bày sản phẩm|Showcase|Product showcase)$"


PRODUCT_MODAL = r"^(Thêm liên kết sản phẩm|Add product links?|Tên sản phẩm sẽ hiển thị|Product name will)"


def _close_product_modal(page, wait=0.5):
    """Đóng hộp 'Thêm liên kết sản phẩm' nếu còn mở (để không che các bước sau)."""
    for _ in range(3):
        t = _visible(page.get_by_text(_rx(PRODUCT_MODAL)), wait)
        if not t:
            return True
        dlg = _dialog_of(t, "Hủy", "Cancel")
        if not click_button(dlg, r"^(Hủy|Cancel)$", timeout=2, last=False):
            page.keyboard.press("Escape")
        _sleep(0.8, 1.2)
    return not _visible(page.get_by_text(_rx(PRODUCT_MODAL)), 0.5)


def add_product(page, prod, cart_name, log=print):
    """Gắn 1 sản phẩm. Lỗi thì chụp màn hình ngay lúc đó rồi đóng hộp sản phẩm cho các bước sau chạy được."""
    try:
        _add_product(page, prod, cart_name, log)
    except Exception:
        dump_debug(page, "gan_sp_luc_loi")
        _close_product_modal(page)
        raise


def _add_product(page, prod, cart_name, log=print):
    """Gắn 1 sản phẩm theo đúng các bước TikTok Studio."""
    _open_add_link(page)
    row = _find_product(page, prod["id"], prod.get("name"))
    if not row:
        raise TikTokError(f"không thấy sản phẩm ID {prod['id']} trong Trưng bày (có thể đã bị gỡ khỏi giỏ)")
    row.scroll_into_view_if_needed()
    radio = row.locator("input[type='radio'], [role='radio']").first
    try:
        radio.click(force=True)
    except Exception:
        row.click()
    _sleep()
    lab = _visible(page.get_by_text(_rx(LIST_HINT)), 3)
    dlg = _dialog_of(lab, 'Tiếp', 'Next') if lab else top_modal(page)
    name_lab = None
    for attempt in range(3):
        click_button(dlg, r"^(Tiếp|Next)$", timeout=6)
        name_lab = _visible(page.get_by_text(_rx(NAME_HINT)), 8)
        if name_lab:
            break
        row.click()  # chọn lại dòng rồi bấm Tiếp lần nữa
        _sleep()
    if not name_lab:
        raise TikTokError("chọn sản phẩm xong nhưng không sang được bước đặt Tên sản phẩm")
    ndlg = _dialog_of(name_lab, 'Thêm', 'Add')
    inp = _visible(ndlg.locator("input:not([type=radio]):not([type=checkbox]):not([type=hidden]), textarea"), 5)
    if not inp:
        raise TikTokError("không thấy ô nhập Tên sản phẩm")
    inp.click()
    inp.press("ControlOrMeta+a")
    inp.press("Delete")
    inp.type((cart_name or prod.get("name", ""))[:30], delay=35)
    _sleep()
    if not click_button(ndlg, r"^(Thêm|Add)$", timeout=8):
        raise TikTokError("không bấm được nút 'Thêm' sau khi đặt tên")
    end = time.time() + 12
    while time.time() < end and _visible(page.get_by_text(_rx(NAME_HINT))):
        time.sleep(0.5)
    _sleep(1, 2)
    log(f"    ✔ Đã gắn sản phẩm …{str(prod['id'])[-6:]} tên «{cart_name}»")


# =============================== Âm thanh ===============================
# Trình chỉnh sửa Âm thanh của TikTok Studio có 4 mục: Đề xuất · Yêu thích · Không giới hạn · Gần đây
SOUND_PANELS = {"suggest": "panel-for_you", "favorites": "panel-favorites", "unlimited": "panel-unlimited",
                "recent": "panel-recent_use"}
SOUND_TABS = {"suggest": r"^(Đề xuất|For you|Recommended)$", "favorites": r"^(Yêu thích|Favorites?)$",
              "unlimited": r"^(Không giới hạn|Unlimited)$", "recent": r"^(Gần đây|Recent)$"}
SOUND_SEARCH = 'input[placeholder="Tìm kiếm âm thanh"], input[placeholder*="Search sound" i]'
# "original sound - ..." thường là giọng nói của người khác, không phải nhạc -> bỏ qua
SKIP_SOUND = re.compile(r"^(original sound|âm thanh gốc|son original|som original|nhạc nền -)", re.I)
AUTO_MUSIC = {
    "smart": "Tự động: có giỏ → nhạc thương mại, không giỏ → nhạc đề xuất",
    "suggest": "Tự động: nhạc TikTok đề xuất (hợp xu hướng)",
    "unlimited": "Tự động: nhạc thương mại 'Không giới hạn' (an toàn bản quyền)",
    "favitem": "Tự động: âm thanh Yêu thích đúng sản phẩm (gắn ở tab Nhạc nền)",
}

SOUND_ITEMS_JS = r"""
(panel) => {
  document.querySelectorAll('[data-sx-row]').forEach(e => e.removeAttribute('data-sx-row'));
  const root = panel ? document.getElementById(panel) : document;
  if (!root) return [];
  const items = Array.from(root.querySelectorAll('[role=listitem][data-item-id]'))
    .filter(li => li.getBoundingClientRect().width > 0);
  return items.map((li, i) => {
    li.setAttribute('data-sx-row', i);
    const t = ((li.querySelector('[class*=infoBasicTitle]') || {}).innerText || '').trim();
    const d = ((li.querySelector('[class*=infoBasicDesc]') || {}).innerText || '').trim();
    const m = d.match(/(\d{1,2}):(\d{2})/);
    return {i, id: li.getAttribute('data-item-id'), title: t,
            artist: d.replace(/^\s*\d{1,2}:\d{2}\s*[·•\-]?\s*/, ''),
            duration: m ? m[0] : '', sec: m ? (+m[1]) * 60 + (+m[2]) : 0};
  });
}
"""
SOUND_ROWS_JS = "() => (" + SOUND_ITEMS_JS + ")('panel-favorites')"   # giữ tên cũ cho phần đồng bộ Yêu thích


def _sound_box(page, timeout=0.0):
    return _visible(page.locator(SOUND_SEARCH), timeout)


def _open_sound_editor(page):
    """Mở trình chỉnh sửa Âm thanh (nếu đang mở rồi thì thôi)."""
    clear_popups(page)
    if _sound_box(page, 1):
        return
    btn = _visible(page.get_by_text(_rx(r"^(Âm thanh|Sounds?)$")), 5)
    if not btn:
        raise TikTokError("không thấy nút Âm thanh")
    btn.click()
    if not _sound_box(page, 20):
        raise TikTokError("bấm Âm thanh nhưng trình chỉnh sửa không mở")
    _sleep(2, 3)
    clear_popups(page)


def _close_sound_editor(page):
    """Thoát trình chỉnh sửa Âm thanh không lưu (khi có lỗi)."""
    try:
        if not _sound_box(page, 1):
            return
        click_button(page, r"^(Hủy|Cancel)$", timeout=3)
        _sleep(1, 1.5)
        # CHỈ bấm "Hủy bỏ" trong hộp hỏi "Hủy bỏ chỉnh sửa này?" — nút "Hủy bỏ" ngoài trang đăng là XOÁ BÀI
        q = _visible(page.get_by_text(_rx(r"^(Hủy bỏ chỉnh sửa|Discard (this |these )?edit)")), 3)
        if q:
            click_button(q.locator("xpath=ancestor::*[.//button][1]"), r"^(Hủy bỏ|Discard)$", timeout=3)
            _sleep(1, 1.5)
    except Exception:
        pass


def _sound_list(page, mode):
    """Bấm sang mục (Đề xuất / Yêu thích / Không giới hạn) và đọc danh sách bài."""
    tab = _visible(page.get_by_role("tab", name=_rx(SOUND_TABS[mode])), 5)
    if tab:
        tab.click()
    elif not click_text(page, SOUND_TABS[mode], timeout=5):
        raise TikTokError(f"không thấy mục {mode} trong Âm thanh")
    end = time.time() + 15
    while time.time() < end:
        rows = page.evaluate(SOUND_ITEMS_JS, SOUND_PANELS[mode])
        if rows:
            return rows
        if _visible(page.get_by_text(_rx(r"(Không có kết quả|No results)")), 0.5):
            return []
        time.sleep(0.6)
    return []


def _sound_search(page, keyword):
    box = _sound_box(page, 5)
    if not box:
        raise TikTokError("không thấy ô Tìm kiếm âm thanh")
    box.fill(keyword)
    box.press("Enter")
    end = time.time() + 15
    while time.time() < end:
        time.sleep(1.5)
        rows = page.evaluate(SOUND_ITEMS_JS, None)
        if rows:
            return rows
    return []


def _pick_sound(rows, min_sec=0, top=3):
    good = [r for r in rows if r["title"] and not SKIP_SOUND.match(r["title"])]
    longer = [r for r in good if r["sec"] >= min_sec]
    cands = (longer or good)[:top]
    return random.choice(cands) if cands else None


AUDIO_CLIP = '[class*="AudioClip__root"]'


def _clip_title(page) -> str:
    """Tên bài nhạc đang nằm trên dòng thời gian (trống nếu chưa có)."""
    try:
        el = page.locator('[class*="AudioClip__title"]')
        return el.first.inner_text().strip() if el.count() else ""
    except Exception:
        return ""


def _select_clip(page):
    """Bấm vào bài nhạc trên dòng thời gian để hiện khung Âm lượng."""
    clip = page.locator(AUDIO_CLIP)
    if not clip.count():
        return False
    try:
        clip.first.click(timeout=5000)
    except Exception:
        clip.first.click(force=True, timeout=5000)
    _sleep(0.8, 1.2)
    return True


def _btn_ok(b):
    try:
        return b.count() and b.first.is_visible() and b.first.get_attribute("aria-disabled") != "true" \
            and b.first.get_attribute("data-disabled") != "true"
    except Exception:
        return False


def _add_sound(page, row):
    """Bấm + (thêm) ở 1 bài. Video đã có nhạc thì nút + bị khoá -> chọn bài cũ rồi bấm ⇆ (thay thế)."""
    el = page.locator(f'[data-sx-row="{row["i"]}"]')
    el.scroll_into_view_if_needed()
    el.hover()
    _sleep(0.6, 1.0)
    ops = el.locator("[class*=operation] button")
    plus = ops.filter(has=page.locator('[data-icon="PlusBold"]'))
    swap = ops.filter(has=page.locator('[data-icon="ArrowLeftRight"]'))
    has_clip = page.locator(AUDIO_CLIP).count() > 0
    if not has_clip and _btn_ok(plus):
        plus.first.click()
    elif has_clip and swap.count():  # đã có nhạc: chọn bài cũ rồi ⇆ đổi (bấm + sẽ chồng thêm 1 bài nữa)
        _select_clip(page)
        el.scroll_into_view_if_needed()
        el.hover()
        _sleep(0.6, 1.0)
        swap.first.click()
    else:  # giao diện đổi tên biểu tượng -> bấm nút cuối còn bấm được
        n = ops.count()
        for i in range(n - 1, max(-1, n - 3), -1):
            if _btn_ok(ops.nth(i)):
                ops.nth(i).click()
                break
        else:
            raise TikTokError(f"không bấm được nút thêm bài «{row['title']}»")
    want = row["title"].strip().lower()
    end = time.time() + 12
    while time.time() < end:
        try:
            titles = [t.strip().lower() for t in page.locator('[class*="AudioClip__title"]').all_inner_texts()]
        except Exception:
            titles = []
        if any(t and (t == want or t in want or want in t) for t in titles):
            break
        time.sleep(0.5)
    else:
        raise TikTokError(f"đã bấm thêm «{row['title']}» nhưng nhạc chưa vào video (đang là «{_clip_title(page)}»)")
    if not _visible(page.get_by_text(_rx(r"^(Âm lượng|Volume)$")), 3):
        _select_clip(page)
    _sleep(0.6, 1.0)


def _set_sound_db(page, db):
    """Chỉnh âm lượng bài nhạc (dB). 0 = giữ nguyên, -14 ≈ nhạc nhỏ làm nền cho giọng nói."""
    inp = _visible(page.locator('label:has-text("dB") input'), 3)
    if not inp and _select_clip(page):
        inp = _visible(page.locator('label:has-text("dB") input'), 3)
    if not inp:
        return False
    inp.click()
    inp.press("Control+A")
    inp.type(str(int(db)), delay=60)
    inp.press("Enter")
    _sleep(0.6, 1.0)
    try:
        return abs(float(inp.input_value() or 0) - db) < 1.01
    except Exception:
        return False


def _save_sound(page):
    if not click_button(page, r"^(Lưu|Save)$", timeout=10):
        raise TikTokError("chọn nhạc xong nhưng không thấy nút Lưu")
    end = time.time() + 20
    while time.time() < end and _sound_box(page):
        time.sleep(0.5)
    _sleep(2, 3)


def _apply_sound(page, row, db=None, log=print):
    _add_sound(page, row)
    if db is not None and not _set_sound_db(page, db):
        log("    (không chỉnh được âm lượng nhạc, giữ mặc định)")
    _save_sound(page)


def set_sound(page, title, db=None, log=print):
    """Chọn 1 âm thanh trong mục Yêu thích theo mã số (ưu tiên) hoặc theo tên."""
    from .sounds import parse_ref
    mid, name = parse_ref(title)
    want = name.strip().lower()

    def find(rows):
        return (next((r for r in rows if mid and r["id"] == mid), None)
                or (None if mid else next((r for r in rows if r["title"].strip().lower() == want), None))
                or (None if mid else next((r for r in rows if want and want in r["title"].lower()), None)))

    _open_sound_editor(page)
    try:
        hit = find(_sound_list(page, "favorites"))
        if not hit:
            hit = find(_load_all_favorites(page))
        if not hit:
            raise TikTokError(f"không thấy âm thanh «{name}» trong mục Yêu thích (có thể đã bỏ lưu)")
        _apply_sound(page, hit, db, log)
        return hit["title"]
    except Exception:
        _close_sound_editor(page)
        raise


def set_sound_auto(page, mode, has_cart=False, video_sec=0, db=None, log=print):
    """Tự chọn nhạc: 'suggest' = TikTok đề xuất, 'unlimited' = nhạc thương mại, 'smart' = có giỏ thì thương mại,
    'search:<từ khoá>' = tìm theo từ khoá. Lấy ngẫu nhiên 1 trong 3 bài đầu (bỏ 'original sound' là giọng nói)."""
    if mode == "smart":
        mode = "unlimited" if has_cart else "suggest"
    _open_sound_editor(page)
    try:
        if mode.startswith("search:"):
            kw = mode.split(":", 1)[1].strip()
            rows = _sound_search(page, kw)
            src = f"tìm «{kw}»"
        else:
            rows = _sound_list(page, mode)
            src = {"suggest": "Đề xuất", "unlimited": "Không giới hạn", "favorites": "Yêu thích"}.get(mode, mode)
        pick = _pick_sound(rows, min_sec=min(int(video_sec or 0), 60))
        if not pick and mode != "suggest":
            rows = _sound_list(page, "suggest")
            src += " (không có bài, lấy Đề xuất)"
            pick = _pick_sound(rows, min_sec=min(int(video_sec or 0), 60))
        if not pick:
            raise TikTokError("mục âm thanh không có bài nào phù hợp")
        log(f"    → chọn «{pick['title']}» · {pick['artist']} ({src})")
        _apply_sound(page, pick, db, log)
        return f"{pick['title']} · {pick['artist']}"
    except Exception:
        _close_sound_editor(page)
        raise


# =============================== Người xem / khai báo ===============================
VIS_TEXT = {"public": r"^(Mọi người|Everyone)$", "friends": r"^(Bạn bè|Friends)$",
            "private": r"^(Chỉ mình (tôi|bạn)|Only (me|you))$"}


def set_visibility(page, vis):
    if vis not in VIS_TEXT:
        return True
    clear_popups(page)
    cur = _visible(page.get_by_text(_rx(r"^(Mọi người|Bạn bè|Chỉ mình (tôi|bạn)|Everyone|Friends|Only (me|you))$")), 5)
    if not cur:
        raise TikTokError("không thấy ô 'Người có thể nhìn thấy bài đăng này'")
    if re.match(VIS_TEXT[vis], cur.inner_text().strip(), re.I):
        return True
    cur.scroll_into_view_if_needed()
    cur.click()
    _sleep()
    opts = page.get_by_text(_rx(VIS_TEXT[vis]))
    for i in range(opts.count() - 1, -1, -1):
        if opts.nth(i).is_visible():
            opts.nth(i).click()
            _sleep()
            return True
    raise TikTokError("không chọn được chế độ người xem")


def _tick(page, pattern):
    """Tick ô vuông nằm cạnh dòng chữ khớp pattern, rồi kiểm tra lại đã tick chưa."""
    lab = _visible(page.get_by_text(_rx(pattern)), 4)
    if not lab:
        return False
    lab.scroll_into_view_if_needed()
    box = lab.locator("xpath=ancestor::*[.//input[@type='checkbox'] or .//*[@role='checkbox']][1]") \
        .locator("input[type='checkbox'], [role='checkbox']").first

    def checked():
        try:
            st = box.get_attribute("aria-checked")
            return (st == "true") if st is not None else box.is_checked()
        except Exception:
            return None

    if checked():
        return True
    lab.click()
    _sleep(0.6, 1.0)
    if checked() is False:
        try:
            box.click(force=True)
            _sleep(0.5, 0.8)
        except Exception:
            pass
    return checked() is not False


def set_disclosure(page, ai_content, disclosure):
    """Khai báo nội dung bài đăng: bật công tắc rồi tick 'Thương hiệu của bạn' (hoặc 'Nội dung định hướng
    thương hiệu'). Gắn giỏ hàng xong TikTok tự bật công tắc, tool chỉ cần tick ô."""
    if not ai_content and disclosure == "none":
        return True
    clear_popups(page)
    click_text(page, r"^(Hiển thị thêm|Xem thêm|Show more|Cài đặt nâng cao|Advanced settings)$", timeout=2)
    _sleep()
    ok = True
    if ai_content:
        ok &= set_switch(page, r"(Nội dung (do|được) AI tạo|AI-generated content)", True)
    if disclosure != "none":
        if set_switch(page, r"(Khai báo nội dung bài đăng|Tiết lộ nội dung|Công khai nội dung|"
                            r"Disclose (post|video) content)", True):
            _sleep(0.8, 1.2)
            pat = r"^(Thương hiệu của bạn|Your brand)$" if disclosure == "own_brand" else \
                r"^(Nội dung định hướng thương hiệu|Nội dung có thương hiệu|Branded content)$"
            if not _tick(page, pat):
                raise TikTokError("không tick được ô khai báo nội dung")
        else:
            ok = False
    return ok


# =============================== Hẹn giờ ===============================
INPUTS_JS = r"""
() => Array.from(document.querySelectorAll('input')).filter(i => { const r = i.getBoundingClientRect();
  return r.width > 0 && r.height > 0; }).map((i, k) => { i.setAttribute('data-sx-in', k); return {k, v: i.value}; })
"""

PICK_JS = r"""
([kind, target]) => {
  // tìm cột số trong bảng chọn giờ (giờ 00-23, phút 00-55) rồi bấm đúng số
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const cols = [];
  for (const e of document.querySelectorAll('div,ul')) {
    if (!vis(e)) continue;
    const kids = Array.from(e.children);
    if (kids.length < 10) continue;
    const nums = kids.map(c => (c.innerText || '').trim());
    if (!nums.every(t => /^\d{2}$/.test(t))) continue;
    cols.push({e, nums});
  }
  const col = kind === 'hour' ? cols.find(c => c.nums.includes('23')) : cols.find(c => c.nums.includes('55') || c.nums.includes('59'));
  if (!col) return false;
  const idx = col.nums.indexOf(target);
  if (idx < 0) return false;
  const el = col.e.children[idx]; el.scrollIntoView({block: 'center'}); el.click(); return true;
}
"""


def _read_schedule(page):
    vals = page.evaluate(INPUTS_JS)
    t = next((v for v in vals if re.fullmatch(r"\d{1,2}:\d{2}", v["v"] or "")), None)
    d = next((v for v in vals if re.search(r"\d{4}", v["v"] or "") and re.search(r"[-/.]", v["v"] or "")), None)
    return t, d


def _date_ok(val, dt):
    """Ô ngày có đúng ngày cần hẹn không: so đủ năm-tháng-ngày ĐÚNG VỊ TRÍ.
    (Bản cũ chỉ xem các con số có mặt hay không -> hẹn 11/11 mà ô đang 2026-11-10 vẫn tưởng đúng, vì tháng = 11.)"""
    v = val or ""
    m = re.search(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", v)  # 2026-11-10
    if m:
        return (int(m[1]), int(m[2]), int(m[3])) == (dt.year, dt.month, dt.day)
    m = re.search(r"(\d{1,2})\D+(\d{1,2})\D+(\d{4})", v)  # 10/11/2026 hoặc 10 tháng 11, 2026 (ngày trước)
    if m:
        return (int(m[3]), int(m[2]), int(m[1])) == (dt.year, dt.month, dt.day)
    return False


SCHED_ERR = r"(Lên lịch trước ít nhất|ít nhất 15 phút|at least 15 min)"  # chữ đỏ TikTok hiện khi giờ hẹn quá gần/đã qua


def _sched_error(page, timeout=1.5):
    """TikTok báo giờ hẹn không hợp lệ (chữ đỏ dưới ô giờ) -> báo lỗi ngay, không đứng chờ."""
    el = _visible(page.get_by_text(_rx(SCHED_ERR)), timeout)
    if el:
        try:
            msg = el.inner_text().strip()[:90]
        except Exception:
            msg = "giờ hẹn không hợp lệ"
        raise TikTokError(f"TikTok không nhận giờ hẹn: «{msg}»")


VI_MONTH = {"mot": 1, "gieng": 1, "hai": 2, "ba": 3, "tu": 4, "bon": 4, "nam": 5, "sau": 6, "bay": 7, "tam": 8,
            "chin": 9, "muoi": 10, "muoi mot": 11, "muoi hai": 12, "january": 1, "february": 2, "march": 3,
            "april": 4, "may": 5, "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
            "november": 11, "december": 12}

CAL_PICK_JS = r"""
(day) => {
  // lịch tháng kiểu mới: span.day (ngày chọn được có class 'valid'); bỏ qua ngày của tháng trước/sau
  const cal = Array.from(document.querySelectorAll('.calendar-wrapper')).find(e => e.getBoundingClientRect().width > 0);
  if (!cal) return 'no_cal';
  const days = Array.from(cal.querySelectorAll('span.day'));
  const txt = days.map(d => (d.innerText || '').trim());
  const a = txt.indexOf('1');
  if (a < 0) return 'no_days';
  let b = txt.indexOf('1', a + 1);
  if (b < 0) b = txt.length;
  for (let i = a; i < b; i++) {
    if (txt[i] === String(day)) {
      if (!days[i].classList.contains('valid')) return 'disabled';
      days[i].scrollIntoView({block: 'center'});
      days[i].click();
      return 'ok';
    }
  }
  return 'missing';
}
"""


def _cal_month(page):
    """(năm, tháng) đang hiện trên lịch, đọc từ tiêu đề 'Tháng Mười Một / 2026'. Không đọc được -> None."""
    try:
        cal = page.locator(".calendar-wrapper").first
        mt = norm(cal.locator(".month-title").first.inner_text()).replace("thang", "").strip()
        yr = int(re.sub(r"\D", "", cal.locator(".year-title").first.inner_text()))
        m = int(mt) if mt.isdigit() else VI_MONTH.get(mt)
        return (yr, m) if m else None
    except Exception:
        return None


def _schedule_inputs(page, dt, t, d):
    """Giao diện kiểu ô chữ (08:10 | 2026-11-10): lịch tháng + 2 cột giờ/phút."""
    # Ngày (chọn trước: chọn ngày sau rồi mới mở hết các giờ)
    if not _date_ok(d["v"], dt):
        page.locator(f'[data-sx-in="{d["k"]}"]').click()
        _sleep()
        try:
            page.locator(".calendar-wrapper").first.wait_for(state="visible", timeout=5000)
        except Exception:
            raise TikTokError("bấm ô ngày rồi nhưng không thấy lịch")
        nums = [int(x) for x in re.findall(r"\d+", d["v"])]
        guess = (nums[0], nums[1]) if len(nums) >= 2 and nums[0] > 1000 else None  # lịch mở ở tháng đang chọn
        for _ in range(13):
            cur = _cal_month(page) or guess
            if not cur:
                break
            diff = (dt.year * 12 + dt.month) - (cur[0] * 12 + cur[1])
            if diff == 0:
                break
            page.locator(".calendar-wrapper .month-header-wrapper .arrow").nth(1 if diff > 0 else 0).click()
            guess = (cur[0] + (cur[1] + (1 if diff > 0 else -1) - 1) // 12, (cur[1] + (1 if diff > 0 else -1) - 1) % 12 + 1)
            _sleep(0.4, 0.7)
        r = page.evaluate(CAL_PICK_JS, dt.day)
        if r == "disabled":
            raise TikTokError(f"TikTok không cho chọn ngày {dt:%d/%m/%Y} (đã qua hoặc quá xa)")
        if r != "ok":
            raise TikTokError(f"không chọn được ngày {dt:%d/%m/%Y} trên lịch ({r})")
        _sleep()
        if page.locator(".calendar-wrapper").first.is_visible():
            page.keyboard.press("Escape")
            _sleep(0.3, 0.6)
    # Giờ
    t, _ = _read_schedule(page)
    want_t = f"{dt.hour:02d}:{dt.minute:02d}"
    if t and t["v"] != want_t:
        page.locator(f'[data-sx-in="{t["k"]}"]').click()
        _sleep()
        cols = page.locator(".tiktok-timepicker-option-list")
        try:
            cols.first.wait_for(state="visible", timeout=5000)
        except Exception:
            pass
        for idx, kind, val in ((0, "hour", f"{dt.hour:02d}"), (1, "minute", f"{dt.minute:02d}")):
            opt = (cols.nth(idx).locator(".tiktok-timepicker-option-item")
                   .filter(has_text=re.compile(rf"^\s*{val}\s*$")) if cols.count() > idx else None)
            if opt is not None and opt.count():
                opt.first.scroll_into_view_if_needed()
                opt.first.click()
            elif not page.evaluate(PICK_JS, [kind, val]):
                raise TikTokError(f"không thấy {'giờ' if kind == 'hour' else 'phút'} {val} trong bảng chọn giờ")
            _sleep(0.4, 0.8)
        if cols.count() and cols.first.is_visible():
            page.keyboard.press("Escape")
            _sleep(0.3, 0.6)
    _sleep()
    t, d = _read_schedule(page)
    got_t, got_d = (t or {}).get("v", ""), (d or {}).get("v", "")
    if got_t != want_t or not _date_ok(got_d, dt):
        raise TikTokError(f"đặt giờ chưa khớp: đang là «{got_d} {got_t}», cần «{dt:%Y-%m-%d} {want_t}»")
    return True


def set_schedule(page, dt: datetime):
    """Chọn 'Lên lịch' rồi đặt ngày + giờ. TikTok có 2 kiểu giao diện (tuỳ tài khoản), tool tự nhận ra."""
    if dt.minute % 5:  # bảng chọn phút của TikTok đi theo bước 5 phút
        dt += timedelta(minutes=5 - dt.minute % 5)
    clear_popups(page)
    lab = _visible(page.get_by_text(_rx(r"^(Lên lịch|Schedule)$")), 5)
    if not lab:
        raise TikTokError("không thấy lựa chọn 'Lên lịch'")
    lab.scroll_into_view_if_needed()
    lab.click()
    _sleep(1.2, 2)
    click_button(page, r"^(Cho phép|Allow|Đồng ý|Agree|OK|Tiếp tục|Continue)$", timeout=2)
    tcb = page.locator('[role=combobox][aria-label="Select time"]').first
    dcb = page.locator('[role=combobox][aria-label="Select date"]').first
    end = time.time() + 10
    while True:
        if tcb.count() and tcb.is_visible():
            ok = _schedule_combo(page, dt, tcb, dcb)
            _sched_error(page)
            return ok
        t, d = _read_schedule(page)
        if t and d:
            ok = _schedule_inputs(page, dt, t, d)
            _sched_error(page)
            return ok
        if time.time() > end:
            raise TikTokError("bấm Lên lịch rồi nhưng không thấy ô ngày/giờ")
        time.sleep(0.5)


def _schedule_combo(page, dt, tcb, dcb):
    """Giao diện kiểu combobox (Select date / Select time) — kênh Kỹ Thuật Nông Nghiệp."""
    want_d = f"{dt.day} tháng {dt.month}, {dt.year}"
    want_t = f"{dt.hour:02d}:{dt.minute:02d}"
    # Ngày
    if want_d not in dcb.inner_text():
        dcb.click()
        _sleep()
        for _ in range(3):
            day = page.locator(f'button.DatePicker__day[data-outside="false"]'
                               f'[aria-label$="ngày {dt.day} tháng {dt.month} năm {dt.year}"]')
            if day.count():
                if day.first.get_attribute("data-disabled") == "true":
                    raise TikTokError(f"TikTok không cho chọn ngày {dt:%d/%m/%Y} (đã qua hoặc quá xa)")
                day.first.click()
                break
            nxt = page.locator('button[aria-label="Next month"]').first
            if not nxt.count():
                break
            nxt.click()
            _sleep(0.5, 0.9)
        _sleep()
        if page.locator(".DatePicker__panel").first.is_visible():
            page.keyboard.press("Escape")
    # Giờ
    if tcb.inner_text().strip() != want_t:
        tcb.click()
        _sleep()
        for kind, val in (("Hours", f"{dt.hour:02d}"), ("Minutes", f"{dt.minute:02d}")):
            opt = page.locator(f'button[role=option][aria-label="{kind} {val}"]').first
            if not opt.count():
                raise TikTokError(f"không thấy {kind} {val} trong bảng chọn giờ")
            opt.click()
            _sleep(0.4, 0.8)
        if page.locator(".TimePicker__panel").first.is_visible():
            page.keyboard.press("Escape")
    _sleep()
    got_d, got_t = dcb.inner_text().strip(), tcb.inner_text().strip()
    if want_d not in got_d or got_t != want_t:
        raise TikTokError(f"đặt giờ chưa khớp: đang là «{got_d} {got_t}», cần «{want_d} {want_t}»")
    return True


# =============================== Đăng 1 video ===============================
def post(job, settings, log=print, lock=None):
    """Trả về (status, ghi_chú). status: scheduled | done | check"""
    global SPEED
    SPEED = 0.5 if settings.get("tt_fast", True) else 1.0
    from playwright.sync_api import sync_playwright
    from .caption import parse_tags

    video = job.get("_upload_path") or job["video_path"]
    if not Path(video).exists():
        raise TikTokError(f"Không tìm thấy file video: {video}")
    headless = bool(settings.get("tt_headless"))
    interactive = settings.get("tt_ask_on_fail", True) and not headless
    notes = []
    when = datetime.strptime(job["scheduled_at"], "%Y-%m-%d %H:%M") if job.get("scheduled_at") else None
    use_schedule = bool(when and (when - datetime.now()).total_seconds() > 20 * 60)
    if use_schedule and job.get("visibility") == "private":
        use_schedule = False  # TikTok khoá Lên lịch với video "Chỉ mình bạn"
        notes.append("video riêng tư nên đăng ngay (TikTok không cho hẹn giờ)")

    with sync_playwright() as p:
        ctx = launch(p, settings, job["channel"], headless)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_default_timeout(30000)

        def step(name, fn, manual, critical=False):
            try:
                if fn() is False:
                    raise TikTokError("không thành công")
                return True
            except (NeedLogin, BrowserBusy):
                raise
            except Exception as e:
                shot = dump_debug(page, name)
                log(f"  ! Bước «{name}» lỗi: {str(e)[:200]}")
                if interactive:
                    ask_user(page, f"⚠️ Tool chưa tự làm được bước «{name}». {manual} Làm xong bấm nút vàng →",
                             lock=lock)
                    notes.append(f"{name}: làm tay")
                    return True
                if critical:
                    raise TikTokError(f"{name}: {e} (ảnh lỗi: {Path(shot).name})")
                notes.append(f"Bỏ qua {name}")
                return False

        try:
            log("  - Mở TikTok Studio, kiểm tra đăng nhập...")
            open_upload(page, settings, job["channel"], log)
            log("  - Tải video lên...")
            upload_file(page, video)
            wait_uploaded(page, lock=lock)
            log("  - Gõ mô tả + hashtag...")
            step("Mô tả", lambda: type_caption(page, job.get("caption", ""), parse_tags(job.get("hashtags", ""))),
                 "Bác gõ/dán mô tả giúp.")
            if job.get("cover_path"):
                log("  - Đặt ảnh bìa...")
                step("Ảnh bìa", lambda: set_cover_checked(page, job["cover_path"], log),
                     f"Bác bấm 'Sửa ảnh bìa' → Tải lên → chọn file {job['cover_path']}.", critical=True)
            for pr in job.get("products") or []:
                log(f"  - Gắn sản phẩm …{str(pr['id'])[-6:]}...")
                step("Gắn sản phẩm", lambda pr=pr: add_product(page, pr, job.get("cart_name", ""), log),
                     f"Bác gắn giúp sản phẩm ID {pr['id']} ({pr.get('name', '')[:40]}), tên giỏ: "
                     f"«{job.get('cart_name', '')}».", critical=True)
            if job.get("products"):
                _close_product_modal(page)  # hộp sản phẩm còn sót (kể cả sau khi làm tay) -> đóng lại
            mm, mref = job.get("music_mode") or "none", job.get("music_ref") or ""
            if mm in ("tiktok", "auto") and mref:
                from .video_utils import has_audio, probe
                keep = job.get("keep_audio") is None or int(job.get("keep_audio")) == 1
                # đã tắt âm gốc -> nhạc to bình thường; còn giọng nói -> hạ nhạc xuống làm nền
                vol = float(settings.get("tt_music_db", -14)) if keep and has_audio(video) else 0.0
                try:
                    if mm == "auto" and mref == "favitem":  # chưa gán bài cụ thể -> chọn lúc đăng
                        from .sounds import pick_for, ref_of
                        f = pick_for(job["channel"], job.get("item_key") or "")
                        mm, mref = ("tiktok", ref_of(f)) if f else ("auto", "smart")
                    if mm == "tiktok":
                        from .sounds import parse_ref
                        log(f"  - Chọn âm thanh Yêu thích «{parse_ref(mref)[1]}»...")
                        got = set_sound(page, mref, vol, log)
                    else:
                        log(f"  - Tự chọn nhạc TikTok ({AUTO_MUSIC.get(mref, mref)})...")
                        got = set_sound_auto(page, mref, bool(job.get("products")),
                                             probe(video).get("duration") or 0, vol, log)
                    notes.append(f"nhạc: {got}")
                except (NeedLogin, BrowserBusy):
                    raise
                except Exception as e:
                    dump_debug(page, "am_thanh")
                    if keep:
                        log(f"  ! Chưa thêm được nhạc ({str(e)[:150]}) → đăng không nhạc")
                        notes.append("không thêm được nhạc")
                    elif interactive:  # đã tắt âm gốc mà không có âm thanh -> không được đăng video câm
                        log(f"  ! Chưa thêm được âm thanh ({str(e)[:150]}) mà video đã tắt âm gốc → nhờ bác làm tay")
                        ask_user(page, "⚠️ Chưa thêm được âm thanh mà video đã TẮT ÂM GỐC (sẽ thành video câm). Bác bấm "
                                       "'Âm thanh' chọn giúp 1 bài rồi Lưu, xong bấm nút vàng →", lock=lock)
                        notes.append("âm thanh: làm tay")
                    else:
                        raise TikTokError(f"không thêm được âm thanh ({str(e)[:120]}) mà video đã tắt âm gốc "
                                          f"→ không đăng để tránh video câm")
            log("  - Chế độ người xem...")
            step("Người xem", lambda: set_visibility(page, job.get("visibility", "public")),
                 "Bác chọn giúp ô 'Người có thể nhìn thấy bài đăng này'.", critical=job.get("visibility") == "private")
            if int(job.get("ai_content") or 0) or (job.get("disclosure") or "none") != "none":
                log("  - Khai báo nội dung...")
                step("Khai báo nội dung", lambda: set_disclosure(page, int(job.get("ai_content") or 0),
                                                                  job.get("disclosure") or "none"),
                     "Bác bấm 'Hiển thị thêm' và bật nhãn AI / tiết lộ nội dung giúp.")
            if use_schedule:
                log(f"  - Hẹn giờ {when:%d/%m %H:%M}...")
                step("Hẹn giờ", lambda: set_schedule(page, when),
                     f"Bác chọn 'Lên lịch' và đặt ngày {when:%d/%m/%Y} giờ {when:%H:%M}.", critical=True)

            wait_uploaded(page, minutes=10, lock=lock)
            if settings.get("tt_confirm_before_post", False) and not headless:
                ask_user(page, "👀 Bác xem lại mô tả, ảnh bìa, giỏ hàng, nhạc, giờ hẹn. Ổn thì bấm nút vàng, tool sẽ bấm "
                               + ("LÊN LỊCH." if use_schedule else "ĐĂNG."), "🚀 ĐĂNG LUÔN", lock=lock)
            clear_popups(page)
            btn = post_button(page)
            if btn and _ready(btn):
                log("  - Bấm " + ("Lên lịch" if use_schedule else "Đăng") + "...")
                btn.scroll_into_view_if_needed()
                _sleep()
                btn.click()
            click_button(page, r"^(Đăng ngay|Post now|Tiếp tục|Continue|Tiếp tục đăng|Lên lịch|Schedule)$", timeout=6)
            ok_text = page.get_by_text(_rx(r"(đã được (tải lên|đăng|lên lịch)|Đã lên lịch|Quản lý bài đăng|"
                                           r"uploaded|scheduled|Manage (your )?posts)"))
            end = time.time() + 120
            while time.time() < end:
                if "/tiktokstudio/upload" not in page.url or _visible(ok_text):
                    st = "scheduled" if use_schedule else "done"
                    msg = (f"Đã hẹn giờ trên TikTok lúc {when:%d/%m %H:%M}" if use_schedule else "Đăng thành công")
                    return st, msg + (f" ({'; '.join(notes)})" if notes else "")
                time.sleep(2)
            shot = dump_debug(page, "xac_nhan")
            return "check", f"Đã bấm đăng nhưng chưa thấy TikTok xác nhận. Ảnh: {Path(shot).name}"
        except Exception:
            dump_debug(page, f"loi_job{job.get('id')}")
            raise
        finally:
            ctx.close()


# =============================== Các việc phụ ===============================
def login(settings, channel):
    from playwright.sync_api import sync_playwright
    with ProfileLock(channel) as lock, sync_playwright() as p:
        ctx = launch(p, settings, channel)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(LOGIN_URL)
            ask_user(page, f"Đăng nhập TikTok cho kênh «{channel}» (nhanh nhất: quét mã QR bằng app TikTok). "
                           f"Đăng nhập xong bấm nút vàng →", "✅ ĐĂNG NHẬP XONG", timeout_min=30, lock=lock)
            page.goto(UPLOAD_URL)
            time.sleep(4)
            if "login" in page.url:
                return False, "Chưa đăng nhập được"
            return True, detect_handle(page)
        finally:
            ctx.close()


SHOWCASE_JS = r"""
() => {
  const out = [];
  const leaves = Array.from(document.querySelectorAll('div,span,td,p')).filter(e =>
      e.children.length === 0 && /^\d{15,22}$/.test((e.textContent || '').trim()));
  for (const el of leaves) {
    let row = el;
    for (let i = 0; i < 10 && row; i++) { row = row.parentElement;
      if (row && row.querySelector('input[type=radio],[role=radio]')) break; }
    if (!row) continue;
    const img = row.querySelector('img');
    const lines = row.innerText.split('\n').map(s => s.trim()).filter(Boolean);
    out.push({id: el.textContent.trim(), lines, image: img ? img.src : ''});
  }
  return out;
}
"""


def _parse_rows(rows):
    res = []
    for r in rows:
        lines = [l for l in r["lines"] if l != r["id"]]
        price = next((l for l in lines if re.search(r"[₫đ]$|^\d[\d.,]*\s*[₫đ]", l)), "")
        stock = next((l for l in lines if re.fullmatch(r"\d+", l)), "")
        status = next((l for l in lines if re.search(r"(hoạt động|Active|Hết hàng|Ngừng)", l, re.I)), "")
        name = max([l for l in lines if l not in (price, stock, status)], key=len, default="")
        res.append({"id": r["id"], "name": name, "price": price, "stock": stock, "status": status,
                    "image": r["image"]})
    return res


def sync_showcase(settings, channel, log=print):
    """Đọc toàn bộ Trưng bày sản phẩm của kênh (mở trang đăng bằng video đen, không đăng)."""
    from playwright.sync_api import sync_playwright
    from .video_utils import make_blank_video
    from .products import save_showcase
    blank = make_blank_video(str(WORK_DIR / "blank.mp4"))
    with ProfileLock(channel) as lock, sync_playwright() as p:
        ctx = launch(p, settings, channel, bool(settings.get("tt_headless")))
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            open_upload(page, settings, channel, log)
            upload_file(page, blank)
            wait_uploaded(page, lock=lock)
            _open_add_link(page)
            modal = top_modal(page)
            found, k = {}, 1
            while True:
                rows = _parse_rows(page.evaluate(SHOWCASE_JS))
                new = [r for r in rows if r["id"] not in found]
                for r in rows:
                    found[r["id"]] = r
                log(f"  - Trang {k}: {len(rows)} sản phẩm (mới {len(new)})")
                lock.touch()
                k += 1
                if not _goto_page(modal, k):
                    break
            products = list(found.values())
            img_dir = SHOWCASE_DIR / slug(channel)
            img_dir.mkdir(parents=True, exist_ok=True)
            for pr in products:  # tải ảnh sản phẩm để AI so sánh
                if pr.get("image", "").startswith("http"):
                    try:
                        r = ctx.request.get(pr["image"], timeout=20000)
                        if r.ok:
                            (img_dir / f"{pr['id']}.jpg").write_bytes(r.body())
                    except Exception:
                        pass
            save_showcase(channel, products)
            click_button(top_modal(page), r"^(Hủy|Cancel)$", timeout=3)
            return products
        except Exception:
            dump_debug(page, "dong_bo_trung_bay")
            raise
        finally:
            try:
                page.goto("about:blank")
            except Exception:
                pass
            ctx.close()


SOUND_DETAIL_JS = r"""async (mid) => { try {
  const r = await fetch('https://www.tiktok.com/api/music/detail/?aid=1988&app_language=vi-VN&language=vi-VN&region=VN&musicId='
                        + mid, {credentials: 'include'});
  return await r.text(); } catch (e) { return ''; } }"""


_LAST_DETAIL = {"text": ""}


def _sound_play_url(page, mid) -> str:
    """Link file nhạc của 1 âm thanh theo mã số (lấy từ máy chủ TikTok)."""
    import json as _json
    raw = page.evaluate(SOUND_DETAIL_JS, str(mid)) or ""
    _LAST_DETAIL["text"] = raw[:300]
    m = re.search(r'"playUrl"\s*:\s*("(?:[^"\\]|\\.)*")', raw)
    return _json.loads(m.group(1)) if m else ""


def _load_all_favorites(page):
    """Danh sách Yêu thích đầy đủ (cuộn xuống cuối để TikTok tải thêm)."""
    rows = _sound_list(page, "favorites")
    for _ in range(20):
        if not rows:
            break
        page.locator(f'[data-sx-row="{rows[-1]["i"]}"]').scroll_into_view_if_needed()
        time.sleep(1.2)
        more = page.evaluate(SOUND_ITEMS_JS, SOUND_PANELS["favorites"])
        if len(more) <= len(rows):
            break
        rows = more
    return rows


def sync_sounds(settings, channel, log=print):
    """Đọc danh sách âm thanh Yêu thích + tải trọn bài để nghe thử. Giữ nguyên sản phẩm đã gắn trước đó."""
    from playwright.sync_api import sync_playwright
    from .video_utils import make_blank_video
    from . import sounds as snd
    blank = make_blank_video(str(WORK_DIR / "blank.mp4"))
    out_dir = SOUNDS_DIR / slug(channel)
    out_dir.mkdir(parents=True, exist_ok=True)
    old = {(f.get("id") or f.get("title")): f for f in snd.load_favs(channel)}
    with ProfileLock(channel) as lock, sync_playwright() as p:
        ctx = launch(p, settings, channel, bool(settings.get("tt_headless")))
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            open_upload(page, settings, channel, log)
            upload_file(page, blank)
            wait_uploaded(page, lock=lock)
            _open_sound_editor(page)
            rows = _load_all_favorites(page)
            if not rows and _visible(page.get_by_text(_rx(r"(Không có kết quả|No results)")), 3):
                raise TikTokError("mục Yêu thích của kênh này đang TRỐNG. Bác mở app TikTok, bấm lưu (Yêu thích) "
                                  "các âm thanh hay dùng, rồi bấm Đồng bộ lại.")
            if not rows:
                dump_debug(page, "am_thanh_yeu_thich")
                raise TikTokError("không đọc được danh sách Yêu thích (đã lưu ảnh + HTML vào data/logs/debug)")
            log(f"  - Có {len(rows)} âm thanh Yêu thích, đang tải file nghe thử...")
            _close_sound_editor(page)
            # hỏi link nhạc từ trang web chính của TikTok (từ trang Studio máy chủ không trả link)
            page.goto("https://www.tiktok.com/music/a-" + str(rows[0]["id"]), wait_until="domcontentloaded",
                      timeout=60000)
            time.sleep(3)
            warned = False
            result = []
            for r in rows:
                item = dict(old.get(r["id"]) or {})
                item.update(id=r["id"], title=r["title"], artist=r["artist"], duration=r["duration"])
                f = out_dir / f"{r['id']}.mp3"
                if not (f.exists() and f.stat().st_size > 1000):
                    try:
                        url = _sound_play_url(page, r["id"])
                        if not url and not warned:
                            warned = True
                            log(f"    (máy chủ TikTok không trả link nhạc: {_LAST_DETAIL['text'][:160]})")
                        if url:
                            resp = ctx.request.get(url, timeout=60000)
                            if resp.ok:
                                f.write_bytes(resp.body())
                    except Exception as e:
                        log(f"    (không tải được file nghe thử: {str(e)[:80]})")
                item["file"] = str(f) if f.exists() and f.stat().st_size > 1000 else ""
                result.append(item)
                lock.touch()
                log(f"  - {r['title']} · {r['artist']} {r['duration']} {'🔊' if item['file'] else '(chưa tải được)'}")
            snd.save_favs(channel, result)
            return result
        except Exception:
            dump_debug(page, "dong_bo_am_thanh")
            raise
        finally:
            try:
                page.goto("about:blank")
            except Exception:
                pass
            ctx.close()


def inspect_ui(settings, channel, log=print):
    """Lưu ảnh + HTML từng màn hình TikTok Studio để người hỗ trợ dò lại khi TikTok đổi giao diện."""
    from playwright.sync_api import sync_playwright
    from .video_utils import make_blank_video
    blank = make_blank_video(str(WORK_DIR / "blank.mp4"))
    shots = []
    with ProfileLock(channel) as lock, sync_playwright() as p:
        ctx = launch(p, settings, channel, False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            open_upload(page, settings, channel, log)
            shots.append(dump_debug(page, "1_trang_dang"))
            upload_file(page, blank)
            wait_uploaded(page, lock=lock)
            shots.append(dump_debug(page, "2_da_tai_len"))
            for name, fn in [("3_them_lien_ket", lambda: _open_add_link(page)),
                             ("4_anh_bia", lambda: (page.keyboard.press("Escape"), click_text(page, r"^(Sửa ảnh bìa|Edit cover)$", 4))),
                             ("5_am_thanh", lambda: (page.keyboard.press("Escape"), _open_sound_editor(page))),
                             ("6_len_lich", lambda: (page.keyboard.press("Escape"),
                                                     click_text(page, r"^(Lên lịch|Schedule)$", 4)))]:
                try:
                    fn()
                    _sleep(1.5, 2.5)
                except Exception as e:
                    log(f"  ! {name}: {e}")
                shots.append(dump_debug(page, name))
                for _ in range(2):
                    click_button(top_modal(page), r"^(Hủy|Cancel|Đóng|Close)$", timeout=1)
            return shots
        finally:
            try:
                page.goto("about:blank")
            except Exception:
                pass
            ctx.close()


# =============================== Kiểm tra ảnh bìa bài đã hẹn giờ ===============================
def verify_covers(settings, channel, jobs, log=print) -> dict:
    """Mở TikTok Studio > Bài đăng, tìm bài hẹn giờ của từng video (theo giờ hẹn), tải ảnh bìa TikTok đang giữ
    và so với ảnh bìa của video. Trả về {job_id: ("ok"|"thieu_bia"|"da_xoa"|"chua_ro", điểm)}.
    'da_xoa' chỉ khi đã đọc hết danh sách bài tới trước lúc đăng video đó mà vẫn không thấy."""
    from playwright.sync_api import sync_playwright
    items = {}

    def on_resp(r):
        try:
            if "item_list" in r.url:
                for it in (r.json().get("item_list") or []):
                    items[it["item_id"]] = it
        except Exception:
            pass

    oldest_post = min(datetime.strptime(j["updated_at"], "%Y-%m-%d %H:%M") for j in jobs) - timedelta(hours=1)
    out = {}
    with ProfileLock(channel) as lock, sync_playwright() as p:
        ctx = launch(p, settings, channel, True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.on("response", on_resp)
        try:
            page.goto("https://www.tiktok.com/tiktokstudio/content", wait_until="domcontentloaded", timeout=60000)
            if "login" in page.url:
                raise NeedLogin(f"Kênh «{channel}» cần đăng nhập lại")
            for _ in range(15):  # chờ danh sách bài tải về (máy bận có thể chậm)
                if items:
                    break
                time.sleep(2)
            clear_popups(page)
            covered, last_n, same = False, -1, 0
            for _ in range(40):  # cuộn tới khi gặp bài tạo trước lúc đăng video cũ nhất (hoặc hết danh sách)
                lock.touch()
                times = [int(it.get("create_time") or 0) for it in items.values()]
                if times and min(times) < oldest_post.timestamp():
                    covered = True
                    break
                same = same + 1 if len(items) == last_n else 0
                if same >= 2:  # cuộn 2 lần không thêm bài nào -> hết danh sách
                    covered = bool(items)
                    break
                last_n = len(items)
                page.mouse.wheel(0, 5000)
                _sleep(2.5, 3.5)
            log(f"  (đọc được {len(items)} bài trên TikTok Studio)")
            by_t = {}
            for it in items.values():
                if int(it.get("schedule_time") or 0):
                    by_t[datetime.fromtimestamp(int(it["schedule_time"])).strftime("%Y-%m-%d %H:%M")] = it
            def _key(t):
                return re.sub(r"\W+", "", norm(t or ""))[:30]
            by_desc = {}
            for it in items.values():
                by_desc.setdefault(_key(it.get("desc")), []).append(it)
            for j in jobs:
                it = by_t.get(j["scheduled_at"])
                if not it and len(_key(j.get("caption"))) >= 12:  # giờ hẹn trên TikTok khác -> tìm theo mô tả
                    same = by_desc.get(_key(j.get("caption"))) or []
                    if same:
                        it = same[0]
                        st_ = int(it.get("schedule_time") or 0)
                        j["_tiktok_time"] = datetime.fromtimestamp(st_).strftime("%Y-%m-%d %H:%M") if st_ else ""
                if not it:
                    out[j["id"]] = ("da_xoa" if covered else "chua_ro", -1)
                    continue
                if not j.get("cover_path") or not Path(j["cover_path"]).exists():
                    out[j["id"]] = ("ok", -1, j.get("_tiktok_time"))
                    continue
                try:
                    body = ctx.request.get((it.get("cover_url") or [""])[0], timeout=30000).body()
                    sc = image_similarity(body, j["cover_path"])
                except Exception:
                    out[j["id"]] = ("chua_ro", -1)
                    continue
                out[j["id"]] = ("ok" if sc >= 80 else "thieu_bia", sc, j.get("_tiktok_time"))
            return out
        finally:
            try:
                page.goto("about:blank")
            except Exception:
                pass
            ctx.close()
