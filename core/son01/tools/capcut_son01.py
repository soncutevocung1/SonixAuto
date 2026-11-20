"""Buoc 5 - Tao du an CapCut phong cach "Son 01" tu ke hoach dung.

Khuon = 1 timeline anh Son tu dung (vd "Dam shop Bo" trong du an DAMBOTC01_SONIX).
Cac lop duoc nhan dien THEO NOI DUNG (khong theo thu tu), xoa noi dung cu, nhan ban lai theo ke hoach:
  video chinh (cat + zoom lo xo bang keyframe), chinh mau + bo loc (keo dai), hieu ung Mo + khung vien sang
  + video minh hoa (khung bo goc, toc do 2x, truot vao), chu mo dau, phu de (tu khoa vang), dem y,
  tieng hieu ung (go phim / ting / chuong / ding), nhac nen.

python capcut_son01.py ke_hoach.json <video_goc> "<ten du an moi>" [--khuon DAMBOTC01_SONIX] [--timeline "Đạm shop Bọ"]
        [--thu-vien canh.json] [--ra ke_qua.json]
CapCut phai TAT khi tao.
"""
import copy, json, os, re, shutil, sys, time, unicodedata
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APP = os.environ.get("SONIX_APP") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, APP)
from core.capcut_draft import _Draft, _uid, _us, US, YELLOW, WHITE, capcut_dang_mo, CapCutError  # noqa: E402
from core.video_utils import probe  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from lo_xo import spring_keys  # noqa: E402

LOCAL = Path(os.path.expandvars(r"%LOCALAPPDATA%\CapCut\User Data"))
ROOT_DIR = LOCAL / "Projects" / "com.lveditor.draft"   # root_meta_info.json luon o day


def drafts_dir() -> Path:
    """Thu muc luu du an: doc 'currentCustomDraftPath' trong cai dat CapCut (vd E:\\Capcut\\CapCut Drafts)."""
    gs = LOCAL / "Config" / "globalSetting"
    try:
        for line in gs.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("currentCustomDraftPath="):
                p = line.split("=", 1)[1].strip().replace("\\\\", "\\")
                if p and Path(p).exists():
                    return Path(p)
    except OSError:
        pass
    return ROOT_DIR


def nfc(s):
    return unicodedata.normalize("NFC", s)


# ---------------------------------------------------------------- nhan dien lop trong khuon
def text_of(mat):
    try:
        return nfc(json.loads(mat["content"])["text"])
    except Exception:
        return ""


class Khuon:
    def __init__(self, d):
        self.d = d
        self.dr = _Draft(d)
        self.role = {}       # ten vai -> (track, segment mau)
        self.tracks = {}     # ten lop -> track
        self.sfx = {}        # ten am -> segment mau
        self.anim = {}       # ten hieu ung chu (vao) -> (vat lieu material_animations, animation)
        vids = [t for t in d["tracks"] if t["type"] == "video" and t["segments"]]
        # video chinh = lop video co tong thoi luong dai nhat
        main = max(vids, key=lambda t: sum(s["target_timerange"]["duration"] for s in t["segments"]))
        self.tracks["main"] = main
        plain = [s for s in main["segments"] if not s.get("common_keyframes")]
        self.role["main"] = plain[0] if plain else main["segments"][0]
        for t in vids:
            if t is main:
                continue
            k, m = self.dr.find(t["segments"][0]["material_id"])
            refs = [self.dr.find(r)[0] for r in t["segments"][0].get("extra_material_refs", [])]
            if "drafts" in refs or (m or {}).get("type") == "video" and (m or {}).get("width") == 1080 and "combination" in str((m or {}).get("path", "")):
                self.tracks["glow"], self.role["glow"] = t, t["segments"][0]
            elif "common_mask" in refs:
                self.tracks["broll"], self.role["broll"] = t, t["segments"][0]
        for t in d["tracks"]:
            if not t["segments"]:
                continue
            if t["type"] in ("adjust", "filter"):
                self.tracks.setdefault("keo_dai", []).append(t)
            elif t["type"] == "effect":
                self.tracks["mo"], self.role["mo"] = t, t["segments"][0]
            elif t["type"] == "audio":
                for s in t["segments"]:
                    _, m = self.dr.find(s["material_id"])
                    nm = nfc((m or {}).get("name", ""))
                    if (m or {}).get("type") == "music":
                        self.tracks["nhac"], self.role["nhac"] = t, s
                    else:
                        self.sfx.setdefault(nm, s)
                        self.tracks.setdefault("sfx", [])
                        if t not in self.tracks["sfx"]:
                            self.tracks["sfx"].append(t)
            elif t["type"] == "text":
                self.tracks.setdefault("chu", []).append(t)
                for s in t["segments"]:
                    for r in s.get("extra_material_refs", []):
                        kk, mm = self.dr.find(r)
                        if kk == "material_animations":
                            for a in mm.get("animations", []):
                                if a.get("type") == "in" and a.get("name"):
                                    self.anim.setdefault(nfc(a["name"]), (mm, a))
                    _, m = self.dr.find(s["material_id"])
                    tx = text_of(m)
                    st = json.loads(m["content"]).get("styles", [])
                    font = st[0].get("font", {}).get("path", "") if st else ""
                    if "DTPhudu" in font:
                        col = st[0]["fill"]["content"]["solid"]["color"]
                        self.role.setdefault("mo_dau_2" if col[1] < 0.5 else "mo_dau_1", s)
                    elif tx.startswith("THỨ"):
                        self.role.setdefault("dem_y", s)
                    elif re.fullmatch(r"\d", tx):
                        self.role.setdefault("so", s)
                    elif "COI CHỪNG" in tx:
                        self.role.setdefault("canh_bao", s)
                    elif "UTM Avo.ttf" in font and len(st) == 1 and st[0]["fill"]["content"]["solid"]["color"][1] > 0.9:
                        self.role.setdefault("phu_de", s)
                    elif "Bold_Italic" in font or "BoldItalic" in font:
                        self.role.setdefault("tu_khoa", s)
        thieu = [r for r in ("main", "phu_de", "mo_dau_1") if r not in self.role]
        if thieu:
            raise CapCutError("Khuon thieu lop: " + ", ".join(thieu))

    def find(self, mid):
        return self.dr.find(mid)


# ---------------------------------------------------------------- ham dung
def clone(k: Khuon, seg, start, dur):
    s = k.dr.clone_seg(seg)
    s["target_timerange"] = {"start": int(start), "duration": int(dur)}
    s["common_keyframes"] = []
    s["keyframe_refs"] = []
    return s


def clone_mat(k: Khuon, s, **changes):
    s["material_id"] = k.dr.clone_mat(s["material_id"], **changes)
    return k.find(s["material_id"])[1]


