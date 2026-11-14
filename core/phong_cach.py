"""Phong cách edit = 1 BỘ gồm 4 thứ (để sau này nhân bản phong cách mới chỉ bằng cách đưa video mẫu cho app):
  mau        MẪU\\<tên phong cách>         vài video mẫu -> app học cách làm (core/mau.py)
  source     SOURCE THÔ\\<tên tự đặt>      video nguyên liệu (vd 'Video Aff' cho Reup Aff) -> Tự lọc theo sản phẩm
  tai_nguyen TÀI NGUYÊN                    nhạc nền, khung, người dẫn + khuôn CapCut 'mẫu'
  quy_trinh  cách dựng: hiện có 'reup_aff' (video có sẵn -> chọn cảnh -> lồng tiếng AI -> khuôn CapCut -> tự xuất)
Bộ của từng phong cách lưu data/edit/phong_cach.json.
"""
import json
from pathlib import Path

from .config import DATA_DIR, VIDEO_EXTS

FILE = DATA_DIR / "edit" / "phong_cach.json"
MAU, SOURCE, TAI_NGUYEN = "MẪU", "SOURCE THÔ", "TÀI NGUYÊN"
QUY_TRINH = {
    "reup_aff": "Reup Aff · video có sẵn → chọn cảnh → lồng tiếng AI → khuôn CapCut → tự xuất 1080p",
    "xoay_minh_hoa": "Xoay + minh hoạ · video tự quay xoay sản phẩm + chèn cảnh aff cùng sản phẩm (2x, tắt tiếng) "
                     "→ giữ tiếng gốc → xuất thẳng mp4 1080p",
}
SAP_CO = "Quay thô tự cắt phần thừa · hiệu ứng (sắp có)"
# Phong cách có sẵn trên mọi máy: tự tạo MẪU\<tên> + SOURCE THÔ\<source> khi mở Edit Video
MAC_DINH = {
    "Reup Aff": {"source": "Video Aff", "quy_trinh": "reup_aff"},
    "Xoay minh họa": {"source": "Xoay", "quy_trinh": "xoay_minh_hoa"},
}


def goc(S) -> Path:
    from .edit_video import input_root
    return input_root(S)


def chuan_bi(S):
    """Đảm bảo có MẪU, SOURCE THÔ (đổi tên từ CHƯA LỌC của bản cũ), TÀI NGUYÊN. Gọi được lúc app đang chạy."""
    r = goc(S)
    if not r.exists():
        return
    cu, moi = r / "CHƯA LỌC", r / SOURCE
    try:
        if cu.is_dir() and not moi.exists():
            cu.rename(moi)
        for sub in (MAU, SOURCE, TAI_NGUYEN):
            (r / sub).mkdir(exist_ok=True)
        for ten, b in MAC_DINH.items():
            (r / MAU / ten).mkdir(exist_ok=True)
            (r / SOURCE / b["source"]).mkdir(exist_ok=True)
    except OSError:
        pass


def _dem(d: Path) -> int:
    return sum(1 for p in d.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTS) if d.is_dir() else 0


def ds_mau(S) -> list:
    d = goc(S) / MAU
    return sorted(p.name for p in d.iterdir() if p.is_dir()) if d.is_dir() else []


def ds_source(S) -> list:
    d = goc(S) / SOURCE
    return sorted(p.name for p in d.iterdir() if p.is_dir()) if d.is_dir() else []


def doc_tat_ca() -> dict:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def bo(ten: str) -> dict:
    """Bộ của phong cách `ten` (mặc định quy trình Reup Aff)."""
    b = {"mau": ten, "source": "", "quy_trinh": "reup_aff"}
    b.update(MAC_DINH.get(ten, {}))
    b.update(doc_tat_ca().get(ten, {}))
    return b


def luu(ten: str, **fields):
    data = doc_tat_ca()
    data.setdefault(ten, {}).update(fields)
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def tom_tat(S, ten: str) -> dict:
    """Xem qua đủ 4 thứ của phong cách trước khi edit."""
    from . import mau as mau_mod
    from . import capcut_draft, edit_video
    r = goc(S)
    b = bo(ten)
    hoc = mau_mod.doc(b["mau"])
    src = r / SOURCE / b["source"] if b["source"] else None
    tn = r / TAI_NGUYEN
    tpl = S.get("edit_template") or edit_video.TEMPLATE
    return {
        "bo": b,
        "mau_dir": r / MAU / b["mau"], "mau_so": _dem(r / MAU / b["mau"]),
        "mau_da_hoc": len(hoc.get("videos", {})), "nhip": hoc.get("nhip", 0), "mo_ta": hoc.get("mo_ta", ""),
        "source_dir": src, "source_so": _dem(src) if src else 0,
        "tn_dir": tn, "nhac": [p.name for p in edit_video.nhac_nen(r)],
        "anh": sorted(p.name for p in tn.glob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")) if tn.is_dir() else [],
        "khuon": (capcut_draft.CAPCUT_DRAFTS / tpl / "draft_content.json").exists(), "ten_khuon": tpl,
    }
