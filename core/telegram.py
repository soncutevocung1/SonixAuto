"""Thông báo về Telegram (Sonix Up Video + Sonix Edit Video).

- 1 bot Telegram (Admin tạo bằng @BotFather). Mã bot KHÔNG nằm trong mã nguồn (kho GitHub công khai):
  Admin nhập ở Cài đặt, rồi tạo "Mã kết nối Sonix" gửi riêng cho người dùng khác.
- Mỗi người nhận tự liên kết Telegram của mình: app hiện 1 mã ngắn, bấm link mở bot, bấm Start là xong.
- Loại tin: su_co (sự cố), xong (đã làm xong), cap_nhat (có bản cập nhật). Nhãn: [Sonix Up Video] / [Sonix Edit Video].
- Tin gồm văn bản ngắn + ảnh chụp lỗi + video quay màn hình (nếu có).
- Gửi trong luồng riêng, lỗi mạng không làm hỏng việc đang chạy. Không bao giờ in mã bot ra nhật ký.
"""
import base64
import json
import random
import re
import socket
import string
import threading
import time
from pathlib import Path

from .config import DATA_DIR, load_settings

API = "https://api.telegram.org"
APPS = {"up": "Sonix Up Video", "edit": "Sonix Edit Video"}
KINDS = {"su_co": "SỰ CỐ", "xong": "ĐÃ XONG", "cap_nhat": "CÓ BẢN CẬP NHẬT", "bao_loi": "Sự cố người dùng"}
STATE = DATA_DIR / "telegram_state.json"
MAX_FILE = 49 * 1024 * 1024  # Telegram bot gửi tối đa 50 MB/tệp


class TgError(Exception):
    pass


def _safe(text) -> str:
    """Che mã bot nếu lỡ có trong thông báo lỗi."""
    return re.sub(r"bot\d+:[\w-]+", "bot***", str(text))


def _token(settings=None) -> str:
    return ((settings or load_settings()).get("tg_bot") or "").strip()


def ready(settings=None) -> bool:
    return bool(_token(settings))


def _call(token, method, data=None, files=None, timeout=60):
    import requests
    if not token:
        raise TgError("Chưa có mã bot Telegram (Cài đặt → Thông báo Telegram)")
    try:
        r = requests.post(f"{API}/bot{token}/{method}", data=data or {}, files=files, timeout=timeout)
        js = r.json()
    except Exception as e:
        raise TgError(_safe(f"Không gửi được Telegram: {type(e).__name__}: {e}")[:300])
    if not js.get("ok"):
        raise TgError(_safe(f"Telegram báo lỗi: {js.get('description', r.status_code)}"))
    return js.get("result")


def bot_info(token) -> dict:
    return _call(token, "getMe", timeout=20)


# ------------------------------- mã kết nối (Admin → người dùng) -------------------------------
def make_share_code(settings) -> str:
    """Mã gửi riêng cho người dùng khác: gồm mã bot + nơi nhận báo lỗi của Admin. Đừng đăng công khai."""
    raw = json.dumps({"t": _token(settings), "a": str(settings.get("tg_admin_chat") or "")}, separators=(",", ":"))
    return "SONIX-" + base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def read_share_code(code: str) -> dict:
    code = (code or "").strip()
    if not code.startswith("SONIX-"):
        raise TgError("Mã kết nối phải bắt đầu bằng SONIX-")
    b = code[6:]
    try:
        js = json.loads(base64.urlsafe_b64decode(b + "=" * (-len(b) % 4)).decode())
    except Exception:
        raise TgError("Mã kết nối không đúng (chép thiếu?)")
    if not js.get("t"):
        raise TgError("Mã kết nối thiếu mã bot")
    return {"tg_bot": js["t"], "tg_admin_chat": js.get("a", ""), "tg_tu_ma": True}


# ------------------------------- liên kết Telegram người nhận -------------------------------
def new_link_code() -> str:
    return "sx" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


def link_url(settings, code) -> str:
    me = bot_info(_token(settings))
    return f"https://t.me/{me['username']}?start={code}"