def set_text(mat, text, keywords=(), color=None):
    """Ghi chu + to vang tu khoa (giu font/vien cua mau)."""
    c = json.loads(mat["content"])
    base = c["styles"][0]
    text = nfc(text)
    spans = []
    low = text.lower()
    for kw in keywords:
        kw = nfc(kw).lower()
        i = low.find(kw)
        if i >= 0:
            spans.append((i, i + len(kw)))
    spans.sort()
    styles, pos = [], 0
    def st(a, b, kw):
        x = copy.deepcopy(base)
        x["range"] = [a, b]
        x["fill"]["content"]["solid"]["color"] = list(YELLOW if kw else (color or base["fill"]["content"]["solid"]["color"]))
        if kw:
            x["bold"] = True
        else:
            x.pop("bold", None)
        return x
    for a, b in spans:
        if a < pos:
            continue
        if a > pos:
            styles.append(st(pos, a, False))
        styles.append(st(a, b, True))
        pos = b
    if pos < len(text):
        styles.append(st(pos, len(text), False))
    c["text"], c["styles"] = text, styles
    mat["content"] = json.dumps(c, ensure_ascii=False)
    mat["base_content"] = ""


def keyframes(seg, src_start_us, kind):
    """Zoom lo xo bang 5 keyframe theo duong cong spring (thoi gian = thoi gian nguon)."""
    if kind == "khong":
        return
    peak = 1.18 if kind == "manh" else 1.08
    pts = spring_keys(stiffness=260, damping=22, n=5, dur=0.42)  # [(giay, tien_do)]
    kl = []
    for t, p in pts:
        kl.append({"id": _uid(), "curveType": "Line", "time_offset": int(src_start_us + _us(0.05 + t)),
                   "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0},
                   "values": [round(1 + (peak - 1) * p, 4)], "string_value": "", "graphID": ""})
    seg["common_keyframes"] = [{"id": _uid(), "material_id": "", "property_type": "KFTypeScaleX", "keyframe_list": kl}]
    seg["clip"]["scale"] = {"x": peak, "y": peak}


TEN_RIENG = {"amino", "tc01", "atonik", "npk", "humic", "đạm", "kích"}


def ngat_dong(txt, toi_da=22):
    """Chu mo dau: ngat dong chu dong (<= toi_da ky tu/dong) de CapCut khong tu xuong dong chong chu."""
    ws = txt.split()
    if len(txt) <= toi_da:
        return txt
    if len(txt) <= 2 * toi_da:  # 2 dong can nhau
        i = min(range(1, len(ws)), key=lambda i: abs(len(" ".join(ws[:i])) - len(" ".join(ws[i:]))))
        return " ".join(ws[:i]) + "\n" + " ".join(ws[i:])
    dong, cur = [], ""
    for w in ws:
        if cur and len(cur) + 1 + len(w) > toi_da:
            dong.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        dong.append(cur)
    return "\n".join(dong)


def viet_phu_de(txt):
    """Phu de kieu anh Son: chu thuong, giu ten rieng (Amino, TC01, NPK), bo dau cham cuoi."""
    ws = []
    for w in txt.split():
        lw = w.lower()
        ws.append(w if lw.strip(",.?!") in ("amino", "tc01", "npk", "atonik") else lw)
    return " ".join(ws).rstrip(".")


def chia_cum(words, max_chu=5, max_kt=24, gap=0.25):
    """Chia loi thanh cum phu de 2-5 chu, ngat o dau cau / cho ngung."""
    # khong ngat cum ngay sau tu noi (vd "Thu | nhat", "cua | cay")
    NOI = {"thứ", "là", "của", "và", "các", "những", "một", "cho", "với", "khi", "mà", "thì", "bị", "được",
           "đang", "đã", "sẽ", "rất", "hoặc", "hay", "trong", "vào", "theo", "để", "cái", "con", "giai", "bình"}
    out, cur = [], []
    for i, w in enumerate(words):
        cuoi_noi = bool(cur) and cur[-1]["w"].lower().strip(",.") in NOI and len(cur) < max_chu + 2
        # chu viet hoa giua chuoi = dau cau moi (Whisper) -> ngat truoc no (tru ten rieng)
        dau_cau = bool(cur) and w["w"][:1].isupper() and w["w"].lower() not in TEN_RIENG
        if cur and (dau_cau or not cuoi_noi and (len(cur) >= max_chu or len(" ".join(x["w"] for x in cur + [w])) > max_kt
                                                 or w["s"] - cur[-1]["e"] > gap)):
            out.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[,.?!]$", w["w"]) and len(cur) >= 2:
            out.append(cur)
            cur = []
    if cur:
        if out and len(cur) == 1:
            out[-1] += cur
        else:
            out.append(cur)
    return out


NOI = {"thứ", "là", "của", "và", "các", "những", "một", "cho", "với", "khi", "mà", "thì", "bị", "được",
       "đang", "đã", "sẽ", "rất", "hoặc", "hay", "trong", "vào", "theo", "để", "cái", "con", "giai", "bình"}


TU_GHEP = {"tham khảo", "hấp thu", "dinh dưỡng", "phát triển", "giai đoạn", "thu hoạch", "sản phẩm", "bình luận",
           "hoạt động", "tình trạng", "suy yếu", "buổi sáng", "buổi chiều", "buổi trưa", "nắng nóng", "chiều mát",
           "sáng sớm", "cây con", "rễ cây", "đạm cá", "bà con", "các bác", "ý kiến", "video này", "bình phun",
           "nuôi hoa", "dưỡng quả", "dưỡng trái", "khô cứng", "hao phân", "giỏ hàng", "màn hình", "sử dụng",
           "chất lượng", "hiệu quả", "phục hồi", "bộ rễ", "lá xanh", "ra hoa", "đậu quả", "vàng lá", "thời điểm"}


def chia_dong(ws, xd=-1, toi_da=20):
    """Ngat dong CHU DONG o cho ngat nghia (anh Son: 'tranh di vao / buoi trua nang nong'),
    moi dong <= ~20 ky tu -> CapCut khong tu xuong dong giua chu ('cu / ng')."""
    w = [nfc(x).strip() for x in ws if x.strip()]
    def dinh(i, noi=True):  # ngat giua tu ghep / sau so (/ sau tu noi khi tu chia) -> sai nghia
        a_, b_ = w[i - 1].lower().strip(",.?!"), w[i].lower().strip(",.?!")
        return (a_ + " " + b_) in TU_GHEP or re.fullmatch(r"[\d,.-]+", a_) is not None or (noi and a_ in NOI)
    if 0 < xd < len(w) and dinh(xd, False):
        xd = next((j for j in (xd + 1, xd - 1, xd + 2, xd - 2) if 0 < j < len(w) and not dinh(j, False)), xd)
    if 0 < xd < len(w):
        return " ".join(w[:xd]) + "\n" + " ".join(w[xd:])
    txt = " ".join(w)
    if len(txt) <= toi_da or len(w) < 2:
        return txt
    def diem(i):
        a, b = " ".join(w[:i]), " ".join(w[i:])
        return abs(len(a) - len(b)) + (12 if dinh(i) else 0)
    i = min(range(1, len(w)), key=diem)
    return " ".join(w[:i]) + "\n" + " ".join(w[i:])


