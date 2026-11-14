"""Phong cách mẫu cho Sonix Edit Video.

Thư mục <nguồn Edit Video>\\MẪU\\<tên phong cách>\\ chứa vài video mẫu (người dùng tự đặt tên thư mục con).
"Học" 1 phong cách:
  - chép lời từng video (nghe trên máy)            -> AI học cách viết lời
  - đo nhịp cắt cảnh (số giây trung bình mỗi cảnh) -> dựng với nhịp tương tự
  - AI xem khung hình + lời                        -> tóm tắt phong cách (mở đầu, giọng, cách chèn chữ, nhịp...)
Kết quả lưu data/edit/mau/<tên>.json. Video để thẳng trong MẪU (không thư mục con) tính là phong cách "Chung".
"""
import json
import re
import time
from pathlib import Path

from .config import DATA_DIR, VIDEO_EXTS

MAU = "MẪU"
CHUNG = "Chung"
DATA = DATA_DIR / "edit" / "mau"
SCHEMA = {
    "type": "object",
    "properties": {
        "mo_ta": {"type": "string", "description": "tóm tắt phong cách 4-8 gạch đầu dòng"},
        "cach_viet": {"type": "string", "description": "quy tắc viết lời rút ra: câu mở, nhịp câu, xưng hô, câu chốt"},
    },
    "required": ["mo_ta", "cach_viet"], "additionalProperties": False,
}


def thu_muc(S) -> Path:
    from .edit_video import input_root
    return input_root(S) / MAU


def _ten_file(ten: str) -> Path:
    return DATA / (re.sub(r'[<>:"/\\|?*]', "_", ten) + ".json")


def danh_sach(S) -> dict:
    """{tên phong cách: [video...]} theo thư mục con của MẪU."""
    root = thu_muc(S)
    out = {}
    if not root.exists():
        return out
    le = [p for p in root.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
    if le:
        out[CHUNG] = sorted(le)
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        vids = sorted(p for p in d.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTS)
        out[d.name] = vids
    return out


MAC_DINH = Path(__file__).resolve().parent / "mac_dinh"  # phần đã học đi kèm app (phong cách mặc định)


def doc(ten: str) -> dict:
    for f in (_ten_file(ten), MAC_DINH / _ten_file(ten).name):
        if f.exists():
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                pass
    return {}


def _nhip(path: Path) -> list:
    """Độ dài các cảnh (giây) theo chỗ cắt cảnh."""
    from scenedetect import ContentDetector, detect
    sc = detect(str(path), ContentDetector(threshold=27), show_progress=False)
    return [round(e.get_seconds() - s.get_seconds(), 2) for s, e in sc if e.get_seconds() > s.get_seconds()]


def hoc(S: dict, ten: str, log=print) -> dict:
    from . import tham_khao
    from .canh import _tam_anh, khung
    from .video_utils import probe
    vids = danh_sach(S).get(ten, [])
    if not vids:
        raise ValueError(f"Thư mục mẫu '{ten}' chưa có video")
    cu = doc(ten)
    videos = cu.get("videos", {})
    for i, v in enumerate(vids, 1):
        k = v.name
        if k in videos and videos[k].get("loi"):
            continue
        log(f"[{i}/{len(vids)}] {k}: nghe + chép lời...")
        item = {"dur": probe(str(v))["duration"]}
        try:
            item["loi"] = tham_khao.chep_loi(str(v))
        except Exception as e:
            item["loi"] = ""
            log(f"   không chép được lời: {e}")
        try:
            item["canh"] = _nhip(v)
        except Exception:
            item["canh"] = []
        log(f"   {len(item['loi'].split())} chữ, {len(item['canh'])} cảnh")
        videos[k] = item
        DATA.mkdir(parents=True, exist_ok=True)
        _ten_file(ten).write_text(json.dumps({**cu, "ten": ten, "videos": videos}, ensure_ascii=False, indent=1),
                                  encoding="utf-8")
    canh = sorted(x for v in videos.values() for x in v.get("canh", []) if x > 0.2)
    nhip = canh[len(canh) // 2] if canh else 0  # trung vị: không bị vài cảnh dài kéo lệch
    out = {"ten": ten, "videos": videos, "nhip": nhip, "luc": time.strftime("%d/%m/%Y %H:%M"),
           "giay_tb": round(sum(v.get("dur", 0) for v in videos.values()) / max(1, len(videos)), 1),
           "chu_tb": round(sum(len(v.get("loi", "").split()) for v in videos.values()) / max(1, len(videos)))}
    log(f"Nhịp cắt cảnh: {nhip:.1f} giây/cảnh, video dài trung bình {out['giay_tb']} giây, {out['chu_tb']} chữ")

    # AI tóm tắt phong cách (nếu có AI)
    from .config import MODELS, NO_AI
    model = S.get("ai_model") or NO_AI
    if model != NO_AI and model in MODELS:
        log("AI xem mẫu và tóm tắt phong cách...")
        from . import analyze
        imgs = []
        for v in vids[:3]:
            d = probe(str(v))["duration"] or 0
            imgs += [im for im in (khung(v, d * x, 360) for x in (0.05, 0.3, 0.6, 0.9)) if im is not None]
        tmp = DATA / "_xem.jpg"
        if imgs:
            _tam_anh(imgs[:12], tmp, 300)
        loi = "\n\n".join(f"--- Video {i + 1} ---\n{v.get('loi', '')}" for i, v in enumerate(list(videos.values())[:6]))
        content = [{"type": "text", "text":
                    f"Đây là các video mẫu của 1 phong cách edit TikTok bán hàng nông nghiệp (tên: {ten}). "
                    f"Nhịp cắt cảnh ~{nhip:.1f} giây/cảnh, video dài ~{out['giay_tb']} giây. "
                    "Ảnh là khung hình đầu/giữa/cuối của 3 video. Lời đọc (chép tự động, có thể sai chính tả):\n"
                    f"{loi}\n\nTóm tắt phong cách để người khác làm theo: cách mở đầu 3 giây, giọng đọc, nhịp, "
                    "cách chèn chữ/tiêu đề, khung hình, nhạc, cách chốt. Rút ra quy tắc viết lời."}]
        if imgs:
            content.append(analyze._img(tmp))
        try:
            sys_ = "Bạn là biên tập viên video TikTok, phân tích phong cách để người khác làm theo."
            r = (analyze._gemini if model.startswith("gemini") else analyze._claude)(content, SCHEMA, S, model,
                                                                                     system=sys_)
            out.update(mo_ta=r["mo_ta"], cach_viet=r["cach_viet"])
        except Exception as e:
            log(f"AI lỗi: {e}")
    _ten_file(ten).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def loi_mau(ten: str) -> list:
    return [v["loi"] for v in doc(ten).get("videos", {}).values() if v.get("loi")]
