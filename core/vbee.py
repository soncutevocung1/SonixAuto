"""Giọng Vbee (trả phí) cho Sonix Edit Video.

Cần trong Cài đặt: vbee_app_id, vbee_token (studio.vbee.vn > Tích hợp API > Tạo ứng dụng), vbee_voice.
Cách gọi: gửi chữ -> Vbee trả request_id -> hỏi lại tới khi xong -> tải file mp3.
Đã kiểm tra 12/11/2026: /api/v1/tts và /api/v1/tts/<id> có thật (báo 401 khi thiếu token, lỗi dạng
{"status":0,"error_code":..,"error_message":..}); /api/v1/voices xem công khai (472 giọng).
Đã chạy thật 12/11/2026 với token thật: POST trả status IN_PROGRESS + request_id, hỏi lại ra audio_link,
kịch bản Đạm cá (~800 ký tự) ra mp3 39 giây.
"""
import time
from pathlib import Path

import requests

API = "https://vbee.vn/api/v1/tts"
VOICES_API = "https://vbee.vn/api/v1/voices"
DEFAULT_VOICE = "hn_female_ngochuyen_full_24k-st"  # Ngọc Huyền 2.0 (anh Sơn hay dùng)
DEFAULT_SPEED = 1.05
# Ưu tiên đứng đầu danh sách chọn; còn lại lấy từ danh_sach_giong().
# "Tuấn Anh quảng cáo" không có trong danh sách công khai /api/v1/voices -> cần mã giọng từ studio để thêm.
VOICES = {
    "hn_female_ngochuyen_full_24k-st": "Ngọc Huyền 2.0",
    "hn_female_ngochuyen_full_48k-fhg": "HN - Ngọc Huyền",
    "hn_female_ngochuyen_full_24k-stl": "Ngọc Huyền nâng cao (Beta)",
}
# Độ nhấn nhá: API v1 KHÔNG có tham số này (đã thử emphasis/emphasis_rate/emotion... đều bị từ chối 12/11/2026).
MAX_CHARS = 2000


def danh_sach_giong() -> dict:
    """{mã giọng: 'Tên · loại'} các giọng tiếng Việt đang bật trên Vbee."""
    try:
        r = requests.get(VOICES_API, params={"limit": 600}, timeout=30).json()
        return {v["code"]: f"{v['name']} · {v.get('level', '')}" for v in r["result"]["voices"]
                if str(v.get("language_code", "")).startswith("vi") and v.get("active")}
    except Exception:
        return dict(VOICES)


KEY_FILE = Path(__file__).resolve().parent.parent / "data" / "vbee_key.txt"


def keys(settings: dict) -> tuple:
    """App ID + token: lấy trong Cài đặt; chưa có thì đọc data/vbee_key.txt (dòng APP_ID= và TOKEN=)."""
    app_id = (settings.get("vbee_app_id") or "").strip()
    token = (settings.get("vbee_token") or "").strip()
    if (not app_id or not token) and KEY_FILE.exists():
        for ln in KEY_FILE.read_text(encoding="utf-8-sig").splitlines():
            k, _, v = ln.partition("=")
            if k.strip().upper() == "APP_ID" and v.strip():
                app_id = app_id or v.strip()
            if k.strip().upper() == "TOKEN" and v.strip():
                token = token or v.strip()
    return app_id, token


class VbeeError(Exception):
    pass


def _headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def tao_giong(text: str, out: str, app_id: str, token: str, voice: str = DEFAULT_VOICE, speed: float = DEFAULT_SPEED,
              timeout: int = 300) -> str:
    if not app_id or not token:
        raise VbeeError("Chưa nhập App ID / Token Vbee trong Cài đặt")
    if len(text) > MAX_CHARS:
        raise VbeeError(f"Lời quá dài cho 1 lần gọi Vbee ({len(text)} > {MAX_CHARS} ký tự)")
    body = {"app_id": app_id, "response_type": "indirect", "callback_url": "https://example.com/sonix",
            "input_text": text, "voice_code": voice or DEFAULT_VOICE, "audio_type": "mp3", "bitrate": 128,
            "speed_rate": f"{speed:.2f}".rstrip("0").rstrip(".")}
    r = requests.post(API, json=body, headers=_headers(token), timeout=60)
    if r.status_code in (401, 403):
        raise VbeeError("Token Vbee sai hoặc hết hạn")
    js = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if r.status_code != 200 or js.get("status") == 0:
        raise VbeeError(f"Vbee báo lỗi {r.status_code}: {js.get('error_message') or r.text[:200]}")
    res = js.get("result") or {}
    rid = res.get("request_id")
    if not rid:
        raise VbeeError(f"Vbee không trả request_id: {r.text[:200]}")

    link, t0 = None, time.time()
    while time.time() - t0 < timeout:
        time.sleep(2)
        s = requests.get(f"{API}/{rid}", headers=_headers(token), timeout=30)
        if s.status_code != 200:
            continue
        sr = (s.json() or {}).get("result") or {}
        st = str(sr.get("status", "")).upper()
        if st == "SUCCESS" and sr.get("audio_link"):
            link = sr["audio_link"]
            break
        if st in ("FAILURE", "FAILED", "ERROR"):
            raise VbeeError(f"Vbee tạo giọng lỗi: {sr}")
    if not link:
        raise VbeeError("Vbee tạo giọng quá lâu, thử lại sau")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    a = requests.get(link, timeout=120)
    a.raise_for_status()
    Path(out).write_bytes(a.content)
    return out
