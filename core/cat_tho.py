"""Quay thô tự cắt phần thừa (phóng sự cưới, sự kiện...) -> dự án CapCut "<tên> CẮT THÔ".

Cách dùng: bác nhập toàn bộ clip thô vào 1 dự án CapCut (như bình thường), TẮT CapCut, rồi chạy quy trình này.
Tool đọc dự án đó, phân tích từng clip rồi tạo dự án MỚI (dự án gốc giữ nguyên):
  - Cắt bỏ: rung lắc mạnh, mất nét, tối đen, máy chĩa xuống đất / đang mang đi ở đầu - cuối clip,
    đoạn đứng yên lâu không có người (máy để quên), clip quá ngắn (bấm nhầm).
  - Bảo vệ: khung có MẶT NGƯỜI hoặc có TIẾNG NÓI (phát biểu, MC, phỏng vấn) -> giữ trọn, chỉ cắt khi hỏng nặng và lâu.
  - Giữ đúng thứ tự, giữ tiếng gốc, mỗi phần lễ có nhãn chữ ở lớp riêng (xoá 1 lớp là hết nhãn).
Mức 'an_toan': chỉ cắt chỗ chắc chắn hỏng (thà giữ thừa còn hơn mất cảnh). Mức 'manh': ngưỡng chặt hơn.

python -m core.edit_job quay_tho <tên> <file cấu hình .json>
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from core.config import DATA_DIR

FPS_PT = 10            # số khung phân tích mỗi giây
W_DOC, H_DOC = 640, 360  # khung đọc (dò mặt)
W_PT, H_PT = 320, 180  # khung phân tích rung / nét / sáng
MAT_MOI = 5            # dò mặt mỗi 5 khung (2 lần / giây)
SR = 16000             # tần số âm thanh phân tích
BUOC = 1.0 / FPS_PT    # 0.1 giây
PHIEN_BAN = "v2"
CACHE = DATA_DIR / "edit" / "cat_tho" / "cache"
KQ_DIR = DATA_DIR / "edit" / "cat_tho"
_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

MUC = {
    # ngưỡng (đơn vị: khung 320x180, mỗi bước 0.1 giây, độ sáng 0-255)
    "an_toan": dict(toi=22, mo_ti_le=0.30, rung=10.0, rung_min=1.0, bv_hong=2.5, cho_min=10.0, cho_giu=2.5,
                    cho_noi=8.0, mang_min=2.0, dau_max=6.0, doan_min=0.8, clip_min=1.0, lien=0.5),
    "manh": dict(toi=28, mo_ti_le=0.38, rung=7.0, rung_min=0.6, bv_hong=1.5, cho_min=6.0, cho_giu=2.0,
                 cho_noi=6.0, mang_min=1.5, dau_max=8.0, doan_min=1.0, clip_min=1.5, lien=0.4),
}
LY_DO = {"toi": "tối đen", "mo": "mất nét", "rung": "rung lắc", "dau": "đầu clip (bật máy / chĩa đất)",
         "cuoi": "cuối clip (tắt máy / chĩa đất)", "cho": "đứng yên lâu / máy để quên", "ngan": "đoạn vụn quá ngắn",
         "mang": "đang mang máy đi (không có người)",
         "clip": "clip quá ngắn / hỏng"}


# ----------------------------------------------------------------------------- ffmpeg + dò mặt
def _ff() -> str:
    return shutil.which("ffmpeg") or __import__("core.video_utils", fromlist=["_ffmpeg"])._ffmpeg()


_TL = threading.local()


def _do_mat():
    """Bộ dò mặt MediaPipe (dùng chung model với Quét cảnh), mỗi luồng 1 bộ."""
    if getattr(_TL, "det", None) is None:
        from core.canh import FACE_MODEL, _face
        _face()  # tải model nếu chưa có
        from mediapipe.tasks.python import BaseOptions, vision
        _TL.det = vision.FaceDetector.create_from_options(vision.FaceDetectorOptions(
            base_options=BaseOptions(model_asset_path=str(FACE_MODEL)), min_detection_confidence=0.5))
    return _TL.det


def _dem_mat(bgr) -> int:
    """Số mặt người: dò trên cả khung + vùng giữa phóng to (bắt mặt ở xa)."""
    import cv2
    import mediapipe as mp
    det = _do_mat()
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    n = len(det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))).detections)
    if n:
        return n
    for x0 in (0, w // 4, w // 2):  # 3 ô 1/2 khung ngang, nửa trên-giữa (mặt thường ở đây)
        crop = rgb[h // 8: h // 8 + h // 2, x0: x0 + w // 2]
        crop = cv2.resize(crop, (w, h), interpolation=cv2.INTER_LINEAR)
        n += len(det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(crop))).detections)
    return n


def _mo_luong(path: str, cuda: bool):
    vf = (f"scale_cuda={W_DOC}:{H_DOC},hwdownload,format=nv12,fps={FPS_PT},format=bgr24" if cuda
          else f"fps={FPS_PT},scale={W_DOC}:{H_DOC},format=bgr24")
    pre = ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"] if cuda else ["-threads", "4"]
    return subprocess.Popen([_ff(), "-hide_banner", "-loglevel", "error", *pre, "-i", path, "-an", "-vf", vf,
                             "-f", "rawvideo", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            creationflags=_NO_WINDOW)


def _dac_trung_hinh(path: str) -> dict:
    import cv2
    sz = W_DOC * H_DOC * 3
    win = cv2.createHanningWindow((W_PT, H_PT), cv2.CV_32F)
    for cuda in (True, False):
        p = _mo_luong(path, cuda)
        out = {k: [] for k in ("sang", "net", "dx", "dy", "tin", "khac", "mat")}
        prev, i = None, 0
        while True:
            buf = p.stdout.read(sz)
            if len(buf) < sz:
                break
            bgr = np.frombuffer(buf, np.uint8).reshape(H_DOC, W_DOC, 3)
            g8 = cv2.cvtColor(cv2.resize(bgr, (W_PT, H_PT), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
            g = g8.astype(np.float32)
            out["sang"].append(float(g.mean()))
            lap = np.abs(cv2.Laplacian(g8, cv2.CV_32F))
            out["net"].append(float(np.percentile(lap, 99.5)))
            if prev is not None:
                (x, y), r = cv2.phaseCorrelate(prev, g, win)
                out["dx"].append(x)
                out["dy"].append(y)
                out["tin"].append(r)
                out["khac"].append(float(np.abs(g - prev).mean()))
            else:
                for k in ("dx", "dy", "tin", "khac"):
                    out[k].append(0.0)
            out["mat"].append(_dem_mat(bgr) if i % MAT_MOI == 0 else -1)
            prev, i = g, i + 1
        p.wait()
        if i:
            d = {k: np.array(v, np.float32) for k, v in out.items()}
            # điền số mặt cho các khung không dò (giữ giá trị lần dò gần nhất)
            m = d["mat"]
            last = 0.0
            for j in range(len(m)):
                if m[j] >= 0:
                    last = m[j]
                else:
                    m[j] = last
            return d
    raise RuntimeError("không đọc được hình")


def _doc_tieng(path: str):
    p = subprocess.run([_ff(), "-hide_banner", "-loglevel", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR),
                        "-f", "s16le", "-"], capture_output=True, creationflags=_NO_WINDOW)
    return np.frombuffer(p.stdout, np.int16).astype(np.float32) / 32768.0


def _dac_trung_tieng(a, n):
    """Độ to (dB) và tỉ lệ năng lượng dải giọng người (300-3400 Hz) cho từng khung 0.1 giây."""
    L = int(SR * BUOC)
    db = np.full(n, -90.0, np.float32)
    giong = np.zeros(n, np.float32)
    if a.size < L:
        return db, giong
    m = min(n, a.size // L)
    blk = a[: m * L].reshape(m, L)
    rms = np.sqrt((blk ** 2).mean(1) + 1e-12)
    db[:m] = 20 * np.log10(rms)
    spec = np.abs(np.fft.rfft(blk * np.hanning(L), axis=1)) ** 2
    f = np.fft.rfftfreq(L, 1 / SR)
    band = (f >= 300) & (f <= 3400)
    giong[:m] = spec[:, band].sum(1) / (spec.sum(1) + 1e-12)
    return db, giong


def _khoa_cache(path: str) -> Path:
    st = os.stat(path)
    return CACHE / (Path(path).stem + f"_{st.st_size}_{int(st.st_mtime)}_{PHIEN_BAN}.npz")


def phan_tich(path: str) -> dict:
    """Đặc trưng của 1 clip (có lưu đệm, chạy lại không phân tích lại)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    k = _khoa_cache(path)
    if k.exists():
        z = np.load(k)
        return {x: z[x] for x in z.files}
    d = _dac_trung_hinh(path)
    d["db"], d["giong"] = _dac_trung_tieng(_doc_tieng(path), len(d["sang"]))
    np.savez_compressed(k, **d)
    return d