def dat_anim(k, seg, ten, dai_us):
    """Doi hieu ung xuat hien cua 1 doan chu (ten trong khuon: 'Loại xem trước', 'Bật lên', 'Trượt lên'...);
    None = hien ngay. Thoi luong hieu ung co gian theo do dai doan (doc kip)."""
    refs = seg.setdefault("extra_material_refs", [])
    idx = next((i for i, r in enumerate(refs) if k.find(r)[0] == "material_animations"), None)
    if ten is None or nfc(ten) not in k.anim:
        if idx is not None:
            k.find(refs[idx])[1]["animations"] = []
        return
    mm, a = k.anim[nfc(ten)]
    n = copy.deepcopy(mm)
    n["id"] = _uid()
    a2 = copy.deepcopy(a)
    a2["start"] = 0
    a2["duration"] = int(min(a.get("duration", _us(0.5)), max(_us(0.15), dai_us * 0.3)))
    n["animations"] = [a2]
    k.dr.m.setdefault("material_animations", []).append(n)
    if idx is None:
        refs.append(n["id"])
    else:
        refs[idx] = n["id"]


# hieu ung chu xoay vong nhu ban anh Son (19 'Loai xem truoc', 13 'Truot len', 4 'Bat len', vai doan khong hieu ung)
ANIM_XOAY = ["Loại xem trước", "Bật lên", "Loại xem trước", None, "Trượt lên", "Loại xem trước", "Bật lên",
             "Loại xem trước", "Trượt lên", None]
JITTER = [0.0, -0.035, 0.025, -0.015, 0.035, -0.025]

# nhom tieng hieu ung (ten trong khuon, so khop dau ten) - xoay vong, khong lap lien nhau
NHOM_AM = {
    "hook1": ["Magic reveal"],
    "hook2": ["滴滴"],
    "go": ["Realistic sound effects for typing", "Enter / click", "Computer-Mouse-Click", "pop! (tapping"],
    "tu_khoa": ["得分", "\"Pop!\"", "Hupong!"],
    "mh": ["UI提示-976714", "Cute notification sound", "UI提示-3262", "StingerCameraShut", "相机快门"],
    "luoi": ["Camera burst", "相机快门", "StingerCameraShut", "UI提示-976714"],
    "dem_y": ["Cute system Pyui"],
    "so": ["回答正确", "Cute system Pyui"],
    "ding": ["Ding"],
}


def chon_am(names, am):
    """am: [(us, nhom)] -> [(us, ten am)]; tiet che mat do (anh Son ~0.8-1 tieng/giay, khong qua 0.75/giay o day
    vi nguoi xem de nhuc dau) va xoay nhieu loai tieng."""
    import collections
    dem, out, last, cuoi = collections.Counter(), [], None, -10 ** 9
    uu_tien = {"hook1": 0, "hook2": 0, "dem_y": 0, "so": 1, "ding": 0, "luoi": 1, "mh": 1, "tu_khoa": 2, "go": 3}
    for at, nhom in sorted(am, key=lambda x: (x[0], uu_tien.get(x[1], 5))):
        if nhom == "go" and at - cuoi < _us(1.1):
            continue
        if nhom in ("tu_khoa", "mh") and at - cuoi < _us(0.35):
            continue
        ung = []
        for p in NHOM_AM.get(nhom, [nhom]):
            ung += [n for n in names if n.startswith(nfc(p)) and n not in ung]
        if not ung and nhom not in ("go",):
            ung = [n for p in NHOM_AM["go"] for n in names if n.startswith(nfc(p))]
        if not ung:
            continue
        ten = min(ung, key=lambda n: (n == last, dem[n], ung.index(n)))
        if nhom == "go" and dem[ten] >= 6:
            continue
        dem[ten] += 1
        out.append((at, ten))
        last, cuoi = ten, at
    return out


def vi_tri_phu_de(video, giay, scale=1.0, vung_sp=0.72):
    """Y (toa do CapCut, +1 = tren cung) cho phu de: sat duoi cam, khong che mat; lan vao vung san pham
    (mac dinh tu 72% chieu cao tro xuong) thi dat len tren dau. Khong thay mat -> 0.42 nhu khuon."""
    try:
        import numpy as np, cv2, mediapipe as mp
        from core.canh import _face, khung
        img = khung(video, giay, 1080)
        if img is None:
            return 0.42
        H, W = img.shape[:2]
        # Nguoi mau ngoi xa -> mat nho (~5% khung): cat vung giua roi phong to cho bo do mat tam gan bat duoc
        y0 = y1 = None
        for cx0, cy0, cx1, cy1 in ((0.15, 0.15, 0.85, 0.75), (0.0, 0.0, 1.0, 1.0), (0.25, 0.30, 0.75, 0.65)):
            a, b, c2, d2 = int(cx0 * W), int(cy0 * H), int(cx1 * W), int(cy1 * H)
            crop = cv2.resize(img[b:d2, a:c2], None, fx=640 / (c2 - a), fy=640 / (c2 - a))
            rgb = np.ascontiguousarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            dets = _face().detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)).detections
            if dets:
                bb = max(dets, key=lambda d: d.bounding_box.width * d.bounding_box.height).bounding_box
                k = (d2 - b) / crop.shape[0]
                y0 = (b + bb.origin_y * k) / H
                y1 = (b + (bb.origin_y + bb.height) * k) / H
                break
        if y0 is None:
            return 0.42
        def ra(yn):  # toa do nguon -> khung ra (zoom quanh tam)
            return 0.5 + (yn - 0.5) * scale
        # Khuon anh Son: phu de nam TREN DAU (y CapCut 0.40-0.57), tranh tay/nguc khi noi.
        # Mat do duoc khong gom non -> chua them ~12% chieu cao cho non la.
        tren = ra(y0) - 0.12
        duoi = ra(y1) + 0.075          # du phong: duoi cam (khi tren dau het cho)
        y = tren if tren >= 0.16 else (duoi if duoi < vung_sp else 0.16)
        y = min(max(y, 0.12), 0.80)    # vung an toan TikTok (tranh thanh tren / chu mo ta duoi)
        return round(1 - 2 * y, 3)
    except Exception as e:
        print("vi_tri_phu_de loi:", e)
        return 0.42


