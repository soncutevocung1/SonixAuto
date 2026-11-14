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
        i = low.find(nfc(kw).lower())
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


def ngat_dong(txt, toi_da=18):
    """Chu mo dau: ngat dong chu dong (<= toi_da ky tu/dong) de CapCut khong tu xuong dong chong chu."""
    dong, cur = [], ""
    for w in txt.split():
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


def kiem_canh(c, sp, dung_giay):
    """Soi 3 khung (dau/giua/cuoi) cua DUNG doan se dung: co mat nguoi lon, chu in san, hoac
    chu san pham khac -> loai. Ket qua luu vao canh (khong soi lai)."""
    key = f"kiem_{sp}_{round(dung_giay, 1)}"
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
        if any(d.bounding_box.height > 0.05 * h for d in _face().detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)).detections):
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


def chon_canh(thu_vien, nhan, da_dung, sp=None, dung_giay=3.0):
    """Chon canh dung nhan, bo canh 'loai' va canh co SAN PHAM KHAC; soi lai 3 khung truoc khi nhan."""
    if not thu_vien or not nhan:
        return None
    cam = (SP_TAGS - {sp}) if sp else set()
    cands = [c for c in thu_vien if nhan in c.get("nhan", []) and "loai" not in c.get("nhan", [])
             and not (cam & set(c.get("nhan", []))) and c["id"] not in da_dung]
    # uu tien canh co dung san pham cua video, roi den canh dai (du cho toc do 2x)
    cands.sort(key=lambda c: (-(sp in c.get("nhan", [])), -min(c["dai"], 8)))
    for c in cands[:8]:
        if kiem_canh(c, sp, dung_giay):
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
    am = []          # (thoi diem us, ten am)
    da_dung = set()
    so_y = 0
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

        # phu de theo cum: vi tri theo mat nguoi mau o giua doan (tinh ca zoom)
        zs = s["clip"]["scale"]["x"]
        y_mat = vi_tri_phu_de(video_goc, (x["s"] + x["e"]) / 2, zs) if video_goc else 0.42
        x["y_phu_de"] = y_mat
        co_mh = False
        # Doan mo dau giu mat nguoi mau (tao tin tuong) -> khong chen minh hoa trong ~4 giay dau
        cho_phep = x["vai"] not in ("mo_dau", "keu_goi") and t >= _us(4.0) and x["e"] - x["s"] >= 1.2
        canh = chon_canh(thu_vien, x.get("minh_hoa"), da_dung, kh.get("sp"), 2.0 * (x["e"] - x["s"])) if cho_phep else None
        if canh and "broll" in k.role:
            co_mh = True
            da_dung.add(canh["id"])
            a = t + _us(0.25)
            b = t + dur
            for role, trk in (("mo", "mo"), ("glow", "glow")):
                if role in tpl:
                    k.tracks[trk]["segments"].append(clone(k, tpl[role], a, b - a))
            bs = clone(k, tpl["broll"], a, b - a)
            need = (b - a) / US
            toc = max(0.5, min(2.0, canh["dai"] / need))
            src = canh["file"].replace("\\", "/")
            clone_mat(k, bs, path=src, material_name=Path(src).name, width=canh["w"], height=canh["h"],
                      duration=_us(canh["e"] + 1))
            bs["source_timerange"] = {"start": _us(canh["s"]), "duration": _us(need * toc)}
            bs["speed"] = toc
            for r in bs.get("extra_material_refs", []):
                kk, m = k.find(r)
                if kk == "speeds":
                    m["speed"] = toc
            k.tracks["broll"]["segments"].append(bs)
            am.append((a, "Cute notification sound 09 / Youtube / TV(935743)"))

        cums = chia_cum(x["words"])
        for ci, cum in enumerate(cums):
            cs = t + _us(cum[0]["s"] - x["s"])
            ce = t + _us(cum[-1]["e"] - x["s"]) + _us(0.08)
            ce = min(ce, t + dur)
            if ci + 1 < len(cums):  # dong truoc tat truoc khi dong sau hien -> khong chong chu
                ce = min(ce, t + _us(cums[ci + 1][0]["s"] - x["s"]) - _us(0.02))
            # Khong de phu de chong len chu mo dau (anh Son de trong 2-3 giay dau)
            if ce <= hook_end + _us(0.3):
                continue
            cs = max(cs, hook_end)
            txt = viet_phu_de(" ".join(w["w"] for w in cum).strip(" ,"))
            kws = [kw for kw in x.get("tu_khoa", []) if kw.lower() in txt.lower()]
            ps = clone(k, tpl["phu_de"], cs, max(_us(0.3), ce - cs))
            m = clone_mat(k, ps)
            set_text(m, txt, kws)
            # luc nhan "THU NHAT/HAI/BA" dang hien tren dau -> phu de xuong duoi cam (khong chong chu)
            dang_dem = any(d0 <= cs < d1 for d0, d1 in dem_span)
            y_pd = -0.18 if dang_dem else y_mat
            ps["clip"]["transform"]["y"] = -0.56 if co_mh else y_pd
            k.tracks["chu"][-1 if len(k.tracks["chu"]) > 2 else 0]["segments"].append(ps)
            # Tieng: tu khoa -> "ting"; cum dau doan hoac cach 2 cum -> go phim (khong de am day dac)
            if kws:
                am.append((cs, "得分"))
            elif ci == 0 or ci % 2 == 0 and cs - last_go[0] > _us(1.2):
                am.append((cs, "Realistic sound effects for typing on keyboards"))
                last_go[0] = cs

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
            am.append((t, "Cute system Pyui"))
        if x["vai"] == "keu_goi" and i == len(kh["doan"]) - 1:
            am.append((t, "Ding"))
        t += dur

    total = t
    # chu mo dau
    hook = kh.get("chu_mo_dau", [])
    if hook:
        h1 = clone(k, tpl["mo_dau_1"], 0, hook_end)
        dong1 = ngat_dong(hook[0].upper())
        set_text(clone_mat(k, h1), dong1)
        k.tracks["chu"][0]["segments"].insert(0, h1)
        am.append((0, "Magic reveal"))
        if len(hook) > 1 and "mo_dau_2" in tpl:
            h2 = clone(k, tpl["mo_dau_2"], _us(1.0), hook_end - _us(1.0))
            set_text(clone_mat(k, h2), ngat_dong(hook[1].upper()))
            # dong do nam ngay duoi khoi chu trang: doi xuong theo so dong cua dong 1 (khuon tinh cho 1 dong)
            h2["clip"]["transform"]["y"] = h1["clip"]["transform"]["y"] - 0.075 * (dong1.count("\n") + 1) - 0.03
            k.tracks["chu"][1 if len(k.tracks["chu"]) > 1 else 0]["segments"].insert(0, h2)
            am.append((_us(1.0), "滴滴 答题错误"))

    # tieng hieu ung: xep vao cac lop am, khong de chong
    end_of = {id(tr): 0 for tr in sfx_tracks}
    for at, name in sorted(am):
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