# ----------------------------------------------------------------------------- quyết định cắt
def _doan(mask):
    """Các đoạn liên tiếp True -> [(i0, i1)) theo chỉ số khung."""
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def _loc_ngan(mask, toi_thieu):
    m = np.zeros_like(mask)
    for a, b in _doan(mask):
        if (b - a) * BUOC >= toi_thieu:
            m[a:b] = True
    return m


def _gian(mask, k):
    if k <= 0:
        return mask
    m = mask.copy()
    for a, b in _doan(mask):
        m[max(0, a - k):b + k] = True
    return m


def _trung_vi(x, k):
    from numpy.lib.stride_tricks import sliding_window_view
    p = np.pad(x, (k // 2, k // 2), mode="edge")
    return np.median(sliding_window_view(p, k), axis=1)


def quyet_dinh(f: dict, muc: str = "an_toan", tong_net=None) -> dict:
    """Trả về {'giu': [(giây đầu, giây cuối)], 'bo': [(đầu, cuối, lý do)], 'noi', 'mat'}."""
    c = MUC[muc]
    n = len(f["sang"])
    dur = n * BUOC
    if dur < c["clip_min"]:
        z = np.zeros(n, bool)
        return {"giu": [], "bo": [(0, dur, "clip")], "noi": z, "mat": z}
    # lời nói: to hơn nền >= 9 dB, đủ to, nhiều năng lượng dải giọng -> giãn 0.6 giây hai bên
    db = f["db"]
    nen = np.percentile(db, 10)
    noi = (db > nen + 9) & (db > -45) & (f["giong"] > 0.45)
    noi = _gian(_loc_ngan(noi, 0.3), 6)
    # mặt người: chỉ tin khi thấy ở 2 lần dò liền nhau (bỏ báo nhầm lẻ tẻ), giãn 1 giây hai bên
    m0 = f["mat"] > 0
    m_truoc = np.concatenate([np.zeros(MAT_MOI, bool), m0[:-MAT_MOI]]) if n > MAT_MOI else np.zeros(n, bool)
    m_sau = np.concatenate([m0[MAT_MOI:], np.zeros(MAT_MOI, bool)]) if n > MAT_MOI else np.zeros(n, bool)
    mat = _gian(m0 & (m_truoc | m_sau), 10)
    bv = noi | mat
    # tối
    toi = _loc_ngan(f["sang"] < c["toi"], 0.5)
    # mất nét: cạnh sắc nhất trong khung yếu hẳn so với lúc nét nhất của clip (và của cả buổi)
    tot = np.percentile(f["net"], 85)
    if tong_net is not None:
        tot = max(tot * 0.6, min(tot, tong_net))
    mo = _loc_ngan(f["net"] < c["mo_ti_le"] * tot, 0.8)
    # rung: chuyển động giật (lệch khỏi chuyển động mượt 1 giây) mà phép đo tin cậy, hoặc lia quá gắt
    v = np.hypot(f["dx"], f["dy"])
    tin = f["tin"] > 0.08
    jit = np.hypot(f["dx"] - _trung_vi(f["dx"], 9), f["dy"] - _trung_vi(f["dy"], 9)) * tin
    jit = np.convolve(jit, np.ones(5) / 5, mode="same")
    rung = _loc_ngan((jit > c["rung"]) | ((v > 60) & tin), c["rung_min"])
    ly = np.array([""] * n, dtype=object)
    ly[mo] = "mo"
    ly[rung] = "rung"
    ly[toi] = "toi"
    # hỏng: chỗ không có người / lời -> cắt; chỗ có người / lời -> chỉ cắt khi hỏng nặng và lâu (rung, tối)
    bo = (mo | rung | toi) & ~bv
    bo |= _loc_ngan((rung | toi) & bv, c["bv_hong"])
    # đang mang máy đi (lia gắt, chuyển động lộn xộn) mà không thấy người -> cắt, kể cả có tiếng (micro cài áo vẫn thu)
    tb = np.ones(20) / 20
    v_tb = np.convolve(v, tb, mode="same")
    tin_tb = np.convolve(f["tin"], tb, mode="same")
    jit_tb = np.convolve(jit, tb, mode="same")
    mang = _loc_ngan((((v_tb > 8) & (tin_tb < 0.65)) | (jit_tb > 4)) & ~mat, c["mang_min"])
    ly[mang & (ly == "")] = "mang"
    bo |= mang
    # đứng yên lâu (so với mức nhiễu riêng của clip): không có lời -> giữ đầu + cuối;
    # có lời mà không thấy người -> máy để quên, cắt nếu đủ lâu
    yen = (f["khac"] < np.percentile(f["khac"], 10) + 1.0) & (np.convolve(v, np.ones(10) / 10, mode="same") < 1.5)
    cho = np.zeros(n, bool)
    for a, b in _doan(_loc_ngan(yen & ~noi, c["cho_min"])) + _doan(_loc_ngan(yen & noi & ~mat, c["cho_noi"])):
        cho[a + int(c["cho_giu"] / BUOC): b - int(1.0 / BUOC)] = True
    ly[cho & (ly == "")] = "cho"
    bo |= cho
    # đầu / cuối clip: máy đang đưa lên / hạ xuống (không có người, đang lia, giật hoặc hỏng), tối đa dau_max giây
    xau = (mo | rung | toi | (v > 8) | (jit > 3)) & ~mat
    k = int(c["dau_max"] / BUOC)

    def _cat_dau(idx, nhan):
        """idx: chỉ số khung tính từ mép clip vào trong. Cắt liền từ mép tới khung xấu cuối cùng trước khi thấy người,
        nếu phần lớn đoạn đó xấu (máy đang đưa lên / chĩa đất); không thì chỉ cắt các khung xấu sát mép."""
        lim = next((t for t, x in enumerate(idx[:k]) if mat[x]), min(k, len(idx)))
        cuoi = max((t for t in range(lim) if xau[idx[t]]), default=-1)
        if cuoi >= 0 and np.mean([xau[idx[t]] for t in range(cuoi + 1)]) >= 0.6:
            hl = cuoi + 1
        else:
            hl = 0
            while hl < lim and xau[idx[hl]]:
                hl += 1
        for t in range(hl):
            bo[idx[t]], ly[idx[t]] = True, nhan

    _cat_dau(list(range(n)), "dau")
    _cat_dau(list(range(n - 1, -1, -1)), "cuoi")
    for idx in (0, 1, n - 1, n - 2):  # 0.2 giây bấm máy
        if 0 <= idx < n and not noi[idx]:
            bo[idx] = True
            ly[idx] = ly[idx] or ("dau" if idx < 2 else "cuoi")
    giu = ~bo
    # lấp lỗ cắt quá ngắn giữa 2 đoạn giữ, bỏ đoạn giữ quá vụn (trừ khi có lời / người)
    lien = int(c["lien"] / BUOC)
    for a, b in _doan(bo):
        if 0 < a and b < n and (b - a) <= lien:
            giu[a:b] = True
    for a, b in _doan(giu):
        if (b - a) * BUOC < c["doan_min"] and not bv[a:b].any():
            giu[a:b] = False
            ly[a:b] = [x or "ngan" for x in ly[a:b]]
    out_bo = []
    for a, b in _doan(~giu):
        vals = [x for x in ly[a:b] if x]
        out_bo.append((a * BUOC, b * BUOC, max(set(vals), key=vals.count) if vals else "ngan"))
    return {"giu": [(a * BUOC, b * BUOC) for a, b in _doan(giu)], "bo": out_bo, "noi": noi, "mat": mat}


# ----------------------------------------------------------------------------- dự án CapCut
def _clip_cua_du_an(ten: str) -> list:
    """Các đoạn trên lớp video chính của dự án theo thứ tự: [{'path','src0','src_dur','seg'}]."""
    from core.capcut_draft import CAPCUT_DRAFTS
    d = json.loads((CAPCUT_DRAFTS / ten / "draft_content.json").read_text(encoding="utf-8"))
    mats = {m["id"]: m for m in d["materials"].get("videos", [])}
    main = next(t for t in d["tracks"] if t["type"] == "video" and t["segments"])
    out = []
    for s in sorted(main["segments"], key=lambda s: s["target_timerange"]["start"]):
        m = mats.get(s["material_id"])
        if not m or m.get("type") != "video":
            continue
        src = s.get("source_timerange") or {"start": 0, "duration": s["target_timerange"]["duration"]}
        out.append({"path": m["path"], "src0": src["start"] / 1e6, "src_dur": src["duration"] / 1e6})
    return out


def chia_phan(clips: list, ranh_gioi=None, khoang_phut: float = 9.0) -> list:
    """Gán tên phần cho từng clip. ranh_gioi = [(tên file đầu phần, tên phần)]; không có thì tự chia theo giờ quay
    (cách nhau > khoang_phut phút là phần mới)."""
    ten = []
    if ranh_gioi:
        bd = {Path(a).stem.upper(): b for a, b in ranh_gioi}
        cur = ""
        for c in clips:
            cur = bd.get(Path(c["path"]).stem.upper(), cur)
            ten.append(cur)
        return ten
    prev, k = None, 0
    for c in clips:
        try:
            t = os.path.getmtime(c["path"])
        except OSError:
            t = prev or 0
        if prev is None or t - prev > khoang_phut * 60:
            k += 1
            cur = f"Phần {k} · {time.strftime('%H:%M', time.localtime(t))}"
        ten.append(cur)
        prev = t
    return ten


def _nhan_tu_mau(d: dict, chu: str, start_us: int, dur_us: int, mau: dict, seg_mau: dict):
    """Thêm 1 nhãn chữ (chép kiểu chữ từ dự án 'mẫu' của Sonix) vào d. Trả về đoạn chữ."""
    from core.capcut_draft import _nfc, _uid
    mm = d["materials"]
    tmat = copy.deepcopy(next(t for t in mau["materials"]["texts"] if t["id"] == seg_mau["material_id"]))
    tmat["id"] = _uid()
    c = json.loads(tmat["content"])
    chu = _nfc(chu)
    st = copy.deepcopy(c["styles"][0])
    st["range"] = [0, len(chu)]
    try:
        st["fill"]["content"]["solid"]["color"] = [1.0, 1.0, 1.0]
        st["size"] = 7.0
    except (KeyError, TypeError):
        pass
    c["text"], c["styles"] = chu, [st]
    tmat["content"] = json.dumps(c, ensure_ascii=False)
    for k in ("words", "current_words"):
        if k in tmat:
            tmat[k] = {"start_time": [], "end_time": [], "text": []}
    mm.setdefault("texts", []).append(tmat)
    s = copy.deepcopy(seg_mau)
    s["id"] = _uid()
    s["material_id"] = tmat["id"]
    refs = []
    for r in seg_mau.get("extra_material_refs", []):
        for k, v in mau["materials"].items():
            if isinstance(v, list):
                x = next((x for x in v if isinstance(x, dict) and x.get("id") == r), None)
                if x is not None:
                    n = copy.deepcopy(x)
                    n["id"] = _uid()
                    mm.setdefault(k, []).append(n)
                    refs.append(n["id"])
                    break
    s["extra_material_refs"] = refs
    s["target_timerange"] = {"start": int(start_us), "duration": int(dur_us)}
    if s.get("source_timerange") is not None:
        s["source_timerange"] = None
    s.setdefault("clip", {})
    s["clip"]["scale"] = {"x": 1.0, "y": 1.0}
    s["clip"]["transform"] = {"x": -0.62, "y": 0.80}
    s["common_keyframes"] = []
    s["keyframe_refs"] = []
    return s


def tao_du_an(nguon: str, ket_qua: list, ten_moi: str, log=print) -> dict:
    """ket_qua: [{'path', 'giu': [(giây đầu, giây cuối) tính trong clip gốc], 'phan'}] theo thứ tự.
    Chép dự án nguồn -> sửa lớp video chính thành các đoạn giữ lại + lớp nhãn phần."""
    from core.capcut_draft import (CAPCUT_DRAFTS, CapCutError, _Draft, _copy_tree, _needed_media, _uid, _us,
                                   _fwd, capcut_dang_mo, danh_sach_du_an)
    if capcut_dang_mo():
        raise CapCutError("CapCut đang mở. Bác tắt CapCut rồi chạy lại.")
    src = CAPCUT_DRAFTS / nguon
    d = json.loads((src / "draft_content.json").read_text(encoding="utf-8"))
    dr = _Draft(d)
    main = next(t for t in d["tracks"] if t["type"] == "video" and t["segments"])
    mats = {m["id"]: m for m in d["materials"]["videos"]}
    theo_path = {}
    for s in main["segments"]:
        m = mats.get(s["material_id"])
        if m:
            theo_path.setdefault(_fwd(m["path"]), s)
    segs, pos, nhan = [], 0, []
    phan_cu = None
    for kq in ket_qua:
        mau_seg = theo_path.get(_fwd(kq["path"]))
        if mau_seg is None or not kq["giu"]:
            continue
        if kq.get("phan") and kq["phan"] != phan_cu:
            nhan.append((kq["phan"], pos))
            phan_cu = kq["phan"]
        for a, b in kq["giu"]:
            dur = _us(b - a)
            if dur <= 0:
                continue
            s = dr.clone_seg(mau_seg)
            s["target_timerange"] = {"start": pos, "duration": dur}
            s["source_timerange"] = {"start": _us(a), "duration": dur}
            if s.get("render_timerange"):
                s["render_timerange"] = {"start": 0, "duration": 0}
            segs.append(s)
            pos += dur
    if not segs:
        raise CapCutError("Không còn đoạn nào để giữ")
    main["segments"] = segs
    # nhãn phần: lớp chữ riêng, mỗi nhãn 3 giây
    mau_p = CAPCUT_DRAFTS / "mẫu" / "draft_content.json"
    so_nhan = 0
    if nhan and mau_p.exists():
        try:
            mau = json.loads(mau_p.read_text(encoding="utf-8"))
            seg_mau = next(t["segments"][0] for t in mau["tracks"] if t["type"] == "text" and t["segments"])
            tt = {"attribute": 0, "flag": 0, "id": _uid(), "is_default_name": True, "name": "", "segments": [],
                  "type": "text"}
            for i, (ten, p0) in enumerate(nhan):
                p1 = nhan[i + 1][1] if i + 1 < len(nhan) else pos
                tt["segments"].append(_nhan_tu_mau(d, ten.upper(), p0, min(3 * 1_000_000, p1 - p0), mau, seg_mau))
            d["tracks"].append(tt)
            so_nhan = len(nhan)
        except Exception as e:  # thiếu khuôn chữ thì vẫn tạo dự án, chỉ không có nhãn
            log(f"Không thêm được nhãn phần ({e}) - dự án vẫn tạo bình thường")
    d["duration"] = pos
    dr.prune()

    # chép thư mục dự án + đăng ký vào danh sách CapCut (cùng cách capcut_draft.tao_du_an)
    base, n, name = ten_moi, 2, ten_moi
    while (CAPCUT_DRAFTS / name).exists() or name in danh_sach_du_an():
        name, n = f"{base} ({n})", n + 1
    dst = CAPCUT_DRAFTS / name
    content = json.dumps(d, ensure_ascii=False)
    _copy_tree(src, dst, _needed_media(d))
    try:
        targets = [dst / "draft_content.json"]
        tl = dst / "Timelines"
        if tl.exists():
            targets += list(tl.glob("*/draft_content.json"))
        for f in targets:
            f.write_text(content, encoding="utf-8")
            patch = f.parent / "attachment" / "patch" / "mini_draft.json"
            if patch.exists():
                os.remove(patch)
        now = int(time.time() * 1_000_000)
        new_id = _uid()
        reset = {"tm_draft_cloud_entry_id": -1, "tm_draft_cloud_parent_entry_id": -1, "tm_draft_cloud_space_id": -1,
                 "tm_draft_cloud_user_id": -1, "tm_draft_cloud_modified": 0, "tm_draft_cloud_completed": "",
                 "cloud_draft_sync": False, "draft_cloud_last_action_download": False}
        mp = dst / "draft_meta_info.json"
        meta = json.loads(mp.read_text(encoding="utf-8"))
        meta.update(reset)
        meta.update({"draft_id": new_id, "draft_name": name, "draft_fold_path": _fwd(dst),
                     "tm_draft_create": now, "tm_draft_modified": now, "tm_duration": pos})
        mp.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        rp = CAPCUT_DRAFTS / "root_meta_info.json"
        shutil.copy2(rp, CAPCUT_DRAFTS / "root_meta_info.json.sonix_backup")
        root = json.loads(rp.read_text(encoding="utf-8"))
        tmpl = next((e for e in root["all_draft_store"] if e.get("draft_name") == nguon), root["all_draft_store"][0])
        e = copy.deepcopy(tmpl)
        e.update(reset)
        e.update({"draft_id": new_id, "draft_name": name, "draft_fold_path": _fwd(dst),
                  "draft_json_file": _fwd(dst) + "\\draft_content.json",
                  "draft_cover": _fwd(dst) + "\\draft_cover.jpg",
                  "tm_draft_create": now, "tm_draft_modified": now, "tm_duration": pos})
        root["all_draft_store"].insert(0, e)
        tmp = rp.with_suffix(".json.sonix_tmp")
        tmp.write_text(json.dumps(root, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, rp)
    except Exception:
        shutil.rmtree(dst, ignore_errors=True)
        raise
    return {"name": name, "path": str(dst), "duration": pos / 1e6, "so_nhan": so_nhan, "so_doan": len(segs)}


# ----------------------------------------------------------------------------- chạy cả quy trình
def _fmt(s: float) -> str:
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


def lam(S, cfg: dict, log=print) -> dict:
    """cfg = {'du_an': tên dự án CapCut nguồn, 'muc': 'an_toan'|'manh', 'ranh_gioi': [[file, tên phần]],
              'ten_moi': tên dự án mới (mặc định '<nguồn> CẮT THÔ'), 'luong': số luồng phân tích (2)}"""
    nguon = cfg["du_an"]
    muc = cfg.get("muc") or "an_toan"
    clips = _clip_cua_du_an(nguon)
    if not clips:
        raise RuntimeError(f"Dự án '{nguon}' không có clip video")
    paths = list(dict.fromkeys(c["path"] for c in clips))
    log(f"Dự án '{nguon}': {len(clips)} đoạn, {len(paths)} file. Phân tích hình + tiếng (có đệm, chạy lại nhanh)...")
    feats, xong, t0 = {}, [0], time.time()

    def _one(p):
        try:
            feats[p] = phan_tich(p)
        except Exception as e:
            feats[p] = None
            log(f"  Lỗi đọc {Path(p).name}: {e}")
        xong[0] += 1
        if xong[0] % 10 == 0 or xong[0] == len(paths):
            log(f"  Đã phân tích {xong[0]}/{len(paths)} file ({time.time() - t0:.0f} giây)")

    with ThreadPoolExecutor(max(1, int(cfg.get("luong") or 2))) as ex:
        list(ex.map(_one, paths))
    nets = [np.percentile(f["net"], 85) for f in feats.values() if f is not None and len(f["net"])]
    tong_net = float(np.median(nets)) if nets else None
    phan = chia_phan(clips, cfg.get("ranh_gioi"))
    ket_qua, bao_cao = [], []
    tong_goc = tong_giu = 0.0
    for c, ph in zip(clips, phan):
        f = feats.get(c["path"])
        if f is None:
            ket_qua.append({"path": c["path"], "giu": [(c["src0"], c["src0"] + c["src_dur"])], "phan": ph})
            continue
        q = quyet_dinh(f, muc, tong_net)
        lo, hi = c["src0"], c["src0"] + c["src_dur"]   # tôn trọng chỗ bác đã cắt sẵn trong CapCut
        giu = [(max(a, lo), min(b, hi)) for a, b in q["giu"] if min(b, hi) - max(a, lo) > 0.05]
        ket_qua.append({"path": c["path"], "giu": giu, "phan": ph})
        g = sum(b - a for a, b in giu)
        tong_goc += c["src_dur"]
        tong_giu += g
        bao_cao.append({"file": Path(c["path"]).name, "phan": ph, "goc": round(c["src_dur"], 1), "giu": round(g, 1),
                        "co_loi": bool(q["noi"].any()), "giu_doan": [[round(a, 1), round(b, 1)] for a, b in giu],
                        "bo": [[round(a, 1), round(b, 1), LY_DO.get(r, r)] for a, b, r in q["bo"]]})
    log(f"Giữ {_fmt(tong_giu)} / {_fmt(tong_goc)} ({100 * tong_giu / max(tong_goc, 1):.0f}%).")
    ten_moi = cfg.get("ten_moi") or f"{nguon} CẮT THÔ"
    if cfg.get("chi_phan_tich"):
        kq = {"name": "", "duration": tong_giu}
    else:
        kq = tao_du_an(nguon, ket_qua, ten_moi, log=log)
        log(f"Đã tạo dự án CapCut '{kq['name']}' · {_fmt(kq['duration'])} · {kq['so_doan']} đoạn · "
            f"{kq['so_nhan']} nhãn phần. Mở CapCut để xem.")
    KQ_DIR.mkdir(parents=True, exist_ok=True)
    (KQ_DIR / f"{nguon}.json").write_text(json.dumps({"du_an": kq.get("name"), "muc": muc, "goc": tong_goc,
                                                       "giu": tong_giu, "clip": bao_cao}, ensure_ascii=False,
                                                      indent=1), encoding="utf-8")
    return kq
