"""Quét kịch bản từ kênh TikTok tham khảo: lấy danh sách video, tải tiếng, chép lời (chạy trên máy)."""
import json
import subprocess
import sys
from pathlib import Path

from core.video_utils import _ffmpeg

_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
_MODEL = None


def danh_sach_video(url: str, n: int = 15) -> list:
    """URL kênh (https://www.tiktok.com/@ten) hoặc 1 video -> [{'id','url','title','views'}...] mới nhất."""
    import yt_dlp
    opts = {"quiet": True, "skip_download": True, "extract_flat": True, "playlistend": n}
    with yt_dlp.YoutubeDL(opts) as y:
        info = y.extract_info(url, download=False)
    entries = info.get("entries") or [info]
    out = []
    for e in entries[:n]:
        vid = e.get("id")
        u = e.get("url") or e.get("webpage_url") or url
        if vid and "/video/" not in u and "@" in url:
            u = url.rstrip("/").split("?")[0] + f"/video/{vid}"
        out.append({"id": vid, "url": u, "title": e.get("title") or e.get("description") or "",
                    "views": e.get("view_count")})
    return out


def tai_tieng(url: str, out_dir: Path) -> str:
    """Tải phần tiếng của 1 video về out_dir/<id>.m4a (đã có thì thôi)."""
    import yt_dlp
    out_dir.mkdir(parents=True, exist_ok=True)
    opts = {"quiet": True, "noprogress": True, "no_warnings": True,
            "format": "bestaudio/best", "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
            "ffmpeg_location": _ffmpeg()}
    with yt_dlp.YoutubeDL(opts) as y:
        info = y.extract_info(url, download=True)
        return y.prepare_filename(info)


def _model():
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel
        # Chạy CPU: card NVIDIA cần thêm thư viện CUDA (cublas), thiếu thì có lúc treo thay vì báo lỗi.
        _MODEL = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=4)
    return _MODEL


def chep_loi(path: str) -> str:
    """Nghe file âm thanh/video -> lời tiếng Việt."""
    import numpy as np
    raw = subprocess.run([_ffmpeg(), "-v", "error", "-i", str(path), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True, creationflags=_NO_WINDOW).stdout
    audio = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    segs, _ = _model().transcribe(audio, language="vi", vad_filter=False)
    return " ".join(s.text.strip() for s in segs).strip()


def luot_xem(s) -> float:
    """'101.6K' -> 101600."""
    s = str(s or "").strip().upper().replace(",", ".")
    mul = 1e6 if s.endswith("M") else 1e3 if s.endswith("K") else 1
    try:
        return float(s.rstrip("MK")) * mul
    except ValueError:
        return 0


def quet_kenh(url, work: Path, n: int = 10, log=print) -> list:
    """Quét video của kênh -> [{'url','title','loi'}]; lưu cache work/kich_ban.json.
    url: link kênh (yt-dlp tự lấy danh sách) HOẶC list link video (lấy từ trình duyệt khi TikTok chặn)."""
    cache = work / "kich_ban.json"
    data = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    if isinstance(url, (list, tuple)):
        vids = [{"id": u.rstrip("/").split("/")[-1], "url": u, "title": ""} for u in url[:n]]
    else:
        vids = danh_sach_video(url, n)
    out = []
    for i, v in enumerate(vids, 1):
        if v["id"] in data:
            out.append(data[v["id"]])
            continue
        log(f"[{i}/{len(vids)}] tải {v['url']}")
        try:
            f = tai_tieng(v["url"], work / "tieng")
            log("   nghe + chép lời...")
            item = {"url": v["url"], "title": v["title"], "loi": chep_loi(f)}
            log(f"   xong: {item['loi'][:60]}")
        except Exception as e:
            log(f"   lỗi: {e}")
            continue
        data[v["id"]] = item
        cache.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        out.append(item)
    return out


SCHEMA_PT = {
    "type": "object",
    "properties": {
        "mo_ta": {"type": "string", "description": "dạng content của kênh, 4-8 gạch đầu dòng: kiểu video, góc kể, "
                                                     "cách mở 3 giây, nhịp, cách dẫn, cách chốt"},
        "cach_viet": {"type": "string", "description": "quy tắc viết lời rút ra để viết lại cho sản phẩm khác"},
        "tieu_de": {"type": "string", "description": "các kiểu đặt tiêu đề / câu giật hay dùng của kênh, kèm ví dụ"},
    },
    "required": ["mo_ta", "cach_viet", "tieu_de"], "additionalProperties": False,
}


def phan_tich(work: Path, S: dict, log=print) -> dict:
    """AI đọc các kịch bản đã quét của 1 kênh -> dạng content + cách viết + kiểu tiêu đề. Lưu work/phan_tich.json."""
    import time
    from core import analyze
    from core.config import MODELS, NO_AI
    cache = work / "kich_ban.json"
    data = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    vids = [v for v in data.values() if (v.get("loi") or "").strip()]
    if not vids:
        raise ValueError("Kênh này chưa có kịch bản nào quét được")
    model = S.get("ai_model") or NO_AI
    if model == NO_AI or model not in MODELS:
        raise ValueError("Chưa chọn AI trong Cài đặt")
    loi = "\n\n".join(f"--- Video {i + 1} ---\n" + (f"Mô tả đăng kèm: {v['title']}\n" if v.get("title") else "")
                      + v["loi"] for i, v in enumerate(vids[:12]))
    content = [{"type": "text", "text":
                f"Đây là lời đọc (chép tự động, có thể sai chính tả) của {len(vids[:12])} video TikTok từ 1 kênh tham "
                f"khảo ({work.name}). Phân tích DẠNG CONTENT của kênh để áp dụng cho kênh bán phân bón / thuốc "
                f"nông nghiệp của mình: kiểu video, góc kể chuyện, cách giật tít mở đầu 3 giây, nhịp câu, xưng hô, "
                f"cách dẫn tới sản phẩm, cách chốt đơn, kiểu tiêu đề hay dùng. Không cần nêu sản phẩm của họ.\n\n{loi}"}]
    log("AI phân tích dạng content của kênh...")
    sys_ = "Bạn là biên tập viên content TikTok bán hàng, phân tích cách làm content của kênh khác để học theo."
    r = (analyze._gemini if model.startswith("gemini") else analyze._claude)(content, SCHEMA_PT, S, model, system=sys_)
    r.update(so_video=len(vids), luc=time.strftime("%d/%m/%Y %H:%M"))
    (work / "phan_tich.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    log("Đã phân tích xong dạng content")
    return r


def doc_phan_tich(work: Path) -> dict:
    try:
        return json.loads((work / "phan_tich.json").read_text(encoding="utf-8"))
    except Exception:
        return {}
