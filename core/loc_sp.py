"""Tự lọc video theo sản phẩm (Sonix Edit Video).

Đầu vào: 1 thư mục video lẫn lộn (anh đặt tên file có tên sản phẩm càng tốt).
Mỗi video, nhận ra sản phẩm theo thứ tự:
  1. tên file (từ khoá ten_file trong danh mục)
  2. máy đọc chữ trên nhãn ở 4 khung hình (từ khoá nhan)
  3. AI xem 4 khung hình (nếu có AI)
Đầu ra: mỗi sản phẩm 1 thư mục MỚI "<THƯ MỤC SẢN PHẨM> <tên đợt>" (vd "KÍCH RỄ 13-11-2026") trong thư mục
nguồn của Edit Video; không gộp vào thư mục có sẵn. Không nhận ra / nhiều sản phẩm -> "CẦN XEM <tên đợt>".
Mặc định CHÉP (file gốc giữ nguyên).
"""
import json
import shutil
import time
from pathlib import Path

from .config import DATA_DIR, VIDEO_EXTS
from .san_pham import SAN_PHAM, khong_dau, theo_ten_file

CAN_XEM = "CẦN XEM"
SCHEMA = {
    "type": "object",
    "properties": {
        "san_pham": {"type": "string", "description": "mã sản phẩm, 'nhieu' nếu thấy rõ từ 2 sản phẩm, 'khong_ro' nếu không chắc"},
        "ly_do": {"type": "string"},
    },
    "required": ["san_pham", "ly_do"], "additionalProperties": False,
}


def thu_muc_dich(root: Path, ten_dot: str) -> dict:
    """{mã sp hoặc 'can_xem': Path} cho đợt này."""
    out = {k: root / f"{sp['thu_muc']} {ten_dot}".strip() for k, sp in SAN_PHAM.items()}
    out["can_xem"] = root / f"{CAN_XEM} {ten_dot}".strip()
    return out


def trung_ten(root: Path, ten_dot: str) -> list:
    """Thư mục đích đã có sẵn trên máy (phải đặt tên đợt khác)."""
    return [p for p in thu_muc_dich(root, ten_dot).values() if p.exists()]


def _khung(path, n=4):
    from .canh import khung
    from .video_utils import probe
    d = probe(str(path))["duration"] or 0
    ts = [d * x for x in (0.15, 0.38, 0.6, 0.82)][:n] if d > 1 else [0]
    return [im for im in (khung(path, t, 480) for t in ts) if im is not None]


def _ocr(imgs) -> dict:
    """{mã sp: số lần thấy chữ nhãn}."""
    from .canh import _ocr as ocr
    dem = {}
    for im in imgs:
        res, _ = ocr()(im, use_cls=False)
        t = " ".join(khong_dau(x[1]) for x in (res or []))
        for k, sp in SAN_PHAM.items():
            if any(w in t for w in sp.get("nhan", [])):
                dem[k] = dem.get(k, 0) + 1
    return dem


def _ai(imgs, settings, model) -> dict:
    from . import analyze
    from .canh import CANH_DIR, _tam_anh
    tmp = CANH_DIR / "_loc.jpg"
    CANH_DIR.mkdir(parents=True, exist_ok=True)
    _tam_anh(imgs, tmp)
    ds = "\n".join(f"- {k}: {sp['ten']} ({sp['quy_cach']}). Hình: {sp.get('hinh', '')}" for k, sp in SAN_PHAM.items())
    content = [{"type": "text", "text": "Các ảnh là khung hình cắt từ 1 video bán phân bón / thuốc. "
                "Video đang giới thiệu sản phẩm nào trong danh sách?\n" + ds +
                "\nTrả mã sản phẩm. Thấy rõ từ 2 sản phẩm trong danh sách được giới thiệu ngang nhau thì 'nhieu'. "
                "Không thấy sản phẩm nào trong danh sách hoặc không chắc thì 'khong_ro'."},
               analyze._img(tmp)]
    sys_ = "Bạn nhận diện sản phẩm nông nghiệp trong video."
    if model.startswith("gemini"):
        return analyze._gemini(content, SCHEMA, settings, model, system=sys_)
    return analyze._claude(content, SCHEMA, settings, model, system=sys_)


def nhan_dien(path: Path, settings: dict, model: str = "") -> tuple:
    """-> (mã sp | 'can_xem', cách nhận ra)."""
    from .config import MODELS, NO_AI
    hits = theo_ten_file(path.stem + " " + path.parent.name)
    if len(hits) == 1:
        return hits[0], "tên file"
    imgs = _khung(path)
    if not imgs:
        return "can_xem", "không đọc được video"
    dem = _ocr(imgs)
    if hits:  # tên file có từ 2 sản phẩm: dùng chữ trên nhãn để chọn
        dem = {k: v for k, v in dem.items() if k in hits} or {k: 0 for k in hits}
    top = sorted(dem.items(), key=lambda x: -x[1])
    if top and top[0][1] >= 1 and (len(top) == 1 or top[0][1] >= 2 * top[1][1]):
        return top[0][0], f"chữ trên nhãn ({top[0][1]}/{len(imgs)} khung)"
    model = model or settings.get("ai_model") or NO_AI
    if model != NO_AI and model in MODELS:
        try:
            r = _ai(imgs, settings, model)
            if r.get("san_pham") in SAN_PHAM:
                return r["san_pham"], "AI: " + r.get("ly_do", "")[:80]
            return "can_xem", "AI: " + r.get("ly_do", "")[:80]
        except Exception as e:
            return "can_xem", f"AI lỗi: {e}"
    return "can_xem", "không nhận ra (chưa bật AI)"


def loc(nguon: Path, root: Path, ten_dot: str, settings: dict, chuyen: bool = False, log=print) -> dict:
    nguon, root = Path(nguon), Path(root)
    trung = trung_ten(root, ten_dot)
    if trung:
        raise ValueError("Đã có thư mục: " + ", ".join(p.name for p in trung) + ". Đặt tên đợt khác.")
    dich = thu_muc_dich(root, ten_dot)
    files = sorted(p for p in nguon.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTS
                   and not any(d in p.parents for d in dich.values()))
    log(f"Lọc {len(files)} video từ {nguon} ({'chuyển' if chuyen else 'chép'})")
    bao_cao, dem = [], {}
    for i, f in enumerate(files, 1):
        k, why = nhan_dien(f, settings)
        d = dich[k]
        d.mkdir(parents=True, exist_ok=True)
        dst = d / f.name
        n = 2
        while dst.exists():
            dst = d / f"{f.stem} ({n}){f.suffix}"
            n += 1
        (shutil.move if chuyen else shutil.copy2)(str(f), str(dst))
        dem[k] = dem.get(k, 0) + 1
        bao_cao.append({"file": str(f), "san_pham": k, "cach": why, "den": str(dst)})
        ten = SAN_PHAM[k]["ten"] if k in SAN_PHAM else CAN_XEM
        log(f"[{i}/{len(files)}] {f.name[:50]} -> {ten} ({why})")
    rp = DATA_DIR / "edit" / "loc" / f"{time.strftime('%Y%m%d_%H%M%S')}.json"
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(bao_cao, ensure_ascii=False, indent=1), encoding="utf-8")
    log("Kết quả: " + ", ".join(f"{(SAN_PHAM[k]['ten'] if k in SAN_PHAM else CAN_XEM)}: {v}" for k, v in dem.items()))
    return dem