SP_TAGS = {"sp_tc01", "sp_dam_ca", "sp_khac"}


_OCR = None
_CAM_CHU = {"sp_dam_ca": [r"[T7]\s*C\s*[O0]\s*1\b", r"GIAM\s*CANH", r"NANO", r"MAGIE", r"HUMIC", r"CANXI"],
            "sp_tc01": [r"DAM\s*CA", r"AMINO", r"NANO", r"MAGIE", r"HUMIC", r"CANXI"]}
_CHU_IN = [r"TIKTOK", r"TRA\s*LOI", r"BINH\s*LUAN", r"FLASH", r"SALE", r"UU\s*DAI", r"DAT\s*HANG", r"MUA\s*NGAY",
           r"\d{2,3}\s*K\b", r"\d{2,3}[.,]000", r"FOLLOW"]


def _bo_dau(s):
    s = unicodedata.normalize("NFD", s.upper().replace("Đ", "D").replace("đ", "D"))
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


def kiem_canh(c, sp, dung_giay, cho_nguoi=True):
    """Soi 3 khung (dau/giua/cuoi) cua DUNG doan se dung: co mat nguoi lon, chu in san, hoac
    chu san pham khac -> loai. Ket qua luu vao canh (khong soi lai)."""
    key = f"kiem2_{sp}_{round(dung_giay, 1)}_{int(cho_nguoi)}"
    if key in c:
        return c[key]
    global _OCR
    import numpy as np, cv2, mediapipe as mp
    from core.canh import _face, khung
    if _OCR is None:
        from rapidocr_onnxruntime import RapidOCR
        _OCR = RapidOCR()
    ok, ly_do = True, ""
    e = min(c["e"], c["s"] + dung_giay)
    for t in (c["s"] + 0.15, (c["s"] + e) / 2, e - 0.15):
        img = khung(c["file"], t, 720)
        if img is None:
            continue
        h = img.shape[0]
        rgb = np.ascontiguousarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        if not cho_nguoi and any(d.bounding_box.height > 0.05 * h for d in _face().detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)).detections):
            ok, ly_do = False, f"co mat nguoi @{t:.1f}"
            break
        res, _ = _OCR(img)
        txt = _bo_dau(" ".join(r[1] for r in (res or [])))
        bad = [p for p in _CAM_CHU.get(sp, []) + _CHU_IN if re.search(p, txt)]
        if bad:
            ok, ly_do = False, f"chu '{bad[0]}' @{t:.1f}"
            break
    c[key] = ok
    if not ok:
        print(f"  bo canh {c['id']}: {ly_do}")
    return ok


SP_NGAN = {"sp_dam_ca": "dam_ca", "sp_tc01": "tc01"}


def _tu(s_):
    return set(re.findall(r"\w+", _bo_dau(s_ or "").lower()))


def chat_luong(c):
    """0..1: do net (Laplacian, AI 'mo') x do phan giai canh ngan."""
    res = min(1.0, min(c.get("w", 576), c.get("h", 1024)) / 1080)
    net = c.get("net")
    net = 0.5 if net is None else min(1.0, net / 250)
    return (0.25 if c.get("mo") else 1.0) * (0.4 + 0.6 * res) * (0.4 + 0.6 * net)


def hop_le(c, sp, cho_nguoi):
    n = set(c.get("nhan", []))
    if "loai" in n and "chai" not in c:   # thu vien cu: 'loai' gom ca chu in/mo -> bo
        return False
    if c.get("mo") or c.get("chu_in") or "loai_han" in n:
        return False
    chai = set(c.get("chai", []))
    if chai - {SP_NGAN.get(sp, sp)}:      # lo chai/bao bi san pham khac (vd chai kich re trong video dam ca)
        return False
    if "chai" not in c and ((SP_TAGS - {sp}) & n):
        return False
    if c.get("nguoi_noi") and not cho_nguoi:
        return False
    return True


def chon_canh(thu_vien, nhan, da_dung, sp=None, dung_giay=3.0, loi="", da_file=None, cho_nguoi=False, nhan_phu=()):
    """Chon canh: dung nhan, khong lo chai san pham khac, net + phan giai cao, khop mo ta voi loi noi,
    KHONG dung lai canh/file da dung trong video (tranh lap canh)."""
    if not thu_vien or not nhan:
        return None
    da_file = da_file if da_file is not None else set()
    nh = [nhan, *nhan_phu]
    tl = _tu(loi)
    cands = [c for c in thu_vien if set(nh) & set(c.get("nhan", [])) and c["id"] not in da_dung
             and c["file"] not in da_file and c.get("dai", 0) >= min(dung_giay, 2.0) * 0.5 and hop_le(c, sp, cho_nguoi)]
    def diem(c):
        d = 3 * chat_luong(c) + (1.0 if nhan in c.get("nhan", []) else 0) + 0.5 * (sp in c.get("nhan", []))
        d += 0.3 * len(tl & _tu(c.get("mo_ta", ""))) + 0.3 * min(c["dai"], 6) / 6
        return d
    cands.sort(key=diem, reverse=True)
    for c in cands[:10]:
        if kiem_canh(c, sp, dung_giay, cho_nguoi=True):
            return c
    return None


