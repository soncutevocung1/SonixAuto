"""Quét & chọn cảnh cho Sonix Edit Video.

Mỗi video nguồn -> cắt thành đoạn ngắn (theo cảnh quay) -> lấy 1 khung giữa đoạn:
  - dò mặt người (MediaPipe)       -> có người thì bỏ (tránh bản quyền / vi phạm)
  - dò chữ (RapidOCR)              -> chữ trên nhãn sản phẩm thì giữ; chữ chèn / sticker / phụ đề thì bỏ
  - vị trí nhãn sản phẩm           -> tính độ đẩy video lên riêng từng đoạn để nền xanh không che sản phẩm
  - (có AI) Claude xem ảnh, gắn loại cảnh: san_pham / su_dung / ket_qua / khac, kiểm tra lại người + chữ chèn
Kết quả lưu data/edit/canh/<sp_key>.json, video nào quét rồi (cùng thời gian sửa) thì bỏ qua.
"""
import json
import os
import subprocess
import sys
import unicodedata
from pathlib import Path

import numpy as np

from core.config import DATA_DIR
from core.video_utils import _ffmpeg, probe

_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
CANH_DIR = DATA_DIR / "edit" / "canh"
FACE_MODEL = DATA_DIR / "models" / "blaze_face_short_range.tflite"
FACE_URL = ("https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/"
            "float16/latest/blaze_face_short_range.tflite")

DOAN_MIN, DOAN_MAX = 2.0, 4.0   # giây gốc mỗi đoạn (2x -> 1-2 giây trên timeline)
DAI_XANH = 0.66                 # dải xanh theme.png mờ dần từ ~58.5%, che hẳn từ ~66-70% chiều cao
Y_MAX = 0.55                    # đẩy tối đa (đơn vị CapCut, 1 = nửa khung). Anh Sơn chỉnh tay: 0.53, 0.506
                                # (0.7 là quá cao). Giới hạn cứng của khung là ~0.83.
Y_SU_DUNG = 0.40                # cảnh pha / rót không dò được vị trí: đẩy lên để thấy cảnh rót (anh chỉnh 0.40)
TU_KHOA = {  # chữ trên nhãn sản phẩm (không dấu, in hoa)
    "dam_ca": ["DAM CA", "AMINO", "ORGANIC", "WIN GOLD", "HUU CO", "PHAN BON", "DAM DAC", "HUONG DAN"],
    "tc01": ["TC01", "TC 01", "KICH RE", "ATONIK", "GIAM CANH", "PHAN BON", "HUONG DAN"],
}
LOAI = ["san_pham", "su_dung", "ket_qua", "khac"]


def _khong_dau(s: str) -> str:
    s = unicodedata.normalize("NFD", s.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").upper()


# ---------- công cụ dò ----------
_DET = _OCR = None


def _face():
    global _DET
    if _DET is None:
        if not FACE_MODEL.exists():
            import requests
            FACE_MODEL.parent.mkdir(parents=True, exist_ok=True)
            FACE_MODEL.write_bytes(requests.get(FACE_URL, timeout=60).content)
        from mediapipe.tasks.python import BaseOptions, vision
        _DET = vision.FaceDetector.create_from_options(vision.FaceDetectorOptions(
            base_options=BaseOptions(model_asset_path=str(FACE_MODEL)), min_detection_confidence=0.55))
    return _DET


def _ocr():
    global _OCR
    if _OCR is None:
        from rapidocr_onnxruntime import RapidOCR
        _OCR = RapidOCR()
    return _OCR


def khung(path: str, t: float, w: int = 360):
    """Ảnh BGR tại giây t (rộng w)."""
    import cv2
    raw = subprocess.run([_ffmpeg(), "-v", "error", "-ss", f"{max(t, 0):.2f}", "-i", str(path), "-frames:v", "1",
                          "-vf", f"scale={w}:-2", "-f", "image2pipe", "-vcodec", "png", "-"],
                         capture_output=True, creationflags=_NO_WINDOW).stdout
    if not raw:
        return None
    return cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)


def _vien_den(img) -> float:
    """Tỉ lệ chiều cao bị viền đen (video ngang đặt trong khung dọc)."""
    g = img.mean(axis=(1, 2))
    den = g < 12
    return float(den.mean())


