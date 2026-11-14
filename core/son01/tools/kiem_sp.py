"""Kiem tra SAN PHAM trong tung canh bang doc chu tren bao bi (RapidOCR) - lop chan san pham khac hang.

python kiem_sp.py <canh.json> [--so-khung 3]
Them nhan sp_tc01 / sp_dam_ca / sp_khac vao canh.json (giu nhan cu), ghi chu doc duoc vao truong "ocr".
"""
import sys, os, json, re, subprocess, tempfile, unicodedata
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from rapidocr_onnxruntime import RapidOCR

pj = sys.argv[1]
opt = dict(zip(sys.argv[2::2], sys.argv[3::2]))
K = int(opt.get("--so-khung", 3))
FF = os.environ.get("SONIX_FFMPEG") or __import__("imageio_ffmpeg").get_ffmpeg_exe()
canh = json.load(open(pj, encoding="utf-8"))
ocr = RapidOCR()


def bo_dau(s):
    s = unicodedata.normalize("NFD", s.upper().replace("Đ", "D").replace("đ", "D"))
    return re.sub(r"[̀-ͯ]", "", s)


LUAT = [
    ("sp_tc01", [r"KICH\s*RE", r"TC\s*-?\s*0?1\b", r"GIAM\s*CANH"]),
    ("sp_dam_ca", [r"DAM\s*CA", r"AMINO"]),
    ("sp_khac", [r"NANO", r"MAGIE", r"HUMIC", r"CANXI", r"\bBO\s*\+", r"BIO\s*ROOT", r"SIEU\s*MUOT",
                 r"CHEATUMIG", r"MIG\s*38", r"BAM\s*DINH", r"BO\s*TRI", r"TOP\s*ONE"]),
]

LOAI_CHU = [r"TIKTOK", r"TRA\s*LOI", r"BINH\s*LUAN", r"FLASH", r"SALE", r"UU\s*DAI", r"DAT\s*HANG", r"MUA\s*NGAY",
            r"GIO\s*HANG", r"FREESHIP", r"\d{2,3}\s*K\b", r"\d{2,3}[.,]000", r"CAPCUT", r"FOLLOW"]

# Do mat nguoi (MediaPipe): mat lon -> canh co nguoi dan / noi truoc camera -> loai
sys.path.insert(0, os.environ.get("SONIX_APP") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")))
import cv2, numpy as np, mediapipe as mp
from core.canh import _face  # bo do mat cua app (MediaPipe tasks + model blaze_face)


def co_mat_lon(path):
    img = cv2.imread(path)
    if img is None:
        return False
    h, w = img.shape[:2]
    rgb = np.ascontiguousarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    for f in _face().detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)).detections:
        if f.bounding_box.height > 0.09 * h:   # mat chiem > 9% chieu cao khung
            return True
    return False


tmp = tempfile.mkdtemp()
for n, c in enumerate(canh, 1):
    if "ocr" in c or c.get("loi") or "loai" in c.get("nhan", []):
        # canh da doc truoc do: chi ap lai luat chu in san
        if "ocr" in c and any(re.search(p, bo_dau(c["ocr"])) for p in LOAI_CHU):
            c["nhan"] = sorted(set(c.get("nhan", [])) | {"loai"})
        if "ocr" in c and "co_mat" not in c and "loai" not in c["nhan"]:
            p = os.path.join(tmp, "m.jpg")
            subprocess.run([FF, "-v", "error", "-y", "-ss", f"{(c['s'] + c['e']) / 2:.2f}", "-i", c["file"], "-frames:v", "1",
                            "-vf", "scale=540:-2", p])
            c["co_mat"] = os.path.exists(p) and co_mat_lon(p)
            if c["co_mat"]:
                c["nhan"] = sorted(set(c["nhan"]) | {"loai"})
        continue
    chu = []
    for j in range(K):
        t = c["s"] + (c["e"] - c["s"]) * (j + 1) / (K + 1)
        p = os.path.join(tmp, f"k{j}.jpg")
        subprocess.run([FF, "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", c["file"], "-frames:v", "1", "-vf", "scale=720:-2", p])
        if os.path.exists(p):
            res, _ = ocr(p)
            chu += [r[1] for r in (res or []) if r[2] > 0.5]
            c["co_mat"] = bool(c.get("co_mat")) or co_mat_lon(p)
            os.remove(p)
    txt = bo_dau(" ".join(chu))
    c["ocr"] = " | ".join(chu)[:300]
    nhan = set(c.get("nhan", []))
    if c.get("co_mat") or any(re.search(p, txt) for p in LOAI_CHU):
        nhan.add("loai")
    for tag, pats in LUAT:
        if any(re.search(p, txt) for p in pats):
            nhan.add(tag)
    c["nhan"] = sorted(nhan)
    if n % 25 == 0:
        json.dump(canh, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"{n}/{len(canh)}", flush=True)
json.dump(canh, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
from collections import Counter
print("Xong. San pham:", dict(Counter(t for c in canh for t in c["nhan"] if t.startswith("sp_"))))