# ---------------------------------------------------------------- chinh
def build(kh, video_goc, k: Khuon, thu_vien=None):
    d = k.d
    sfx_tracks = k.tracks.get("sfx", [])
    keep = {id(t) for t in [k.tracks["main"], k.tracks.get("glow"), k.tracks.get("broll"), k.tracks.get("mo"),
                            k.tracks.get("nhac")] + k.tracks.get("keo_dai", []) + k.tracks.get("chu", []) + sfx_tracks if t}
    d["tracks"] = [t for t in d["tracks"] if id(t) in keep]
    tpl = {r: copy.deepcopy(s) for r, s in k.role.items()}
    sfx_tpl = {n: copy.deepcopy(s) for n, s in k.sfx.items()}
    for t in d["tracks"]:
        if t not in k.tracks.get("keo_dai", []):
            t["segments"] = []

    # vat lieu video goc
    _, main_mat = k.find(tpl["main"]["material_id"])
    info = probe(video_goc) if video_goc else {}
    if video_goc and nfc(Path(main_mat["path"]).name) != nfc(Path(video_goc).name):
        tpl["main"]["material_id"] = k.dr.clone_mat(tpl["main"]["material_id"], path=str(video_goc).replace("\\", "/"),
                                                    material_name=Path(video_goc).name,
                                                    duration=_us(info.get("duration", 0)) or main_mat["duration"])

    t = 0
    hook_end = _us(2.2) if kh.get("chu_mo_dau") else 0
    if len(kh.get("chu_mo_dau", [])) > 1:
        hook_end = _us(2.4)
    # Nhu ban anh Son: chu mo dau phu het doan mo dau (toi da 4.5s), khong phu de lap lai trong doan nay
    if kh.get("chu_mo_dau") and kh["doan"] and kh["doan"][0]["vai"] == "mo_dau":
        hook_end = max(hook_end, min(_us(kh["doan"][0]["e"] - kh["doan"][0]["s"]), _us(4.5)))
    last_go = [-_us(5)]
    # khoang thoi gian nhan dem y hien (tinh truoc tu ke hoach) -> de phu de ne
    dem_span, tt = [], 0
    for j, y in enumerate(kh["doan"]):
        dj = _us(y["e"] - y["s"])
        if y.get("dem_y") and (j == 0 or kh["doan"][j - 1].get("dem_y") != y["dem_y"]):
            span = dj + sum(_us(z["e"] - z["s"]) for z in kh["doan"][j + 1:j + 1 + next(
                (n for n, z in enumerate(kh["doan"][j + 1:]) if z.get("dem_y") != y["dem_y"]), len(kh["doan"]))])
            dem_span.append((tt, tt + span))
        tt += dj
    am = []          # (thoi diem us, nhom am) -> chon_am xoay vong ten tieng
    da_dung, da_file = set(), set()
    so_y = 0
    st = {"anim": 0, "luoi_cuoi": -10}
    luoi_tracks = []

    def them_doan_video(trk, c, a, b, scale=None, x=None, y=None):
        """1 canh minh hoa (khung bo goc cua khuon), toc do toi da 2x, TAT TIENG."""
        bs = clone(k, tpl["broll"], a, b - a)
        need = (b - a) / US
        toc = max(0.5, min(2.0, c["dai"] / need))
        src = c["file"].replace("\\", "/")
        clone_mat(k, bs, path=src, material_name=Path(src).name, width=c["w"], height=c["h"], duration=_us(c["e"] + 1))
        bs["source_timerange"] = {"start": _us(c["s"]), "duration": _us(need * toc)}
        bs["speed"] = toc
        bs["volume"] = 0.0
        for r in bs.get("extra_material_refs", []):
            kk, m = k.find(r)
            if kk == "speeds":
                m["speed"] = toc
        if scale is not None:
            bs["clip"]["scale"] = {"x": scale, "y": scale}
            bs["clip"]["transform"]["x"], bs["clip"]["transform"]["y"] = x, y
        trk["segments"].append(bs)
        da_dung.add(c["id"])
        da_file.add(c["file"])

    def lop_luoi():
        """4 cap lop (vien sang + video) cho luoi 4 o, nhu du an PBCP/SPT/bo 3 cua anh Son."""
        if not luoi_tracks:
            bt, gt = k.tracks["broll"], k.tracks.get("glow")
            luoi_tracks.append((gt, bt))
            sau = bt
            for j in range(3):
                cap = []
                for src in (gt, bt):
                    if src is None:
                        cap.append(None)
                        continue
                    nt = copy.deepcopy({kk: vv for kk, vv in src.items() if kk != "segments"})
                    nt["id"] = _uid()
                    nt["segments"] = []
                    d["tracks"].insert(d["tracks"].index(sau) + 1, nt)
                    sau = nt
                    cap.append(nt)
                luoi_tracks.append(tuple(cap))
        return luoi_tracks

    O_LUOI = [(-0.5, 0.36), (0.5, 0.36), (-0.5, -0.36), (0.5, -0.36)]
    for i, x in enumerate(kh["doan"]):
        dur = _us(x["e"] - x["s"])
        s = clone(k, tpl["main"], t, dur)
        s["source_timerange"] = {"start": _us(x["s"]), "duration": dur}
        s["clip"] = copy.deepcopy(tpl["main"]["clip"])
        keyframes(s, _us(x["s"]), x.get("zoom", "khong"))
        # Che cat nhay (jump cut): doan khong zoom thi phong xen ke 1.0 / 1.1 so voi doan truoc
        if x.get("zoom", "khong") == "khong" and i % 2 == 1:
            s["clip"]["scale"] = {"x": 1.1, "y": 1.1}
        k.tracks["main"]["segments"].append(s)
        x["t0"] = t

        zs = s["clip"]["scale"]["x"]
        y_mat = vi_tri_phu_de(video_goc, (x["s"] + x["e"]) / 2, zs) if video_goc else 0.42
        x["y_phu_de"] = y_mat
        kieu_mh = None
        # Doan mo dau / keu goi giu mat nguoi mau (tao tin tuong) -> khong chen minh hoa
        cho_phep = x["vai"] not in ("mo_dau", "keu_goi") and t >= _us(4.0) and x["e"] - x["s"] >= 1.2 and "broll" in k.role
        a_mh, b_mh = t + _us(0.25), t + dur
        # Cach dung / pha: LUOI 4 O canh nguoi dung that (2x, tat tieng) -> nguoi xem thay nhieu nguoi dang dung
        if (cho_phep and x["vai"] == "cach_dung" and x.get("minh_hoa") in ("pha_thuoc", "phun_tuoi", "nong_dan_vuon")
                and x["e"] - x["s"] >= 2.0 and i - st["luoi_cuoi"] > 1):
            o = []
            for nh in (x["minh_hoa"], "pha_thuoc", "phun_tuoi", "nong_dan_vuon"):
                while len(o) < 4:
                    c = chon_canh(thu_vien, nh, da_dung | {z["id"] for z in o}, kh.get("sp"), 2.0 * (b_mh - a_mh) / US,
                                  x.get("text", ""), da_file | {z["file"] for z in o}, cho_nguoi=True)
                    if not c:
                        break
                    o.append(c)
            if len(o) == 4:
                trs = lop_luoi()
                f = 0.66
                sc = round(tpl["broll"]["clip"]["scale"]["x"] * f, 3)
                # lam mo nen phia sau (hieu ung 'Mo' cua khuon) suot luc hien luoi
                if "mo" in tpl:
                    k.tracks["mo"]["segments"].append(clone(k, tpl["mo"], a_mh, b_mh - a_mh))
                for j, (c, (ox, oy)) in enumerate(zip(o, O_LUOI)):
                    a_j = a_mh + _us(0.12 * j)
                    gt, vt = trs[j]
                    if gt is not None and "glow" in tpl:  # vien sang cho tung o: thu nho + dat cung cho voi video
                        g = clone(k, tpl["glow"], a_j, b_mh - a_j)
                        g["clip"] = copy.deepcopy(tpl["glow"]["clip"])
                        gs = g["clip"]["scale"]["x"] * f
                        g["clip"]["scale"] = {"x": round(gs, 3), "y": round(gs, 3)}
                        g["clip"]["transform"]["x"] = ox
                        g["clip"]["transform"]["y"] = round(oy + tpl["glow"]["clip"]["transform"]["y"] * f
                                                            - tpl["broll"]["clip"]["transform"]["y"] * f, 3)
                        gt["segments"].append(g)
                    them_doan_video(vt, c, a_j, b_mh, sc, ox,
                                    round(oy + tpl["broll"]["clip"]["transform"]["y"] * f - tpl["broll"]["clip"]["transform"]["y"] * f, 3))
                kieu_mh = "luoi"
                st["luoi_cuoi"] = i
                am.append((a_mh, "luoi"))
        if cho_phep and not kieu_mh:
            canh = chon_canh(thu_vien, x.get("minh_hoa"), da_dung, kh.get("sp"), 2.0 * (x["e"] - x["s"]),
                             x.get("text", ""), da_file)
            if canh:
                kieu_mh = "mot"
                for role, trk in (("mo", "mo"), ("glow", "glow")):
                    if role in tpl:
                        k.tracks[trk]["segments"].append(clone(k, tpl[role], a_mh, b_mh - a_mh))
                them_doan_video(k.tracks["broll"], canh, a_mh, b_mh)
                am.append((a_mh, "mh"))

        # ---- PHU DE theo cum nghia (ke hoach AI), dung truoc loi 0.15s, hien lien tuc toi cum sau
        ws = x["words"]
        pd = x.get("phu_de")
        if not pd:
            pd, pos = [], 0
            for cum in chia_cum(ws):
                pd.append({"tu": pos, "den": pos + len(cum) - 1, "xuong_dong": -1, "nhan": False})
                pos += len(cum)
        bd = []
        for c in pd:
            c0 = t + _us(ws[c["tu"]]["s"] - x["s"]) - _us(0.15)
            c0 = max(c0, t, (bd[-1]["s"] + _us(0.35)) if bd else 0)
            if c0 >= t + dur - _us(0.2):
                if bd:  # het cho: gop vao cum truoc
                    bd[-1]["den"] = c["den"]
                continue
            bd.append({"s": c0, **c})
        for j, c in enumerate(bd):
            c["e"] = bd[j + 1]["s"] if j + 1 < len(bd) else t + dur
        # cum NHAN (tu khoa) dung sau cum thuong -> cum thuong keo dai, tu khoa vang nghieng noi rieng
        # MOI LUC CHI 1 CAU (anh Son: chu de len nhau thi khong biet doc cau nao truoc) -> khong lop phu chong
        for c in bd:
            c["phu"] = False
        dang_dem = lambda u: any(d0 <= u < d1 for d0, d1 in dem_span)
        tren = min(y_mat, 0.40) if y_mat > 0 else y_mat
        if kieu_mh == "luoi":
            y_goc = -0.64
        elif kieu_mh == "mot":
            y_goc = 0.5 if i % 2 == 0 else -0.58
        else:
            y_goc = y_mat
        for j, c in enumerate(bd):
            cs, ce = c["s"], c["e"]
            if ce <= hook_end + _us(0.3):
                continue
            cs = max(cs, hook_end)
            # cum chi la "thu nhat / thu hai la..." ma nhan THU dang hien -> bo (khong lap chu, doc thang vao y)
            tho = " ".join(w["w"].strip() for w in ws[c["tu"]:c["den"] + 1]).lower().strip(" ,.:")
            if x.get("dem_y") and dang_dem(cs) and re.fullmatch(r"thứ\s*(nhất|hai|ba|tư|năm|\d+)(\s*(là|,))?", tho):
                if j + 1 < len(bd):
                    bd[j + 1]["s"] = cs
                continue
            dong = chia_dong([w["w"] for w in ws[c["tu"]:c["den"] + 1]], c["xuong_dong"] - c["tu"] if c["xuong_dong"] > 0 else -1)
            txt = "\n".join(viet_phu_de(l) for l in dong.split("\n")).strip(" ,")
            yb = y_goc
            if yb > 0 and dang_dem(cs):
                yb = min(yb, 0.40)
            if c["phu"]:
                ps = clone(k, tpl["tu_khoa"], cs, max(_us(0.4), ce - cs))
                set_text(clone_mat(k, ps), txt)
                base_y = bd[j - 1].get("y", yb)
                # tu khoa noi NGAY DUOI cau dan (doc tu tren xuong nhu ban anh Son: 0.40 -> 0.26)
                # 1 dong chu cao ~0.12 (toa do CapCut) -> cach = nua khoi tren + nua khoi duoi + khe 0.03
                nd, no = bd[j - 1].get("so_dong", 1), txt.count("\n") + 1
                ps["clip"]["transform"]["y"] = round(max(-0.66, base_y - 0.06 * (nd + no) - 0.03), 3)
                dat_anim(k, ps, "Trượt lên", ce - cs)
                k.tracks["chu"][-1 if len(k.tracks["chu"]) > 2 else 0]["segments"].append(ps)
                am.append((cs, "tu_khoa"))
                continue
            # Y CHINH (nhan): cau rieng, chu vang dam nghieng to hon, cung vi tri -> nhin la biet y can nho
            nhan = c["nhan"] and "tu_khoa" in tpl
            ps = clone(k, tpl["tu_khoa"] if nhan else tpl["phu_de"], cs, max(_us(0.4), ce - cs))
            kws = [] if nhan else [kw for kw in x.get("tu_khoa", []) if kw.lower() in txt.lower()]
            set_text(clone_mat(k, ps), txt, kws, color=YELLOW if c["nhan"] else None)
            if nhan:
                sc0 = tpl["phu_de"]["clip"]["scale"]["x"]
                ps["clip"]["scale"] = {"x": round(sc0 * 1.2, 3), "y": round(sc0 * 1.2, 3)}
            c["y"] = round(yb, 3)   # vi tri co dinh trong doan
            c["so_dong"] = txt.count("\n") + 1
            if j + 1 < len(bd) and bd[j + 1]["phu"]:
                # chua cho tu khoa ben duoi: day cau dan len neu khoi tu khoa se lot xuong qua -0.66
                no = chia_dong([w["w"] for w in ws[bd[j + 1]["tu"]:bd[j + 1]["den"] + 1]]).count("\n") + 1
                du = -0.66 - (c["y"] - 0.06 * (c["so_dong"] + no) - 0.03)
                if du > 0:
                    c["y"] = round(c["y"] + du, 3)
            c["y"] = max(c["y"], -0.66 + 0.06 * (c["so_dong"] - 1))
            ps["clip"]["transform"]["y"] = c["y"]
            ten_anim = ANIM_XOAY[st["anim"] % len(ANIM_XOAY)]
            st["anim"] += 1
            if len(txt) <= 10 and ten_anim == "Loại xem trước":
                ten_anim = "Bật lên"   # cum ngan: hien ngay cho doc kip
            if nhan:
                ten_anim = "Trượt lên"
            dat_anim(k, ps, ten_anim, ce - cs)
            k.tracks["chu"][-1 if len(k.tracks["chu"]) > 2 else 0]["segments"].append(ps)
            am.append((cs, "tu_khoa" if c["nhan"] else "go"))

        # so thu tu to ben phai cho muc trong danh sach con (1-2-3 giai doan)
        if x.get("so") and "so" in tpl:
            ss = clone(k, tpl["so"], t + _us(0.1), min(dur, _us(3.0)) - _us(0.1))
            set_text(clone_mat(k, ss), str(x["so"]))
            k.tracks["chu"][0]["segments"].append(ss)
            am.append((t + _us(0.1), "so"))

        moi_y = x.get("dem_y") and (i == 0 or kh["doan"][i - 1].get("dem_y") != x["dem_y"])
        if moi_y and "dem_y" in tpl:
            so_y += 1
            nhan = {1: "THỨ NHẤT", 2: "THỨ HAI", 3: "THỨ BA", 4: "THỨ TƯ"}.get(x["dem_y"], f"THỨ {x['dem_y']}")
            # 1 nhan cho ca y: keo dai qua cac doan lien sau cung so y
            span = dur
            for y in kh["doan"][i + 1:]:
                if y.get("dem_y") != x["dem_y"]:
                    break
                span += _us(y["e"] - y["s"])
            ds = clone(k, tpl["dem_y"], t, span)
            set_text(clone_mat(k, ds), nhan)
            k.tracks["chu"][0]["segments"].append(ds)
            am.append((t, "dem_y"))
        if x["vai"] == "keu_goi" and i == len(kh["doan"]) - 1:
            am.append((t, "ding"))
        t += dur

    total = t
    # chu mo dau
    hook = kh.get("chu_mo_dau", [])
    if hook:
        h1 = clone(k, tpl["mo_dau_1"], 0, hook_end)
        dong1 = ngat_dong(hook[0].upper())
        set_text(clone_mat(k, h1), dong1)
        k.tracks["chu"][0]["segments"].insert(0, h1)
        am.append((0, "hook1"))
        if len(hook) > 1 and "mo_dau_2" in tpl:
            h2 = clone(k, tpl["mo_dau_2"], _us(1.0), hook_end - _us(1.0))
            dong2 = ngat_dong(hook[1].upper())
            set_text(clone_mat(k, h2), dong2)
            # 2 dong chu mo dau KHONG chong nhau: dong do nam duoi khoi chu trang, cach theo so dong that
            n1 = dong1.count("\n") + 1
            h2["clip"]["transform"]["y"] = round(h1["clip"]["transform"]["y"] - 0.085 * n1 - 0.045, 3)
            k.tracks["chu"][1 if len(k.tracks["chu"]) > 1 else 0]["segments"].insert(0, h2)
            am.append((_us(1.0), "hook2"))

    # tieng hieu ung: chon ten xoay vong, xep vao cac lop am, khong de chong
    end_of = {id(tr): 0 for tr in sfx_tracks}
    for at, name in chon_am(list(sfx_tpl), am):
        mau = sfx_tpl.get(nfc(name))
        if not mau or not sfx_tracks:
            continue
        ln = mau["target_timerange"]["duration"]
        tr = next((tr for tr in sfx_tracks if end_of[id(tr)] <= at), None)
        if tr is None:
            continue
        s = clone(k, mau, at, min(ln, max(0, total - at)))
        if s["target_timerange"]["duration"] <= 0:
            continue
        tr["segments"].append(s)
        end_of[id(tr)] = at + ln

    # xep lai chu vao cac lop chu: doan chong thoi gian (phu de + tu khoa noi + THU/so) phai o lop khac nhau
    txt_tracks = k.tracks.get("chu", [])
    if txt_tracks:
        segs = sorted([sg for tr in txt_tracks for sg in tr["segments"]], key=lambda sg: sg["target_timerange"]["start"])
        for tr in txt_tracks:
            tr["segments"] = []
        ends = [0] * len(txt_tracks)
        for sg in segs:
            a0 = sg["target_timerange"]["start"]
            j = next((j for j, e in enumerate(ends) if e <= a0), None)
            if j is None:
                nt = copy.deepcopy({kk: vv for kk, vv in txt_tracks[0].items() if kk != "segments"})
                nt["id"] = _uid()
                nt["segments"] = []
                d["tracks"].insert(d["tracks"].index(txt_tracks[-1]) + 1, nt)
                txt_tracks.append(nt)
                ends.append(0)
                j = len(ends) - 1
            txt_tracks[j]["segments"].append(sg)
            ends[j] = a0 + sg["target_timerange"]["duration"]

    # nhac nen + lop keo dai
    if "nhac" in tpl:
        ms = clone(k, tpl["nhac"], 0, total)
        ms["source_timerange"] = {"start": tpl["nhac"]["source_timerange"]["start"], "duration": total}
        k.tracks["nhac"]["segments"].append(ms)
    for tr in k.tracks.get("keo_dai", []):
        tr["segments"] = tr["segments"][:1]
        tr["segments"][0]["target_timerange"] = {"start": 0, "duration": total}
    for tr in d["tracks"]:
        tr["segments"].sort(key=lambda s: s["target_timerange"]["start"])
    d["tracks"] = [tr for tr in d["tracks"] if tr["segments"]]
    k.dr.prune()
    d["duration"] = total
    return total


