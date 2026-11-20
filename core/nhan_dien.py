"""Nhận diện sản phẩm MIỄN PHÍ, chạy trên máy, không cần mạng: đọc CHỮ TRÊN NHÃN trong khung hình (máy đọc chữ
RapidOCR, đã cài sẵn cho Sonix Edit Video), so với chữ nhãn / từ khoá của từng sản phẩm.

Dùng trước khi gọi AI: nhận ra chắc chắn thì AI chỉ cần viết caption (hoặc không cần AI). Chọn luôn khung hình
thấy nhãn rõ nhất làm ảnh bìa.
"""
import re
from pathlib import Path

from .config import norm

DUNG_TICH = {"dam_ca_1l": [r"\b1 ?l\b", r"\b1 ?lit\b", r"\b1000 ?ml\b"],
             "dam_ca_5l": [r"\b5 ?l\b", r"\b5 ?lit\b", r"\bcan 5\b"]}


def _key_edit(item_key) -> str:
    """Mã sản phẩm của Up Video -> mã bên Edit Video (dam_ca_1l / dam_ca_5l -> dam_ca)."""
    return "dam_ca" if item_key.startswith("dam_ca") else item_key


def _chu(t) -> str:
    return re.sub(r"\s+", " ", norm(str(t)).replace("đ", "d")).strip()


def tu_nhan(settings) -> dict:
    """{mã sp: [chữ cần thấy trên nhãn]} gộp từ: chữ nhãn bên Edit Video + từ khoá + tên sản phẩm."""
    try:
        from . import san_pham as sp_edit
        edit = sp_edit.nap()
    except Exception:
        edit = {}
    out = {}
    for it in settings.get("items", []):
        ws = set()
        for w in (edit.get(_key_edit(it["key"])) or {}).get("nhan", []):
            ws.add(_chu(w))
        for w in str(it.get("keywords") or "").split(","):
            ws.add(_chu(w))
        ws = {w for w in ws if len(w.replace(" ", "")) >= 3 and not re.fullmatch(r"[\d ]+(l|lit|ml)?", w)}
        out[it["key"]] = sorted(ws)
    return out


def thong_tin(settings, item_key) -> str:
    """Thành phần / công dụng / cách dùng của sản phẩm (bác điền ở Sonix Edit Video) để AI viết caption đúng."""
    try:
        from . import san_pham as sp_edit
        return ((sp_edit.nap().get(_key_edit(item_key or "")) or {}).get("thong_tin") or "").strip()
    except Exception:
        return ""


_OCR = None


def _ocr():
    global _OCR
    if _OCR is None:
        from rapidocr_onnxruntime import RapidOCR
        _OCR = RapidOCR()
    return _OCR


def co_ocr() -> bool:
    try:
        import rapidocr_onnxruntime  # noqa: F401
        return True
    except Exception:
        return False


def doc_chu(img_path) -> str:
    res, _ = _ocr()(str(img_path), use_cls=False)
    return _chu(" ".join(x[1] for x in (res or [])))


def doan(settings, frame_paths) -> dict:
    """Đọc chữ trên các khung hình -> {"item": mã | "", "conf": 0-95, "best": chỉ số khung rõ nhất, "why": ...}."""
    words = tu_nhan(settings)
    dem, best_frame, chu_all = {}, {}, []
    for i, p in enumerate(frame_paths):
        try:
            t = doc_chu(p)
        except Exception:
            continue
        chu_all.append(t)
        for k, ws in words.items():
            n = sum(1 for w in ws if re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", t))
            if n:
                dem[k] = dem.get(k, 0) + 1
                if n > best_frame.get(k, (-1, 0))[1]:
                    best_frame[k] = (i, n)
    if not dem:
        return {"item": "", "conf": 0, "best": None, "why": "không đọc được chữ sản phẩm trên nhãn"}
    # đạm cá: 2 loại cùng chữ nhãn -> phân biệt bằng dung tích đọc được
    if "dam_ca_1l" in dem and "dam_ca_5l" in dem:
        all_t = " ".join(chu_all)
        has = {k: any(re.search(rx, all_t) for rx in DUNG_TICH[k]) for k in DUNG_TICH}
        if has["dam_ca_5l"] and not has["dam_ca_1l"]:
            dem.pop("dam_ca_1l")
        elif has["dam_ca_1l"] and not has["dam_ca_5l"]:
            dem.pop("dam_ca_5l")
    top = sorted(dem.items(), key=lambda x: -x[1])
    k, n = top[0]
    tie = len(top) > 1 and top[1][1] == n
    conf = 92 if n >= 2 and not tie else 80 if not tie else 55
    return {"item": k, "conf": conf, "best": best_frame[k][0], "tie": tie,
            "why": f"đọc được chữ nhãn ở {n}/{len(frame_paths)} khung" + (" (có sản phẩm khác ngang điểm)" if tie else "")}


def khung_ocr(video_path, work: Path, n=5):
    """Cắt n khung nét (rộng 960) để máy đọc chữ; trả về [(giây, đường dẫn)]."""
    from .video_utils import export_frame, frame_times
    out = []
    for i, t in enumerate(frame_times(video_path, n)):
        p = work / f"ocr{i}.jpg"
        if export_frame(video_path, t, str(p), width=960):
            out.append((t, p))
    return out
