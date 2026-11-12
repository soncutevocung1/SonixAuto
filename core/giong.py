"""Tạo giọng đọc cho Sonix Edit Video: Vbee (trả phí), ElevenLabs (sau này), miễn phí (Microsoft).

Đọc từng câu riêng rồi nối lại: biết được thời gian từng câu (để chọn cảnh khớp lời) và câu nào lỗi
mạng thì chỉ đọc lại câu đó.
"""
import asyncio
import re
import subprocess
import sys
import time
from pathlib import Path

from core.video_utils import _ffmpeg, probe

FREE_VOICES = {
    "vi-VN-HoaiMyNeural": "Hoài My (nữ, miền Bắc) · miễn phí",
    "vi-VN-NamMinhNeural": "Nam Minh (nam, miền Bắc) · miễn phí",
}
_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


class GiongError(Exception):
    pass


def tach_cau(text: str) -> list:
    parts = re.split(r"(?<=[.!?…])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _noi(files: list, out: str):
    lst = Path(out).with_suffix(".txt")
    lst.write_text("".join(f"file '{Path(f).as_posix()}'\n" for f in files), encoding="utf-8")
    subprocess.run([_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c:a", "libmp3lame", "-q:a", "2", out], check=True,
                   creationflags=_NO_WINDOW)
    lst.unlink(missing_ok=True)


def giong_mien_phi(text: str, out: str, voice: str = "vi-VN-HoaiMyNeural", rate: str = "+20%",
                   tries: int = 15) -> dict:
    """Giọng Microsoft miễn phí (cần mạng). rate '+20%' = đọc nhanh hơn 20%.
    Trả về {'path', 'duration', 'cau': [{'text','start','end'}...]}."""
    import edge_tts

    out_p = Path(out)
    tmp = out_p.parent / (out_p.stem + "_cau")
    tmp.mkdir(parents=True, exist_ok=True)
    cau = tach_cau(text)
    files = []

    async def one(t, f):
        await edge_tts.Communicate(t, voice, rate=rate).save(str(f))

    for i, t in enumerate(cau):
        f = tmp / f"{i:02d}.mp3"
        for k in range(tries):
            try:
                asyncio.run(one(t, f))
                if f.exists() and f.stat().st_size > 1000:
                    break
            except Exception:
                pass
            time.sleep(min(2.0 + k, 6.0))  # dịch vụ miễn phí hay từ chối ngẫu nhiên: chờ rồi thử lại
        else:
            raise GiongError(f"Không tạo được giọng cho câu {i + 1}: {t[:40]}…")
        files.append(f)

    _noi(files, str(out_p))
    timeline, pos = [], 0.0
    for t, f in zip(cau, files):
        d = probe(str(f))["duration"]
        timeline.append({"text": t, "start": round(pos, 3), "end": round(pos + d, 3)})
        pos += d
    for f in files:
        f.unlink(missing_ok=True)
    tmp.rmdir()
    return {"path": str(out_p), "duration": probe(str(out_p))["duration"], "cau": timeline}
