"""Phong cách edit "Sơn 01" (anh Sơn tạo): video tự quay nói tự do -> tool tự cắt + dựng dự án CapCut.

Quy trình (tools/son01.py): nghe (Whisper, từng chữ) -> cắt thô (bỏ lặng, ờ à, câu nói lại) -> AI lên kế hoạch
(mở đầu / vấn đề / giải pháp / cách dùng / kêu gọi, từ khoá, zoom, cảnh minh hoạ) -> dự án CapCut theo khuôn của
anh Sơn (zoom lò xo, phụ đề trên đầu, từ khoá vàng, khung viền sáng, SFX khớp nhịp cắt, nhạc nền) -> xem trước MP4
(bộ dựng render/) -> AI chấm 10 tiêu chí, dưới mức đạt thì sửa và dựng lại.

Dữ liệu: data/son01/{goi (gói phong cách đã cài), thu_vien (thư viện cảnh minh hoạ), viec (từng video)}.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from core.config import BASE_DIR, DATA_DIR

from . import goi

DATA = DATA_DIR / "son01"
TOOLS = Path(__file__).resolve().parent / "tools"
THU_VIEN = DATA / "thu_vien"
VIEC = DATA / "viec"
TAT_CA = THU_VIEN / "tat_ca.json"
_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def env() -> dict:
    e = dict(os.environ)
    try:
        import imageio_ffmpeg
        e.setdefault("SONIX_FFMPEG", imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        pass
    e.update({"SONIX_APP": str(BASE_DIR), "SONIX_KHUON": str(goi.thu_muc_goi()), "SONIX_DATA": str(DATA),
              "SONIX_RENDER": str(BASE_DIR / "render"), "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
    return e


def _chay(script, args, log=print):
    """Chạy 1 công cụ trong tools/ (tiến trình riêng), chuyển từng dòng ra nhật ký. Lỗi -> RuntimeError."""
    cmd = [sys.executable, "-I", str(TOOLS / script), *[str(a) for a in args]]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env(), cwd=str(BASE_DIR),
                         creationflags=_NO_WINDOW, text=True, encoding="utf-8", errors="replace")
    cuoi = []
    for line in p.stdout:
        line = line.rstrip()
        if not line:
            continue
        cuoi = (cuoi + [line])[-15:]
        log(line)
    if p.wait() != 0:
        raise RuntimeError(f"{script} lỗi: " + " | ".join(cuoi[-3:]))


def ma_sp(sp_key: str) -> str:
    """Khoá sản phẩm app (dam_ca) -> nhãn thư viện cảnh (sp_dam_ca)."""
    return "sp_" + sp_key


# ------------------------------------------------------------------ thư viện cảnh minh hoạ
def ds_thu_vien() -> list:
    """[{ten, so_canh, dung_duoc}] các thư viện đã lập."""
    out = []
    for d in sorted(THU_VIEN.iterdir()) if THU_VIEN.is_dir() else []:
        f = d / "canh.json"
        if d.is_dir() and f.exists():
            try:
                c = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            out.append({"ten": d.name, "so_canh": len(c), "dung_duoc": sum("loai" not in x.get("nhan", []) for x in c),
                        "da_gan_nhan": sum(bool(x.get("nhan")) for x in c)})
    return out


def _ten_tv(thu_muc: Path) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", thu_muc.name)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn").replace("đ", "d").replace("Đ", "D")
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_") or "thu_vien"


def gop_thu_vien(log=print):
    libs = [str(THU_VIEN / x["ten"]) for x in ds_thu_vien()]
    if libs:
        _chay("gop_thu_vien.py", [TAT_CA, *libs], log)


def lap_thu_vien(thu_muc, S=None, log=print):
    """Tách cảnh mọi video trong thư mục -> AI gắn nhãn (mô phỏng rễ, ra đọt, pha thuốc...) -> soi chữ sản phẩm."""
    thu_muc = Path(thu_muc)
    if not thu_muc.is_dir():
        raise RuntimeError(f"Không thấy thư mục {thu_muc}")
    out = THU_VIEN / _ten_tv(thu_muc)
    out.mkdir(parents=True, exist_ok=True)
    log(f"Thư viện '{out.name}' từ {thu_muc}")
    log("1/3 Tách cảnh...")
    _chay("thu_vien.py", [thu_muc, out, "--nguong", "45", "--min", "1.2"], log)
    log("2/3 AI gắn nhãn cảnh...")
    _chay("gan_nhan.py", [out, "--model", "claude-sonnet-5-5"], log)
    log("3/3 Soi chữ trên bao bì (chặn sản phẩm khác hãng)...")
    _chay("kiem_sp.py", [out / "canh.json"], log)
    gop_thu_vien(log)
    log(f"Xong thư viện '{out.name}'")


# ------------------------------------------------------------------ dựng
def dung(video, sp_key, S, ten="", vong=3, dat=8.0, dai=36, log=print) -> dict:
    """Dựng 1 video quay thô theo phong cách Sơn 01. Trả về ket_qua.json."""
    from core.san_pham import SAN_PHAM
    if not goi.thong_tin():
        log("Máy này chưa có gói phong cách Sơn 01 -> tải về và cài...")
        log(goi.cai_dat(log=log))
    video = Path(video)
    if not video.exists():
        raise RuntimeError(f"Không thấy video {video}")
    sp = SAN_PHAM.get(sp_key, {})
    ten_sp = sp.get("ten", sp_key)
    ten = ten or f"SONIX SƠN 01 - {ten_sp.upper()}"
    work = VIEC / video.stem  # giữ lời đã nghe (loi.json, cat.json) -> dựng lại không phải nghe lại
    args = [video, "--sp", ma_sp(sp_key), "--san-pham", f"{ten_sp} ({sp.get('quy_cach', '')})".replace(" ()", ""),
            "--ten", ten, "--lam-viec", work, "--vong", int(vong), "--dat", float(dat), "--dai", int(dai)]
    if TAT_CA.exists():
        args += ["--thu-vien", TAT_CA]
    else:
        log("Chưa có thư viện cảnh minh hoạ -> video sẽ không chèn cảnh minh hoạ (lập thư viện ở mục 2).")
    _chay("son01.py", args, log)
    kq = json.loads((work / "ket_qua.json").read_text(encoding="utf-8"))
    kq["lam_viec"] = str(work)
    (work / "ket_qua.json").write_text(json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
    return kq


def ket_qua_gan_day(n=5) -> list:
    out = []
    for f in sorted(VIEC.glob("*/ket_qua.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:n]:
        try:
            k = json.loads(f.read_text(encoding="utf-8"))
            k.setdefault("lam_viec", str(f.parent))
            k["luc"] = time.strftime("%d/%m %H:%M", time.localtime(f.stat().st_mtime))
            out.append(k)
        except Exception:
            pass
    return out
