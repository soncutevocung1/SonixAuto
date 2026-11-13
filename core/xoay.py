"""Quy trình "Xoay + minh hoạ": video tự quay xoay sản phẩm (SOURCE THÔ\\Xoay) + chèn vài đoạn cắt từ video aff
cùng sản phẩm (tua nhanh 2x, tắt tiếng) làm minh hoạ, rồi xuất thẳng mp4 1080p bằng ffmpeg (không cần CapCut).

- Âm thanh: giữ tiếng gốc video xoay (Sonix Up Video tự thêm âm thanh yêu thích khi đăng).
- Đoạn chèn: 4-5 đoạn x 2 giây, ~2/3 che hết khung, ~1/3 hiện khung nhỏ góc trên; không chèn 1,5 giây đầu
  (giữ cảnh sản phẩm làm mồi) và 2 giây cuối.
- Cảnh chèn lấy từ chỉ mục cảnh đã quét của sản phẩm (đã bỏ cảnh có người, chữ chèn, sản phẩm khác...),
  ưu tiên cảnh cách dùng / kết quả trên cây, mỗi đoạn 1 video khác nhau, không lặp lại trong cùng đợt.
- Sản phẩm của video xoay: tên file -> chữ trên nhãn -> AI (core/loc_sp.py), nhớ trong data/edit/xoay.json.
"""
import json
import random
import subprocess
import sys
import time
from pathlib import Path

from .config import DATA_DIR, VIDEO_EXTS
from .video_utils import _ffmpeg, probe

FILE = DATA_DIR / "edit" / "xoay.json"
TOC = 2.0          # tua nhanh đoạn chèn
DAI_CHEN = 2.0     # giây mỗi đoạn chèn trên video
_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def _doc() -> dict:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"sp": {}, "da_lam": {}}


def _ghi(d: dict):
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def ds_video(thu_muc: Path) -> list:
    return sorted(p for p in Path(thu_muc).rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTS)


def san_pham_cua(f: Path, S: dict, log=print) -> str:
    """Mã sản phẩm của video xoay ('' nếu không nhận ra)."""
    from . import loc_sp
    d = _doc()
    k = str(f)
    if k not in d["sp"]:
        sp, why = loc_sp.nhan_dien(Path(f), S)
        d["sp"][k] = sp if sp != "can_xem" else ""
        _ghi(d)
        log(f"   {Path(f).name}: {sp} ({why})")
    return d["sp"][k]


def chon_chen(sp: str, n: int, dung: set, seed=None) -> list:
    """n đoạn chèn [(path, giây bắt đầu, số giây trên video)] từ cảnh đã quét của sản phẩm."""
    from . import canh
    rnd = random.Random(seed)
    idx = canh.doc_index(sp)
    kho = {"ket_qua": [], "su_dung": [], "san_pham": []}
    can = 3.0  # đoạn nguồn tối thiểu (giây gốc); chèn = min(2 giây, đoạn nguồn / 2x)
    for k, v in idx.items():
        if not Path(k).exists():
            continue
        for d in v["doan"]:
            l = d.get("loai") or ("san_pham" if d.get("sp") else "ket_qua")
            if canh.dung_duoc(d) and l in kho and d["e"] - d["s"] >= can and (k, d["s"]) not in dung:
                kho[l].append((k, d["s"], round(min(DAI_CHEN, (d["e"] - d["s"] - 0.1) / TOC), 2)))
    for l in kho:
        rnd.shuffle(kho[l])
    # xen kẽ: kết quả, cách dùng, kết quả, sản phẩm, ... ; mỗi đoạn 1 video khác nhau
    thu_tu = ["ket_qua", "su_dung", "ket_qua", "san_pham", "su_dung", "ket_qua", "san_pham"]
    out, da_video = [], set()
    i = 0
    while len(out) < n and any(kho.values()) and i < 200:
        l = thu_tu[i % len(thu_tu)]
        i += 1
        for j, (k, s, g) in enumerate(kho[l]):
            if k not in da_video:
                out.append((k, s, g))
                da_video.add(k)
                dung.add((k, s))
                kho[l].pop(j)
                break
    return out


def vi_tri(dur: float, n: int) -> list:
    """Thời điểm bắt đầu các đoạn chèn, rải đều, chừa 1,5 giây đầu và 2 giây cuối."""
    a, b = 1.5, max(1.5 + n * (DAI_CHEN + 1), dur - 2.0 - DAI_CHEN)
    if n == 1:
        return [round((a + b) / 2, 2)]
    return [round(a + (b - a) * i / (n - 1), 2) for i in range(n)]