def soi_khung(img, sp_key: str) -> dict:
    """Dò người + chữ + vị trí nhãn sản phẩm trên 1 khung (toạ độ chuẩn hoá 0-1, y tính từ trên xuống)."""
    import cv2
    import mediapipe as mp
    h, w = img.shape[:2]
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    faces = [f for f in _face().detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))).detections
             if f.bounding_box.width * f.bounding_box.height > 0.004 * w * h]
    res, _ = _ocr()(img, use_cls=False)
    from .san_pham import SAN_PHAM
    kw = (SAN_PHAM.get(sp_key) or {}).get("nhan") or TU_KHOA.get(sp_key, [])
    kw = kw + ["PHAN BON", "HUONG DAN"]
    nhan, khac = [], []
    # chữ nhãn của sản phẩm KHÁC (video nguồn hay lẫn: thư mục Đạm cá có cảnh Nano Đồng...)
    kw_khac = {k: [x for x in v.get("nhan", []) if len(x) >= 5 and x not in kw]
               for k, v in SAN_PHAM.items() if k != sp_key}
    toan_bo = " ".join(_khong_dau(x[1]) for x in (res or []))
    sp_khac = [k for k, ws in kw_khac.items() if any(x in toan_bo for x in ws)]
    for box, txt, sc in (res or []):
        p = np.array(box, float)
        x0, y0, x1, y1 = p[:, 0].min() / w, p[:, 1].min() / h, p[:, 0].max() / w, p[:, 1].max() / h
        t = _khong_dau(txt)
        (nhan if any(k in t for k in kw) else khac).append((x0, y0, x1, y1, txt, float(sc)))
    sp = None
    if nhan:
        # Nhãn: bắt đầu từ chữ có tên sản phẩm, gom dần mọi dòng chữ sát bên (chữ nhỏ, hướng dẫn, hotline...)
        x0 = min(b[0] for b in nhan); y0 = min(b[1] for b in nhan)
        x1 = max(b[2] for b in nhan); y1 = max(b[3] for b in nhan)
        gap = 0.06
        doi = True
        while doi:
            doi = False
            for b in list(khac):
                if b[0] <= x1 + gap and b[2] >= x0 - gap and b[1] <= y1 + gap and b[3] >= y0 - gap:
                    x0, y0, x1, y1 = min(x0, b[0]), min(y0, b[1]), max(x1, b[2]), max(y1, b[3])
                    khac.remove(b)
                    doi = True
        hh = y1 - y0
        sp = [max(0, x0 - 0.03), max(0, y0 - 0.15 * hh), min(1, x1 + 0.03), min(1, y1 + 0.2 * hh + 0.02)]
    chen = []
    for b in khac:
        cao = b[3] - b[1]
        t = _khong_dau(b[4])
        chu = sum(c.isalnum() for c in t)
        if "HOTLINE" in t or (any(k in t for k in ("LIT", "100%", "CUC", "NHANH", "MANH")) and chu < 14):
            continue  # chữ in trên can (huy hiệu, dung tích, hotline)
        if cao >= 0.028 and b[5] >= 0.6 and chu >= 4:
            chen.append([round(float(v), 3) for v in b[:4]] + [b[4]])
    return {"nguoi": len(faces), "chu_chen": chen, "sp": [round(float(v), 3) for v in sp] if sp else None,
            "vien_den": round(_vien_den(img), 2), "sp_khac": sp_khac}


def do_day(sp_box) -> float:
    """Độ đẩy video lên (transform y CapCut) để đáy sản phẩm nằm trên nền xanh. Không thấy sản phẩm -> 0."""
    if not sp_box:
        return 0.0
    can = sp_box[3] - (DAI_XANH - 0.02)
    can = min(can, sp_box[1])  # sản phẩm cao hơn phần nhìn thấy -> không đẩy mất đầu sản phẩm
    return round(min(Y_MAX, max(0.0, 2 * can)), 2)


def y_doan(d: dict) -> float:
    if d.get("sp"):
        y = do_day(d["sp"])
    else:
        day = d.get("ai_sp_day") or 0
        y = do_day([0, max(0.0, day - 0.4), 1, day]) if day > 0 else 0.0
    if d.get("loai") == "su_dung":
        y = max(y, Y_SU_DUNG)
    return y