def _don_vat_lieu(d):
    """Bo video/am thanh cua khuon khong con doan nao dung (tranh CapCut bao 'thieu file' tren may khac)."""
    dung = set()
    for t in d["tracks"]:
        for s in t["segments"]:
            dung.add(s.get("material_id"))
            dung.update(s.get("extra_material_refs", []))
    for k in ("videos", "audios"):
        lst = d["materials"].get(k)
        if isinstance(lst, list):
            d["materials"][k] = [m for m in lst if m.get("id") in dung]


def thu_muc_khuon(khuon):
    """Khuon = duong dan thu muc (goi phong cach da cai) | ten du an trong CapCut | mac dinh goi da cai (SONIX_KHUON)."""
    if khuon and os.path.isabs(str(khuon)) and Path(khuon).is_dir():
        return Path(khuon)
    goi = os.environ.get("SONIX_KHUON")
    if not khuon and goi:
        return Path(goi) / "khuon"
    return drafts_dir() / (khuon or "DAMBOTC01_SONIX")


def tao(kh_path, video_goc, ten, khuon=None, timeline=None, thu_vien_path=None):
    if capcut_dang_mo():
        raise CapCutError("CapCut đang mở. Bác tắt CapCut rồi chạy lại.")
    root = drafts_dir()
    src = thu_muc_khuon(khuon)
    if not (src / "draft_content.json").exists():
        raise CapCutError(f"Không thấy khuôn {src}. Cài gói phong cách Sơn 01 trước.")
    tid, tname = None, None
    lay = src / "timeline_layout.json"
    cpath = src / "draft_content.json"
    if lay.exists():
        L = json.loads(lay.read_text(encoding="utf-8"))["dockItems"][0]
        pairs = list(zip(L["timelineIds"], L["timelineNames"]))
        tid, tname = next(((a, b) for a, b in pairs if timeline and nfc(b) == nfc(timeline)), pairs[0])
        if (src / "Timelines" / tid / "draft_content.json").exists():
            cpath = src / "Timelines" / tid / "draft_content.json"
        else:
            tid = None
    d = json.loads(cpath.read_text(encoding="utf-8"))
    kh = json.loads(Path(kh_path).read_text(encoding="utf-8"))
    tv = json.loads(Path(thu_vien_path).read_text(encoding="utf-8")) if thu_vien_path and os.path.exists(thu_vien_path) else None
    k = Khuon(d)
    total = build(kh, video_goc, k, tv)
    _don_vat_lieu(d)

    root.mkdir(parents=True, exist_ok=True)
    base, n = ten, 2
    while (root / ten).exists():
        ten, n = f"{base} ({n})", n + 1
    dst = root / ten
    dst.mkdir(parents=True)
    BO = {"Timelines", "matting", "qr_upload", "smart_crop", "adjust_mask", ".locked", "timeline_layout.json", "goi.json"}
    for p in src.iterdir():
        if p.name in BO or p.name.endswith((".bak", ".tmp")):
            continue
        (shutil.copytree if p.is_dir() else shutil.copy2)(p, dst / p.name)
    content = json.dumps(d, ensure_ascii=False)
    old = str(src).replace("\\", "/")
    content = content.replace(old + "/", str(dst).replace("\\", "/") + "/")
    (dst / "draft_content.json").write_text(content, encoding="utf-8")
    if tid:
        tdir = dst / "Timelines" / tid
        tdir.mkdir(parents=True)
        for f in (src / "Timelines" / tid).iterdir():
            if f.is_file() and not f.name.endswith((".bak", ".tmp")) and f.name != "draft_content.json":
                shutil.copy2(f, tdir / f.name)
        (tdir / "draft_content.json").write_text(content, encoding="utf-8")
        lay2 = json.loads(lay.read_text(encoding="utf-8"))
        lay2["dockItems"] = [{"dockIndex": 0, "ratio": 1, "timelineIds": [tid], "timelineNames": ["Sơn 01"]}]
        (dst / "timeline_layout.json").write_text(json.dumps(lay2, ensure_ascii=False), encoding="utf-8")
        # Timelines/project.json: thieu file nay CapCut KHONG mo duoc du an (id timeline chinh = id noi dung)
        pj_src = src / "Timelines" / "project.json"
        pj = json.loads(pj_src.read_text(encoding="utf-8")) if pj_src.exists() else {
            "config": {"color_space": -1, "hdr_vivid": False, "mixed_track_mode_on": False,
                       "render_index_track_mode_on": False, "use_float_render": False}, "version": 0}
        t_now = int(time.time() * US)
        pj.update({"id": _uid(), "create_time": t_now, "update_time": t_now, "main_timeline_id": tid,
                   "timelines": [{"create_time": t_now, "id": tid, "is_marked_delete": False, "name": "Sơn 01",
                                  "update_time": t_now}]})
        (dst / "Timelines" / "project.json").write_text(json.dumps(pj, ensure_ascii=False), encoding="utf-8")
        if d.get("id") != tid:  # id noi dung phai trung id timeline chinh
            d["id"] = tid
            content = json.dumps(d, ensure_ascii=False).replace(old + "/", str(dst).replace("\\", "/") + "/")
            (dst / "draft_content.json").write_text(content, encoding="utf-8")
            (tdir / "draft_content.json").write_text(content, encoding="utf-8")

    now = int(time.time() * US)
    new_id = _uid()
    reset = {"tm_draft_cloud_entry_id": -1, "tm_draft_cloud_parent_entry_id": -1, "tm_draft_cloud_space_id": -1,
             "tm_draft_cloud_user_id": -1, "tm_draft_cloud_modified": 0, "cloud_draft_sync": False}
    fold = str(dst).replace("\\", "/")
    mp = dst / "draft_meta_info.json"
    meta = json.loads(mp.read_text(encoding="utf-8"))
    meta.update(reset)
    meta.update({"draft_id": new_id, "draft_name": ten, "draft_fold_path": fold,
                 "draft_root_path": str(root).replace("\\", "/"),
                 "tm_draft_create": now, "tm_draft_modified": now, "tm_duration": total})
    mp.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    # dang ky du an vao danh sach CapCut (root_meta_info.json)
    ROOT_DIR.mkdir(parents=True, exist_ok=True)
    rp = ROOT_DIR / "root_meta_info.json"
    if rp.exists():
        shutil.copy2(rp, ROOT_DIR / "root_meta_info.json.sonix_backup")
        r = json.loads(rp.read_text(encoding="utf-8"))
    else:
        r = {"all_draft_store": [], "draft_ids": 0, "root_path": str(root).replace("\\", "/")}
    r.setdefault("all_draft_store", [])
    goi_json = src / "goi.json"
    mau = json.loads(goi_json.read_text(encoding="utf-8")).get("entry") if goi_json.exists() else None
    cu = next((x for x in r["all_draft_store"] if x.get("draft_name") == (khuon or "")), None)
    e = copy.deepcopy(cu or mau or (r["all_draft_store"][0] if r["all_draft_store"] else {}))
    e.update(reset)
    e.update({"draft_id": new_id, "draft_name": ten, "draft_fold_path": fold,
              "draft_root_path": str(root).replace("\\", "/"),
              "draft_json_file": str(dst / "draft_content.json").replace("\\", "/"),
              "draft_cover": str(dst / "draft_cover.jpg").replace("\\", "/"),
              "tm_draft_create": now, "tm_draft_modified": now, "tm_duration": total})
    r["all_draft_store"].insert(0, e)
    tmp = rp.with_suffix(".json.sonix_tmp")
    tmp.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, rp)
    return {"ten": ten, "thu_muc": str(dst), "giay": total / US, "timeline_khuon": tname,
            "so_doan": len(kh["doan"]), "vai_tim_thay": sorted(k.role), "am_co": sorted(k.sfx)}


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = dict(zip(a[3::2], a[4::2]))
    kq = tao(a[0], a[1], a[2], opt.get("--khuon"), opt.get("--timeline"), opt.get("--thu-vien"))
    print(json.dumps(kq, ensure_ascii=False, indent=1))
