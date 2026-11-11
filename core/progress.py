"""Tiến độ đăng video đang chạy (bộ đăng ghi, tab Hàng chờ đọc 2 giây/lần)."""
import json
import re
import time

from .config import DATA_DIR

FILE = DATA_DIR / "tien_do.json"
TT_STEPS = [  # thứ tự các bước đăng TikTok (để tính % tiến độ)
    ("Chuẩn bị video", r"âm thanh gốc|Ghép nhạc"),
    ("Mở TikTok Studio", r"Mở TikTok Studio"),
    ("Tải video lên", r"Tải video lên"),
    ("Gõ mô tả + hashtag", r"Gõ mô tả"),
    ("Đặt ảnh bìa", r"Đặt ảnh bìa"),
    ("Gắn sản phẩm", r"Gắn sản phẩm"),
    ("Chọn nhạc", r"nhạc TikTok|âm thanh Yêu thích"),
    ("Chế độ người xem", r"Chế độ người xem"),
    ("Khai báo nội dung", r"Khai báo nội dung"),
    ("Hẹn giờ", r"Hẹn giờ \d"),
    ("Bấm Lên lịch / Đăng", r"Bấm (Lên lịch|Đăng)"),
]
FB_STEPS = [("Tải video lên Facebook", r"FACEBOOK"), ("Hẹn giờ trên Facebook", r"FB ")]
_S = {}


def _save():
    try:
        tmp = FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(_S, ensure_ascii=False), encoding="utf-8")
        tmp.replace(FILE)
    except Exception:
        pass


def on_log(msg: str):
    """Bộ đăng gọi với mỗi dòng nhật ký; tự nhận ra video bắt đầu / bước / kết thúc."""
    global _S
    try:
        m = re.match(r"▶ #(\d+) (TIKTOK|FACEBOOK) · (.+?) · (.+)$", msg)
        if m:
            _S = {"job": int(m.group(1)), "platform": m.group(2).lower(), "channel": m.group(3),
                  "file": m.group(4), "start": time.time(), "updated": time.time(), "step": "Bắt đầu",
                  "idx": 0, "total": len(TT_STEPS if m.group(2) == "TIKTOK" else FB_STEPS), "lines": [],
                  "state": "running"}
            _save()
            return
        if not _S or _S.get("state") != "running":
            return
        line = msg.strip()
        _S["lines"] = (_S.get("lines") or [])[-14:] + [time.strftime("%H:%M:%S ") + line]
        _S["updated"] = time.time()
        steps = TT_STEPS if _S["platform"] == "tiktok" else FB_STEPS
        if line.startswith("- "):
            for i, (name, rx) in enumerate(steps):
                if re.search(rx, line):
                    _S["idx"], _S["step"] = i + 1, name
                    break
            else:
                _S["step"] = line[2:].rstrip(".")
        elif line.startswith("✔") or line.startswith("✖") or line.startswith("⛔") or "Ảnh bìa chưa lên" in line:
            _S["state"] = "ok" if line.startswith("✔") else "fail"
            _S["result"] = line[1:].strip()[:200]
            _S["idx"] = _S["total"] if _S["state"] == "ok" else _S.get("idx", 0)
            _S["end"] = time.time()
        elif line.startswith("…") or line.startswith(". nghỉ"):
            _S["state"] = "rest"
        _save()
    except Exception:
        pass


def read() -> dict:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