def dung_video(src: Path, chen: list, out: Path, seed=None) -> Path:
    """Dựng 1 video: video xoay 1080x1920 + các đoạn chèn (2x, tắt tiếng), giữ tiếng gốc."""
    rnd = random.Random(seed)
    dur = probe(str(src))["duration"]
    pos = vi_tri(dur, len(chen))
    # khoảng 2/3 che hết khung, 1/3 khung nhỏ; không để 2 khung nhỏ liền nhau
    kieu = []
    for i in range(len(chen)):
        nho = rnd.random() < 0.34 and (not kieu or kieu[-1] != "nho")
        kieu.append("nho" if nho else "full")
    if "nho" not in kieu and len(chen) >= 3:
        kieu[len(chen) // 2] = "nho"
    args = [_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(src)]
    for p, s, g in chen:
        args += ["-ss", f"{s:.2f}", "-t", f"{g * TOC + 0.2:.2f}", "-an", "-i", str(p)]
    fl = ["[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30[b0]"]
    for i, ((p, s, g), a, k) in enumerate(zip(chen, pos, kieu), 1):
        base = (f"[{i}:v]setpts=(PTS-STARTPTS)/{TOC},fps=30,trim=duration={g},setpts=PTS-STARTPTS+{a}/TB,"
                "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1")
        if k == "nho":
            fl.append(base + ",scale=470:-2,pad=iw+12:ih+12:6:6:white" + f"[c{i}]")
            xy = "x=W-w-40:y=150"
        else:
            fl.append(base + f"[c{i}]")
            xy = "x=0:y=0"
        fl.append(f"[b{i - 1}][c{i}]overlay={xy}:eof_action=pass:enable='between(t,{a},{a + g})'[b{i}]")
    out.parent.mkdir(parents=True, exist_ok=True)
    args += ["-filter_complex", ";".join(fl), "-map", f"[b{len(chen)}]", "-map", "0:a?",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-t", f"{dur:.2f}", str(out)]
    r = subprocess.run(args, capture_output=True, text=True, errors="ignore", creationflags=_NO_WINDOW)
    if r.returncode != 0 or not out.exists():
        raise RuntimeError("ffmpeg lỗi: " + (r.stderr or "")[-400:])
    return out


def lam(S: dict, files: list, kenh: str, so_chen: int = 0, log=print) -> list:
    """Dựng lần lượt các video xoay, đưa vào CHƯA UP\\<ngày>\\NN.mp4 của kênh. Trả về danh sách file đã đưa vào."""
    from .xuat_capcut import dua_vao_kenh
    root = S.get("root_folder") or ""
    if not root or not kenh:
        raise ValueError("Chưa chọn kênh / thư mục Sonix Up Video")
    tmp_dir = DATA_DIR / "edit" / "xoay_tam"
    d = _doc()
    dung, out = set(), []
    for i, f in enumerate(files, 1):
        f = Path(f)
        log(f"[{i}/{len(files)}] {f.name}")
        try:
            sp = san_pham_cua(f, S, log)
            if not sp:
                log("   bỏ qua: không nhận ra sản phẩm")
                continue
            n = so_chen or (5 if probe(str(f))["duration"] >= 30 else 4)
            chen = chon_chen(sp, n, dung, seed=int(time.time()) + i)
            if len(chen) < 2:
                log(f"   bỏ qua: sản phẩm {sp} chưa có đủ cảnh đã quét (bấm Quét cảnh)")
                continue
            tmp = dung_video(f, chen, tmp_dir / f"{f.stem}_{int(time.time())}.mp4", seed=i)
            dst = dua_vao_kenh(tmp, root, kenh)
            d = _doc()
            d["da_lam"][str(f)] = {"luc": time.strftime("%d/%m/%Y %H:%M"), "ra": str(dst), "sp": sp}
            _ghi(d)
            out.append(dst)
            log(f"   {sp}, chèn {len(chen)} đoạn -> {dst}")
        except Exception as e:
            log(f"   lỗi: {e}")
    log(f"Xong {len(out)}/{len(files)} video vào {kenh}")
    return out


def da_lam() -> dict:
    return _doc().get("da_lam", {})