def find_chat(settings, code):
    """Tìm người vừa bấm Start với mã này. Không xác nhận đã đọc tin (máy khác dùng chung bot vẫn đọc được).
    Trả về {"chat_id", "name"} hoặc None."""
    for u in _call(_token(settings), "getUpdates", {"timeout": 0, "allowed_updates": '["message"]'}, timeout=30) or []:
        m = u.get("message") or {}
        if (m.get("text") or "").strip() in (f"/start {code}", code):
            ch = m.get("chat") or {}
            name = " ".join(x for x in (ch.get("first_name"), ch.get("last_name")) if x) or ch.get("username") or ""
            return {"chat_id": str(ch.get("id")), "name": name or str(ch.get("id"))}
    return None


# ------------------------------- gửi -------------------------------
def _caption(app, kind, title, body) -> str:
    head = f"[{APPS.get(app, app)}] {KINDS.get(kind, kind)}"
    host = socket.gethostname()
    txt = f"<b>{_esc(head)}</b>\n<b>{_esc(title)}</b>\n{_esc(body)}\n<i>Máy {_esc(host)} · {time.strftime('%H:%M %d/%m/%Y')}</i>"
    return txt[:1020]


def _esc(s) -> str:
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def send_to(token, chat_id, app, kind, title, body="", photos=(), video=None, document=None, raw_caption=None):
    cap = raw_caption or _caption(app, kind, title, body)
    photos = [p for p in photos if p and Path(p).exists()][:5]
    if len(photos) > 1:
        media, files = [], {}
        for i, p in enumerate(photos):
            media.append({"type": "photo", "media": f"attach://p{i}", **({"caption": cap, "parse_mode": "HTML"} if i == 0 else {})})
            files[f"p{i}"] = open(p, "rb")
        try:
            _call(token, "sendMediaGroup", {"chat_id": chat_id, "media": json.dumps(media)}, files)
        finally:
            for f in files.values():
                f.close()
        cap = None
    elif photos:
        with open(photos[0], "rb") as f:
            _call(token, "sendPhoto", {"chat_id": chat_id, "caption": cap, "parse_mode": "HTML"}, {"photo": f})
        cap = None
    if video and Path(video).exists() and Path(video).stat().st_size < MAX_FILE:
        with open(video, "rb") as f:
            _call(token, "sendVideo", {"chat_id": chat_id, "caption": cap or "Video quay màn hình", "parse_mode": "HTML",
                                       "supports_streaming": "true"}, {"video": f}, timeout=300)
        cap = None
    if document and Path(document).exists() and Path(document).stat().st_size < MAX_FILE:
        with open(document, "rb") as f:
            _call(token, "sendDocument", {"chat_id": chat_id, "caption": cap or "Gói nhật ký", "parse_mode": "HTML"},
                  {"document": f}, timeout=300)
        cap = None
    if cap:
        _call(token, "sendMessage", {"chat_id": chat_id, "text": cap, "parse_mode": "HTML",
                                     "disable_web_page_preview": "true"})


def receivers(settings, app, kind) -> list:
    out = []
    for r in settings.get("tg_nguoi_nhan") or []:
        if r.get("chat_id") and r.get("on", True) and app in (r.get("apps") or list(APPS)) \
                and kind in (r.get("kinds") or ["su_co", "xong", "cap_nhat"]):
            out.append(r)
    return out


def _log(msg):
    try:
        from .config import LOG_DIR
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_DIR / "telegram.log", "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%d/%m %H:%M:%S')}  {_safe(msg)}\n")
    except Exception:
        pass


def notify(app, kind, title, body="", photos=(), video=None, document=None, settings=None, wait=False):
    """Gửi cho mọi người nhận đã bật loại tin này. Chạy ngầm (wait=False) để không làm chậm việc đang chạy."""
    try:
        settings = settings or load_settings()
    except Exception:
        return 0
    token, rs = _token(settings), receivers(settings, app, kind)
    if not token or not rs:
        return 0

    def run():
        vid = video
        if vid and str(vid).endswith(".webm"):
            vid = to_mp4(vid)
        for r in rs:
            try:
                send_to(token, r["chat_id"], app, kind, title, body, photos, vid, document)
                _log(f"Đã gửi «{title}» ({kind}) tới {r.get('name')}")
            except Exception as e:
                _log(f"Gửi «{title}» tới {r.get('name')} lỗi: {e}")
    if wait:
        run()
    else:
        threading.Thread(target=run, name="sonix-telegram", daemon=True).start()
    return len(rs)