# ---------- cắt đoạn ----------
def tach_doan(path: str) -> list:
    """[(start, end)] giây gốc: theo cảnh quay, đoạn dài chia nhỏ DOAN_MIN-DOAN_MAX."""
    dur = probe(str(path))["duration"]
    cuts = [0.0, dur]
    try:
        from scenedetect import ContentDetector, detect
        sc = detect(str(path), ContentDetector(threshold=27), show_progress=False)
        cuts = sorted({0.0, dur, *[s[0].get_seconds() for s in sc], *[s[1].get_seconds() for s in sc]})
    except Exception:
        pass
    out = []
    for a, b in zip(cuts, cuts[1:]):
        a, b = a + 0.15, b - 0.15  # tránh khung chuyển cảnh
        n = int((b - a) // DOAN_MAX) + (1 if (b - a) % DOAN_MAX >= DOAN_MIN else 0)
        for i in range(n):
            s = a + i * DOAN_MAX
            e = min(b, s + DOAN_MAX)
            if e - s >= DOAN_MIN:
                out.append((round(s, 2), round(e, 2)))
    return out


# ---------- quét thư mục ----------
def _index_path(sp_key):
    return CANH_DIR / f"{sp_key}.json"


def doc_index(sp_key) -> dict:
    p = _index_path(sp_key)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _luu(sp_key, idx):
    CANH_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _index_path(sp_key).with_suffix(".tmp")
    tmp.write_text(json.dumps(idx, ensure_ascii=False, indent=0), encoding="utf-8")
    tmp.replace(_index_path(sp_key))


def do_dong(path: str, s: float, e: float) -> float:
    """Tỉ lệ cặp khung gần như đứng yên (ảnh tĩnh, outro, video ghép ảnh giật giật). Video quay thật ~0."""
    n = 64
    raw = subprocess.run([_ffmpeg(), "-v", "error", "-ss", f"{s:.2f}", "-t", f"{e - s:.2f}", "-i", str(path),
                          "-vf", f"fps=6,scale={n}:{n},format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, creationflags=_NO_WINDOW).stdout
    fr = np.frombuffer(raw, np.uint8)[: len(raw) // (n * n) * n * n].reshape(-1, n * n).astype(np.int16)
    if len(fr) < 3:
        return 1.0
    diff = np.abs(np.diff(fr, axis=0)).mean(axis=1)
    return round(float((diff < 1.2).mean()), 2)


OUTRO = 3.0  # bỏ 3 giây cuối mỗi video nguồn (thường là outro: ảnh + nút Follow)


def quet_video(path: str, sp_key: str) -> dict:
    p = probe(str(path))
    doan = []
    for s, e in tach_doan(path):
        if s >= p["duration"] - OUTRO:
            continue
        e = min(e, p["duration"] - OUTRO)
        if e - s < DOAN_MIN:
            continue
        img = khung(path, (s + e) / 2)
        if img is None:
            continue
        r = soi_khung(img, sp_key)
        r.update(s=s, e=round(e, 2), y=do_day(r["sp"]), tinh=do_dong(path, s, e))
        doan.append(r)
    return {"mtime": os.stat("\\\\?\\" + os.path.abspath(str(path))).st_mtime, "dur": p["duration"],
            "w": p["width"], "h": p["height"],
            "doan": doan}


def quet(sp_key: str, files: list, log=print) -> dict:
    """Quét (cục bộ, miễn phí) mọi video chưa quét. Lưu sau mỗi video."""
    idx = doc_index(sp_key)
    for i, f in enumerate(files, 1):
        k = str(f)
        try:
            if k in idx and abs(idx[k]["mtime"] - os.stat("\\\\?\\" + os.path.abspath(k)).st_mtime) < 1:
                continue
        except OSError:
            pass
        try:
            idx[k] = quet_video(k, sp_key)
            n = idx[k]["doan"]
            log(f"[{i}/{len(files)}] {Path(f).name[:50]}: {len(n)} đoạn, "
                f"{sum(1 for d in n if d['nguoi'])} có người, {sum(1 for d in n if d['chu_chen'])} có chữ chèn")
        except Exception as e:
            log(f"[{i}/{len(files)}] lỗi {Path(f).name[:50]}: {e}")
            continue
        _luu(sp_key, idx)
    return idx


# ---------- AI gắn loại cảnh ----------
AI_SCHEMA = {
    "type": "object",
    "properties": {"canh": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "so": {"type": "integer"},
            "loai": {"type": "string", "enum": LOAI},
            "nguoi": {"type": "boolean", "description": "thấy mặt / thân người rõ (chỉ bàn tay thì false)"},
            "chu_chen": {"type": "boolean", "description": "có chữ, sticker, phụ đề, khung bình luận chèn thêm (KHÔNG tính chữ in trên nhãn sản phẩm)"},
            "sp_khac": {"type": "boolean", "description": "thấy rõ một sản phẩm KHÁC sản phẩm đang làm video"},
            "sp_day": {"type": "number", "description": "mép dưới sản phẩm, 0 = đỉnh ảnh, 1 = đáy ảnh; không có sản phẩm thì 0"},
            "dep": {"type": "integer", "description": "1-5: hình rõ, đẹp, đúng chủ đề phân bón"},
        },
        "required": ["so", "loai", "nguoi", "chu_chen", "sp_khac", "sp_day", "dep"], "additionalProperties": False}}},
    "required": ["canh"], "additionalProperties": False,
}
AI_VER = 2  # đổi cách hỏi AI thì tăng số này: các đoạn gắn nhãn bằng bản cũ sẽ được AI xem lại
AI_HUONG_DAN = (
    "Các ảnh dưới đây là khung hình cắt từ video bán {ten} ({hinh}), đánh số trên góc. "
    "Các sản phẩm KHÁC cùng hãng hay lẫn vào: {khac}.\nVới MỖI ảnh cho biết:\n"
    "- loai: san_pham (cận sản phẩm/bao bì, đập hộp, cầm chai/can), su_dung (pha, đổ, tưới, phun, đong), "
    "ket_qua (cây, lá, rễ, hoa, quả, vườn tốt sau khi dùng), khac (không liên quan / mờ / màn hình đen)\n"
    "- nguoi: có mặt hoặc thân người thấy rõ (chỉ bàn tay cầm sản phẩm thì false)\n"
    "- chu_chen: có chữ / sticker / phụ đề / khung bình luận / logo kênh / nút Follow chèn thêm lên video, "
    "KỂ CẢ dòng phụ đề nhỏ ở giữa hoặc dưới ảnh (chữ in sẵn trên nhãn sản phẩm KHÔNG tính)\n"
    "- sp_khac: thấy rõ chai/can/gói của sản phẩm KHÁC {ten} (sản phẩm khác cùng hãng ở trên, hay hãng khác)\n"
    "- sp_day: mép dưới của sản phẩm theo chiều cao ảnh (0-1), không có sản phẩm thì 0\n"
    "- dep: 1-5")


def _tam_anh(imgs: list, path: Path, rong: int = 240):
    """Ghép các khung (đánh số, 6 khung / hàng) thành 1 ảnh để gửi AI 1 lần."""
    import cv2
    tiles = []
    for i, im in enumerate(imgs, 1):
        t = cv2.resize(im, (rong, int(rong * im.shape[0] / im.shape[1])))
        cv2.rectangle(t, (0, 0), (46, 34), (0, 0, 0), -1)
        cv2.putText(t, str(i), (4, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
        tiles.append(t)
    hh = max(t.shape[0] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, hh - t.shape[0], 0, 4, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in tiles]
    while len(tiles) % 6:
        tiles.append(np.full_like(tiles[0], 255))
    rows = [np.hstack(tiles[i:i + 6]) for i in range(0, len(tiles), 6)]
    cv2.imwrite(str(path), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 82])


def gan_nhan_ai(sp_key: str, settings: dict, model: str = "", log=print) -> dict:
    """Claude/Gemini xem các đoạn chưa gắn nhãn (12 đoạn / lần gọi)."""
    from core import analyze, kich_ban
    from core.config import MODELS, NO_AI
    model = model or settings.get("ai_model") or NO_AI
    if model == NO_AI or model not in MODELS:
        log("Không có AI -> chỉ dùng kết quả dò trên máy")
        return doc_index(sp_key)
    idx = doc_index(sp_key)
    # chưa gắn nhãn, hoặc gắn bằng cách hỏi cũ; bỏ qua đoạn chắc chắn hỏng (có người + ảnh tĩnh / viền đen)
    can = [(k, i) for k, v in idx.items() for i, d in enumerate(v["doan"])
           if d.get("ai_ver", 1 if "loai" in d else 0) < AI_VER and d.get("vien_den", 0) < 0.3
           and d.get("tinh", 0) < 0.4 and not d.get("sp_khac")]
    log(f"AI xem {len(can)} đoạn...")
    tmp = CANH_DIR / "_tam.jpg"
    sp = kich_ban.SAN_PHAM[sp_key]
    huong_dan = AI_HUONG_DAN.format(ten=sp["ten"], hinh=sp.get("hinh", ""),
                                    khac="; ".join(f"{v['ten']} ({v.get('hinh', '')})"
                                                   for k_, v in kich_ban.SAN_PHAM.items() if k_ != sp_key))
    N = 6  # 6 khung / lần, ảnh to hơn để AI đọc được phụ đề nhỏ
    for j in range(0, len(can), N):
        nhom = can[j:j + N]
        imgs = [khung(k, (idx[k]["doan"][i]["s"] + idx[k]["doan"][i]["e"]) / 2, 400) for k, i in nhom]
        ok = [(n, im) for n, im in zip(nhom, imgs) if im is not None]
        if not ok:
            continue
        _tam_anh([im for _, im in ok], tmp, 360)
        content = [{"type": "text", "text": huong_dan}, analyze._img(tmp)]
        try:
            if model.startswith("gemini"):
                r = analyze._gemini(content, AI_SCHEMA, settings, model, system="Bạn phân loại cảnh quay video.")
            else:
                r = analyze._claude(content, AI_SCHEMA, settings, model, system="Bạn phân loại cảnh quay video.")
        except Exception as e:
            log(f"   AI lỗi: {e}")
            continue
        for c in r.get("canh", []):
            n = c.get("so", 0) - 1
            if 0 <= n < len(ok):
                k, i = ok[n][0]
                d = idx[k]["doan"][i]
                d.update(loai=c["loai"], ai_nguoi=c["nguoi"], ai_chu=c["chu_chen"], dep=c["dep"],
                         ai_sp_khac=c.get("sp_khac", False), ai_ver=AI_VER,
                         ai_sp_day=c["sp_day"])  # nhãn không đọc được chữ -> dùng vị trí AI ước
        _luu(sp_key, idx)
        if (j // N) % 10 == 0 or j + N >= len(can):
            log(f"   {min(j + N, len(can))}/{len(can)}")
    return idx


# ---------- chọn cảnh ----------
def _sach(d: dict) -> bool:
    """Không chữ chèn, không ảnh tĩnh/giật, không viền đen, không phải cảnh rác."""
    # AI đã xem thì tin AI về chữ chèn (máy dò hay nhầm chữ trên nhãn); chữ máy dò thấy rất to thì vẫn bỏ
    # Máy đọc được cả 1 câu dài (>= 10 ký tự) ngoài nhãn: gần như chắc chắn là phụ đề -> bỏ dù AI bảo không
    if "ai_chu" in d:
        chu = d["ai_chu"] or any(c[3] - c[1] >= 0.05 or (sum(ch.isalpha() for ch in c[4]) >= 10
                                                          and "HOTLINE" not in _khong_dau(c[4]))
                                 for c in d["chu_chen"])
    else:
        chu = bool(d["chu_chen"])
    return (not chu and d.get("tinh", 0) < 0.4 and d.get("vien_den", 0) < 0.3
            and not d.get("sp_khac") and not d.get("ai_sp_khac")
            and d.get("loai") != "khac" and d.get("dep", 3) >= 2)


def dung_duoc(d: dict) -> bool:
    return _sach(d) and not d["nguoi"] and not d.get("ai_nguoi")


def co_nguoi(d: dict) -> bool:
    """Đoạn có người (dùng cho khung chia 4 ô)."""
    return _sach(d) and bool(d["nguoi"] or d.get("ai_nguoi"))


def loai_cau(cau: str) -> str:
    """Câu thoại cần cảnh gì."""
    import re
    t = " " + re.sub(r"[^\w\s]", " ", unicodedata.normalize("NFC", cau).lower()) + " "
    co = lambda ws: sum(f" {w} " in t for w in ws)
    # giữ dấu: "rẻ" (giá) khác "rễ" (cây); câu mở đầu nói giá -> cảnh sản phẩm
    gia = co(["giá", "rẻ", "giảm", "sale", "ship", "xả kho", "ưu đãi", "săn", "mua", "thanh toán", "bình luận"])
    dung = co(["pha", "tưới", "phun", "lít nước", "cách dùng", "liều", "ngày tưới"])
    cay = co(["cây", "lá", "xanh", "đọt", "rễ", "chồi", "hoa", "quả", "rễ tơ", "đẻ nhánh", "bung", "đất", "vườn"])
    if dung and dung >= cay:
        return "su_dung"
    if cay > gia:
        return "ket_qua"
    return "san_pham"


def chia_cau(loi: str, giay: float) -> list:
    """Lời -> [(câu, số giây)] chia theo số chữ (Vbee đọc đều)."""
    import re
    cau = [c.strip() for c in re.split(r"(?<=[.!?…])\s+", loi.strip()) if c.strip()]
    tong = sum(len(c) for c in cau) or 1
    return [(c, giay * len(c) / tong) for c in cau]


def chon(sp_key: str, cau_list: list, speed: float = 2.0, seed=None, luoi: bool = True) -> list:
    """cau_list = [(câu, số giây trên timeline)] -> clips [(path, src_start, src_len, y)] đủ thời lượng,
    có thể kèm 1 mục {'luoi': [4 x (path, start, len)]} = khung chia 4 ô người dùng.
    Không lặp lại đoạn, không lấy 2 đoạn liền nhau cùng 1 video."""
    import random
    rnd = random.Random(seed)
    idx = doc_index(sp_key)
    kho = {l: [] for l in LOAI}
    for k, v in idx.items():
        if not Path(k).exists():
            continue
        for d in v["doan"]:
            if dung_duoc(d):
                l = d.get("loai") or ("san_pham" if d["sp"] else "ket_qua")
                kho.setdefault(l, []).append((k, d))
    for l in kho:
        rnd.shuffle(kho[l])
        kho[l].sort(key=lambda x: -x[1].get("dep", 3))  # đẹp trước, cùng điểm thì ngẫu nhiên
    nguoi = [(k, d) for k, v in idx.items() if Path(k).exists() for d in v["doan"] if co_nguoi(d)]
    rnd.shuffle(nguoi)
    # Khung 4 ô: đặt ở câu nói về người dùng (không có thì câu giữa bài); cần 4 video KHÁC nhau
    o_luoi = None
    if luoi:
        cell, seen = [], set()
        for k, d in nguoi:
            if k not in seen:
                cell.append((k, d))
                seen.add(k)
            if len(cell) == 4:
                break
        if len(cell) == 4:
            hit = [i for i, (c, _) in enumerate(cau_list)
                   if any(w in _khong_dau(c) for w in ["NGUOI DUNG", "TIN DUNG", "BA CON DUNG", "NHAN HANG"])]
            o_luoi = (hit[0] if hit else len(cau_list) // 2, cell)

    dung, out, gan, loai_gan = set(), [], [], []
    for ci, (cau, giay) in enumerate(cau_list):
        if o_luoi and ci == o_luoi[0]:
            cell = o_luoi[1]
            g = min(giay, 3.5, *[(d["e"] - d["s"]) / speed for _, d in cell])
            out.append({"luoi": [(k, d["s"], round(g * speed, 2)) for k, d in cell]})
            giay -= g
        l = loai_cau(cau)
        con = giay
        while con > 0.3:
            thu_tu = [l] + [x for x in ("san_pham", "ket_qua", "su_dung") if x != l]
            if loai_gan[-3:] == [l, l, l]:  # 3 cảnh cùng loại liền nhau (vd toàn ruộng) -> chen 1 cảnh khác
                thu_tu = thu_tu[1:] + thu_tu[:1]
            pick = None
            for tranh in (gan[-4:], gan[-1:]):  # ưu tiên không trùng 4 video gần nhất, hết thì chỉ tránh liền kề
                for ll in thu_tu:
                    for k, d in kho.get(ll, []):
                        if (k, d["s"]) not in dung and k not in tranh:
                            pick = (k, d, ll)
                            break
                    if pick:
                        break
                if pick:
                    break
            if not pick:
                return out  # hết cảnh -> capcut_draft tự lặp lại
            k, d, ll = pick
            dung.add((k, d["s"]))
            gan.append(k)
            loai_gan.append(ll)
            lay = min(d["e"] - d["s"], max(DOAN_MIN, con * speed + 0.2))
            out.append((k, d["s"], round(lay, 2), y_doan(d)))
            con -= lay / speed
    return out
