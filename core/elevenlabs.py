"""Giọng ElevenLabs (trả phí) cho Sonix Edit Video.

Mã: Cài đặt (eleven_key) hoặc data/elevenlabs_key.txt dòng API_KEY=  (elevenlabs.io > Developers > API Keys).
Tiếng Việt: dùng model eleven_v3 (tự nhiên nhất) hoặc eleven_flash_v2_5 (nhanh, rẻ hơn).
"""
from pathlib import Path

import requests

API = "https://api.elevenlabs.io/v1"
KEY_FILE = Path(__file__).resolve().parent.parent / "data" / "elevenlabs_key.txt"
MODELS = {
    "eleven_v3": "Eleven v3 · tự nhiên, nhiều cảm xúc nhất",
    "eleven_flash_v2_5": "Flash v2.5 · nhanh, rẻ (nửa giá)",
    "eleven_turbo_v2_5": "Turbo v2.5 · cân bằng",
}
DEFAULT_MODEL = "eleven_v3"


class ElevenError(Exception):
    pass


def key(S: dict) -> str:
    k = (S.get("eleven_key") or "").strip()
    if not k and KEY_FILE.exists():
        for ln in KEY_FILE.read_text(encoding="utf-8-sig").splitlines():
            a, _, b = ln.partition("=")
            if a.strip().upper() == "API_KEY" and b.strip():
                k = b.strip()
    return k


def _h(k):
    return {"xi-api-key": k, "Content-Type": "application/json"}


def _loi(r) -> str:
    try:
        d = r.json().get("detail")
        msg = d.get("message") if isinstance(d, dict) else d
    except Exception:
        msg = r.text[:200]
    if r.status_code == 401:
        return "Mã ElevenLabs sai hoặc thiếu quyền (cần quyền Text to Speech + Voices)"
    if r.status_code in (402, 429) or "quota" in str(msg).lower():
        return f"ElevenLabs hết lượt / quá nhiều yêu cầu: {msg}"
    return f"ElevenLabs báo lỗi {r.status_code}: {msg}"


def danh_sach_giong(k: str) -> dict:
    """{voice_id: 'Tên · loại'} các giọng trong tài khoản (kể cả giọng đã thêm từ thư viện / giọng nhái)."""
    r = requests.get(f"{API}/voices", headers=_h(k), timeout=30)
    if r.status_code != 200:
        raise ElevenError(_loi(r))
    return {v["voice_id"]: f"{v['name']} · {v.get('category', '')}" for v in r.json().get("voices", [])}


def tao_giong(text: str, out: str, k: str, voice_id: str, model: str = DEFAULT_MODEL, speed: float = 1.0,
              timeout: int = 180) -> str:
    if not k:
        raise ElevenError("Chưa có mã ElevenLabs")
    if not voice_id:
        raise ElevenError("Chưa chọn giọng ElevenLabs")
    body = {"text": text, "model_id": model or DEFAULT_MODEL, "language_code": "vi",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    if abs(float(speed) - 1.0) > 0.01:
        body["voice_settings"]["speed"] = max(0.7, min(1.2, float(speed)))
    r = requests.post(f"{API}/text-to-speech/{voice_id}", params={"output_format": "mp3_44100_128"},
                      headers=_h(k), json=body, timeout=timeout)
    if r.status_code == 400 and "language_code" in r.text:  # model không nhận mã ngôn ngữ -> gửi lại không có
        body.pop("language_code")
        r = requests.post(f"{API}/text-to-speech/{voice_id}", params={"output_format": "mp3_44100_128"},
                          headers=_h(k), json=body, timeout=timeout)
    if r.status_code != 200 or not r.headers.get("content-type", "").startswith("audio"):
        raise ElevenError(_loi(r))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_bytes(r.content)
    return out