# ------------------------------- chống gửi trùng -------------------------------
def _state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def once(key, every_sec=0) -> bool:
    """True nếu chưa gửi tin có khoá này (hoặc đã quá every_sec giây kể từ lần gửi trước)."""
    s = _state()
    last = s.get(key)
    if last and (not every_sec or time.time() - last < every_sec):
        return False
    s[key] = time.time()
    try:
        STATE.write_text(json.dumps(s), encoding="utf-8")
    except Exception:
        pass
    return True


# ------------------------------- ảnh chụp lỗi + video quay màn hình -------------------------------
def latest_shot(since: float):
    """Ảnh chụp lỗi mới nhất (data/logs/debug) chụp sau thời điểm `since`."""
    from .config import DEBUG_DIR
    try:
        shots = [p for p in DEBUG_DIR.glob("*.png") if p.stat().st_mtime >= since - 2]
        return str(max(shots, key=lambda p: p.stat().st_mtime)) if shots else None
    except Exception:
        return None


def rec_dir(job_id) -> Path:
    from .config import WORK_DIR
    return WORK_DIR / "quay_man_hinh" / str(job_id)


def want_record(settings, app="up") -> bool:
    """Quay màn hình lúc đăng (để gửi kèm khi có sự cố) khi đã bật và có người nhận tin sự cố."""
    return bool(settings.get("tg_quay", True)) and ready(settings) and bool(receivers(settings, app, "su_co"))


def recorded_video(job_id):
    d = rec_dir(job_id)
    vids = sorted(d.glob("*.webm"), key=lambda p: p.stat().st_mtime) if d.is_dir() else []
    return str(vids[-1]) if vids else None


def to_mp4(src) -> str:
    """webm (Playwright quay) -> mp4 nhỏ để Telegram phát được trên điện thoại. Lỗi thì trả lại file gốc."""
    import subprocess
    try:
        from .video_utils import _ffmpeg
        out = str(Path(src).with_suffix(".mp4"))
        subprocess.run([_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-vf",
                        "scale='min(960,iw)':-2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "30",
                        "-pix_fmt", "yuv420p", "-an", out], capture_output=True, timeout=300,
                       creationflags=0x08000000 if __import__("sys").platform == "win32" else 0)
        return out if Path(out).exists() and Path(out).stat().st_size > 0 else str(src)
    except Exception:
        return str(src)


def clean_records(max_age_h=24):
    import shutil
    from .config import WORK_DIR
    root = WORK_DIR / "quay_man_hinh"
    if not root.is_dir():
        return
    for d in root.iterdir():
        try:
            if time.time() - d.stat().st_mtime > max_age_h * 3600:
                shutil.rmtree(d, ignore_errors=True)
        except Exception:
            pass


# ------------------------------- đường gửi Báo lỗi về Admin -------------------------------
def is_admin(settings) -> bool:
    """Máy Admin: tự tạo bot (không phải nhận mã kết nối từ người khác)."""
    return bool(_token(settings)) and not settings.get("tg_tu_ma")


def _builtin():
    """Bot báo lỗi gắn sẵn trong app (chỉ gửi được về Telegram Admin). Không có thì trả None."""
    try:
        from .lien_ket_admin import B
        raw = bytes(x ^ 0x5A for x in base64.b64decode(B)).decode()
        js = json.loads(raw)
        return (js["t"], str(js["a"])) if js.get("t") and js.get("a") else None
    except Exception:
        return None


def admin_target(settings):
    """(mã bot, chat Admin) để gửi Báo lỗi. Người dùng KHÔNG cần có Telegram."""
    if is_admin(settings) and settings.get("tg_admin_chat"):
        return _token(settings), str(settings["tg_admin_chat"])
    b = _builtin()
    if b:
        return b
    if _token(settings) and settings.get("tg_admin_chat"):  # máy đã dán mã kết nối Admin gửi
        return _token(settings), str(settings["tg_admin_chat"])
    return None


def encode_builtin(token, chat) -> str:
    raw = json.dumps({"t": token, "a": str(chat)}, separators=(",", ":")).encode()
    return base64.b64encode(bytes(x ^ 0x5A for x in raw)).decode()
