"""Cat tho v2 - hoc theo cach anh Son cat (xem core/son01/LUAT_CAT_ANH_SON.md).

1) NHIN HINH (MediaPipe, chay tren may): moi 0.2s do dien thoai trong khung + huong mat (cui xuong / khuat mat)
   -> danh dau doan "dang doc kich ban" de BO.
2) NGHE KY: Silero VAD (onnx) tim dao tieng noi -> faster-whisper nghe tung dao (khong bo sot loi),
   moc tung chu; tinh chinh dau/cuoi cau theo nang luong am (khong cut chu).
3) TACH CAU theo khoang lang, gan ti le "dang doc" cho tung cau.
4) CHON LAN NOI: Claude xem toan bo cac cau (ca lan noi lai o xa), chon 1 lan tot nhat cho moi y
   (tron cau, khong vap, nhin ong kinh; ngang nhau thi lay lan CUOI), giu dung mach.

python cat_tho2.py <video> <ra_cat.json> [--lam-viec thu_muc] [--model claude-opus-5-5] [--whisper large-v3-turbo]
Ra: cat.json [{s, e, text, words, id_cau}] (cung dinh dang cat_tho.py) + nhin.json, nghe.json, cau.json, chon.json
"""
import sys, os, json, math, subprocess, tempfile
import numpy as np
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.environ.get("SONIX_APP") or os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, APP)
FF = os.environ.get("SONIX_FFMPEG") or __import__("imageio_ffmpeg").get_ffmpeg_exe()
MODELS = os.environ.get("SONIX_MODELS") or os.path.join(APP, "data", "son01", "models")
URL = {
    "efficientdet_lite0.tflite": "https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/float32/latest/efficientdet_lite0.tflite",
    "face_landmarker.task": "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task",
    "silero_vad.onnx": "https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx",
}
SR = 16000


def model(n):
    p = os.path.join(MODELS, n)
    if not os.path.exists(p):
        import urllib.request
        os.makedirs(MODELS, exist_ok=True)
        print("tai model", n, flush=True)
        urllib.request.urlretrieve(URL[n], p + ".tmp")
        os.replace(p + ".tmp", p)
    return p


def probe(video):
    p = subprocess.run([FF, "-i", video], capture_output=True, text=True, encoding="utf-8", errors="ignore")
    import re
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", p.stderr)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


# ---------------------------------------------------------------- 1) nhin hinh
def nhin(video, buoc=0.2, w=1080, vung=(0.2, 0.14, 0.6, 0.42)):
    """vung: (x, y, rong, cao) theo ti le khung - vung nguoi ngoi; cat rieng de mat du lon cho model."""
    import mediapipe as mp
    from mediapipe.tasks.python import vision, BaseOptions
    det = vision.ObjectDetector.create_from_options(vision.ObjectDetectorOptions(
        base_options=BaseOptions(model_asset_path=model("efficientdet_lite0.tflite")),
        score_threshold=0.2, max_results=8, category_allowlist=["cell phone", "remote"]))
    lm = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model("face_landmarker.task")),
        output_facial_transformation_matrixes=True, output_face_blendshapes=True, num_faces=1,
        min_face_detection_confidence=0.3))
    dur = probe(video)
    h = None
    x0, y0, cw, ch = vung
    crop = f"scale={w}:-2,crop=trunc(iw*{cw}/2)*2:trunc(ih*{ch}/2)*2:iw*{x0}:ih*{y0}"
    info = subprocess.run([FF, "-v", "error", "-i", video, "-vf", crop, "-frames:v", "1", "-f", "rawvideo",
                           "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    w = int(w * cw / 2) * 2
    h = len(info) // (w * 3)
    cmd = [FF, "-v", "error", "-i", video, "-vf", f"fps={1 / buoc}," + crop, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    out, i = [], 0
    while True:
        b = p.stdout.read(w * h * 3)
        if len(b) < w * h * 3:
            break
        img = np.frombuffer(b, np.uint8).reshape(h, w, 3)
        mi = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(img))
        ph = max([d.categories[0].score for d in det.detect(mi).detections] or [0.0])
        r = lm.detect(mi)
        pitch = yaw = None
        mat_xuong = 0.0
        if r.face_blendshapes:
            bs = {c.category_name: c.score for c in r.face_blendshapes[0]}
            mat_xuong = (bs.get("eyeLookDownLeft", 0) + bs.get("eyeLookDownRight", 0)) / 2
        if r.facial_transformation_matrixes:
            M = np.array(r.facial_transformation_matrixes[0])[:3, :3]
            pitch = math.degrees(math.atan2(M[2, 1], M[2, 2]))
            yaw = math.degrees(math.asin(max(-1, min(1, -M[2, 0]))))
        out.append({"t": round(i * buoc, 2), "phone": round(ph, 3), "mat": r.facial_transformation_matrixes != [], "mat_xuong": round(mat_xuong, 2),
                    "pitch": None if pitch is None else round(pitch, 1), "yaw": None if yaw is None else round(yaw, 1)})
        i += 1
    p.wait()
    return {"buoc": buoc, "dur": dur, "khung": out}


def danh_dau_doc(nh, nguong_phone=0.35, nguong_cui=None):
    """1 = dang doc kich ban (dien thoai / cui mat / khuat mat). Lam muot 1.0s.
    nguong_cui: goc pitch coi la cui; None -> tu hieu chinh theo phan bo (mat nhin thang chiem da so)."""
    K = nh["khung"]
    ps = [k["pitch"] for k in K if k["pitch"] is not None]
    if nguong_cui is None and ps:
        med = float(np.percentile(ps, 20))   # tu the nhin ong kinh (nhom ngang dau)
        nguong_cui = med + 6.5               # C3420: noi -5.4..0.8 do (p10-p90), doc dien thoai toi 11 do
        nh["pitch_trung_vi"] = med
    raw = []
    for k in K:
        cui = k["pitch"] is not None and nguong_cui is not None and k["pitch"] > nguong_cui
        xuong = k.get("mat_xuong", 0) >= 0.65
        raw.append(1.0 if (k["phone"] >= nguong_phone or not k["mat"] or cui or xuong) else 0.0)
    n = max(1, int(round(1.0 / nh["buoc"])))
    sm = [float(np.mean(raw[max(0, i - n // 2): i + n // 2 + 1])) for i in range(len(raw))]
    nh["nguong_cui"] = nguong_cui
    return [1 if v >= 0.5 else 0 for v in sm]


# ---------------------------------------------------------------- 2) nghe ky
def am_thanh(video):
    wav = os.path.join(tempfile.gettempdir(), "sonix_v2.raw")
    subprocess.run([FF, "-v", "error", "-y", "-i", video, "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", wav], check=True)
    return np.fromfile(wav, dtype=np.int16).astype(np.float32) / 32768


def vad(a, nguong=0.45, min_noi=0.25, min_lang=0.30, dem=0.15):
    import onnxruntime as ort
    s = ort.InferenceSession(model("silero_vad.onnx"), providers=["CPUExecutionProvider"])
    state = np.zeros((2, 1, 128), np.float32)
    sr = np.array(SR, dtype=np.int64)
    N, ctx = 512, 64
    prev = np.zeros(ctx, np.float32)
    probs = []
    for i in range(0, len(a) - N, N):
        x = np.concatenate([prev, a[i:i + N]])[None, :]
        o, state = s.run(None, {"input": x, "state": state, "sr": sr})
        prev = a[i + N - ctx: i + N]
        probs.append(float(o[0][0]))
    dt = N / SR
    seg, on, st = [], False, 0
    for i, pr in enumerate(probs):
        t = i * dt
        if pr >= nguong and not on:
            on, st = True, t
        elif pr < nguong - 0.15 and on:
            on = False
            seg.append([st, t])
    if on:
        seg.append([st, len(probs) * dt])
    gop = []
    for s0, e0 in seg:
        if gop and s0 - gop[-1][1] < min_lang:
            gop[-1][1] = e0
        else:
            gop.append([s0, e0])
    return [[max(0, s0 - dem), e0 + dem] for s0, e0 in gop if e0 - s0 >= min_noi]


def nghe(video, a, dao, ten_model="large-v3-turbo"):
    from faster_whisper import WhisperModel
    m = WhisperModel(ten_model, device="cpu", compute_type="int8")
    clips = [x for d in dao for x in d]
    segs, _ = m.transcribe(a, language="vi", word_timestamps=True, vad_filter=False, clip_timestamps=clips,
                           condition_on_previous_text=False, beam_size=5, temperature=[0, 0.4],
                           no_speech_threshold=0.6)
    words = []
    for s in segs:
        if s.no_speech_prob > 0.7:
            continue
        for w in s.words or []:
            words.append({"w": w.word, "s": round(w.start, 3), "e": round(w.end, 3), "p": round(w.probability, 3)})
    return words


def tinh_chinh(a, s, e, lui=0.25, toi=0.45):
    """Dau cau: lui ve cho nang luong thap nhat trong 'lui' giay truoc; cuoi cau: ra den khi am tat han (<= 'toi')."""
    hop = int(0.01 * SR)
    def rms(t0, t1):
        i0, i1 = max(0, int(t0 * SR)), min(len(a), int(t1 * SR))
        x = a[i0:i1]
        n = len(x) // hop
        return np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12) if n else np.zeros(1)
    nen = float(np.percentile(rms(max(0, s - 2), e + 2), 10)) * 2.2
    r = rms(s - lui, s)
    k = len(r) - 1
    while k > 0 and r[k] > nen:
        k -= 1
    s2 = s - lui + k * 0.01
    r = rms(e, e + toi)
    k = 0
    while k < len(r) - 1 and r[k] > nen:
        k += 1
    e2 = e + k * 0.01 + 0.06
    return round(max(0, s2), 3), round(e2, 3)


# ---------------------------------------------------------------- 3) tach cau
def tach_cau(words, doc, buoc, a, gap=0.45):
    cau, cur = [], []
    for w in words:
        if cur and w["s"] - cur[-1]["e"] >= gap:
            cau.append(cur); cur = []
        cur.append(w)
    if cur:
        cau.append(cur)
    out = []
    for i, c in enumerate(cau):
        s, e = tinh_chinh(a, c[0]["s"], c[-1]["e"])
        i0, i1 = int(s / buoc), max(int(s / buoc) + 1, int(e / buoc))
        d = doc[i0:i1] or [0]
        out.append({"id": i, "s": s, "e": e, "text": " ".join(x["w"].strip() for x in c).strip(), "words": c,
                    "doc": round(float(np.mean(d)), 2), "p": round(float(np.mean([x["p"] for x in c])), 2)})
    return out


# ---------------------------------------------------------------- 3b) Claude xem hinh tung cau
def kiem_hinh_ai(video, cau, model_ai="claude-sonnet-5-5", lo=12, vung=(0.2, 0.14, 0.6, 0.42)):
    """Moi cau 3 khung (25/50/75%) vung nguoi ngoi -> Claude: dang cam/nhin dien thoai? nhin ong kinh?"""
    import base64
    from core import config
    from core.analyze import _claude
    x0, y0, cw, ch = vung
    tmp = tempfile.mkdtemp(prefix="sx_kh_")
    schema = {"type": "object", "properties": {"cau": {"type": "array", "items": {"type": "object", "properties": {
        "id": {"type": "integer"}, "dien_thoai": {"type": "boolean"}, "nhin_ong_kinh": {"type": "boolean"}},
        "required": ["id", "dien_thoai", "nhin_ong_kinh"], "additionalProperties": False}}},
        "required": ["cau"], "additionalProperties": False}
    kq = {}
    for b in range(0, len(cau), lo):
        nhom = cau[b:b + lo]
        anh = []
        for c in nhom:
            for k, r in enumerate((0.25, 0.5, 0.75)):
                t = c["s"] + (c["e"] - c["s"]) * r
                p = os.path.join(tmp, f"{c['id']}_{k}.jpg")
                subprocess.run([FF, "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-vf",
                                f"scale=1080:-2,crop=iw*{cw}:ih*{ch}:iw*{x0}:ih*{y0},scale=200:-2,"
                                f"drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':text='{c['id']}':x=4:y=4:fontsize=26:"
                                f"fontcolor=yellow:box=1:boxcolor=black", p])
        sheet = os.path.join(tmp, f"bang_{b}.jpg")
        lst = os.path.join(tmp, f"ds_{b}.txt")
        files = [os.path.join(tmp, f"{c['id']}_{k}.jpg") for c in nhom for k in range(3)]
        ins = []
        for f_ in files:
            ins += ["-i", f_]
        n = len(files)
        subprocess.run([FF, "-v", "error", "-y", *ins, "-filter_complex",
                        "".join(f"[{i}]" for i in range(n)) + f"xstack=inputs={n}:grid={6}x{-(-n // 6)}:fill=black"
                        if n > 1 else "null", "-frames:v", "1", sheet])
        b64 = base64.b64encode(open(sheet, "rb").read()).decode()
        content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                   {"type": "text", "text": "Mỗi câu có 3 ảnh liền nhau, số vàng góc trái là id câu. Với từng id: "
                    "dien_thoai = người trong ảnh đang CẦM hoặc NHÌN điện thoại (đọc kịch bản) ở phần lớn các ảnh; "
                    "nhin_ong_kinh = mặt ngẩng nhìn thẳng ống kính, tay không cầm điện thoại. Các id: "
                    + ", ".join(str(c["id"]) for c in nhom)}]
        r = _claude(content, schema, config.load_settings(), model_ai,
                    "Bạn kiểm tra khung hình video quay thô. Trả lời chính xác theo ảnh.")
        for x in r.get("cau", []):
            kq[x["id"]] = x
        print(f"   xem hinh cau {b}-{b + len(nhom) - 1}", flush=True)
    for c in cau:
        x = kq.get(c["id"])
        if x:
            c["dien_thoai_ai"] = bool(x["dien_thoai"])
            c["nhin_ong_kinh"] = bool(x["nhin_ong_kinh"])
            if x["dien_thoai"]:
                c["doc"] = max(c["doc"], 0.9)
            elif x["nhin_ong_kinh"]:
                c["doc"] = min(c["doc"], 0.2)
    return cau


# ---------------------------------------------------------------- 4) chon lan noi (Claude)
LUAT = open(os.path.join(HERE, "..", "LUAT_CAT_ANH_SON.md"), encoding="utf-8").read() \
    if os.path.exists(os.path.join(HERE, "..", "LUAT_CAT_ANH_SON.md")) else ""
SCHEMA = {"type": "object", "properties": {
    "y": {"type": "array", "items": {"type": "object", "properties": {
        "y": {"type": "string"},
        "cau": {"type": "array", "items": {"type": "integer"}},
        "ly_do": {"type": "string"}}, "required": ["y", "cau", "ly_do"], "additionalProperties": False}},
    "nhan_xet": {"type": "string"}}, "required": ["y", "nhan_xet"], "additionalProperties": False}


def chon(cau, model_ai="claude-opus-5-5", dai=36):
    from core import config
    from core.analyze import _claude
    dong = []
    for c in cau:
        dong.append(f"#{c['id']} [{c['s']:.1f}-{c['e']:.1f}s, {c['e'] - c['s']:.1f}s] "
                    f"doc_dien_thoai={int(c['doc'] * 100)}% ro={int(c['p'] * 100)}% | {c['text']}")
    system = ("Bạn là biên tập viên cắt source thô cho anh Sơn. Đây là LUẬT anh Sơn cắt (học từ bài anh tự cắt):\n"
              + LUAT + "\n\nNhiệm vụ: từ danh sách câu (theo thời gian thật của video quay thô), dựng lại KỊCH BẢN anh "
              "muốn nói: chia thành các Ý theo đúng thứ tự, mỗi Ý chọn đúng 1 LẦN NÓI tốt nhất "
              "(có thể là 1 câu hoặc vài câu LIỀN NHAU thuộc cùng 1 lần nói). "
              "Bắt buộc: bỏ mọi câu có doc_dien_thoai >= 40% (đang đọc kịch bản); không chọn câu nói dở/thiếu chữ cuối; "
              "ý nào nói nhiều lần thì so sánh tất cả các lần (kể cả cách xa) và lấy lần trọn vẹn, trôi chảy; "
              "ngang nhau thì lấy lần SAU CÙNG. Mỗi ý chỉ xuất hiện 1 lần. Tổng thời lượng khoảng "
              f"{dai:.0f} giây (30-42). Lời có thể bị nghe nhầm chữ, hãy hiểu theo ngữ cảnh ngành phân bón.")
    kq = _claude([{"type": "text", "text": "Danh sách câu:\n" + "\n".join(dong)}], SCHEMA, config.load_settings(),
                 model_ai, system)
    return kq


def ghep(cau, kq):
    by = {c["id"]: c for c in cau}
    out = []
    for y in kq["y"]:
        ids = [i for i in y["cau"] if i in by]
        if not ids:
            continue
        # gom cac cau lien nhau thanh 1 doan
        nhom = [[ids[0]]]
        for i in ids[1:]:
            if i == nhom[-1][-1] + 1 and by[i]["s"] - by[nhom[-1][-1]]["e"] < 1.2:
                nhom[-1].append(i)
            else:
                nhom.append([i])
        for g in nhom:
            cs = [by[i] for i in g]
            out.append({"s": cs[0]["s"], "e": cs[-1]["e"], "text": " ".join(c["text"] for c in cs),
                        "words": [w for c in cs for w in c["words"]], "id_cau": g, "y": y["y"]})
    return out


def main():
    a_ = sys.argv[1:]
    video, ra = a_[0], a_[1]
    opt = dict(zip(a_[2::2], a_[3::2]))
    lv = opt.get("--lam-viec") or os.path.dirname(os.path.abspath(ra))
    os.makedirs(lv, exist_ok=True)
    pj = lambda n: os.path.join(lv, n)
    if os.path.exists(pj("nhin.json")):
        nh = json.load(open(pj("nhin.json"), encoding="utf-8"))
    else:
        print("1/4 Nhin hinh (dien thoai, huong mat)...", flush=True)
        nh = nhin(video)
        json.dump(nh, open(pj("nhin.json"), "w", encoding="utf-8"))
    doc = danh_dau_doc(nh)
    print(f"   pitch trung vi {nh.get('pitch_trung_vi')}, nguong cui {nh.get('nguong_cui')}, "
          f"ti le dang doc {np.mean(doc) * 100:.0f}%", flush=True)
    a = am_thanh(video)
    if os.path.exists(pj("nghe.json")):
        ng = json.load(open(pj("nghe.json"), encoding="utf-8"))
    else:
        print("2/4 Nghe ky (VAD + Whisper tung dao)...", flush=True)
        dao = vad(a)
        words = nghe(video, a, dao, opt.get("--whisper", "large-v3-turbo"))
        ng = {"dao": dao, "words": words}
        json.dump(ng, open(pj("nghe.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(f"   {len(ng['dao'])} dao tieng noi, {len(ng['words'])} chu", flush=True)
    cau = tach_cau(ng["words"], doc, nh["buoc"], a)
    if os.path.exists(pj("cau_ai.json")):
        cache = {c["id"]: c for c in json.load(open(pj("cau_ai.json"), encoding="utf-8"))}
        for c in cau:
            o = cache.get(c["id"])
            if o and abs(o["s"] - c["s"]) < 0.05:
                c["doc"], c["dien_thoai_ai"], c["nhin_ong_kinh"] = o["doc"], o.get("dien_thoai_ai"), o.get("nhin_ong_kinh")
    else:
        print("3b Claude xem hinh tung cau...", flush=True)
        kiem_hinh_ai(video, cau)
        json.dump(cau, open(pj("cau_ai.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(cau, open(pj("cau.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"3/4 {len(cau)} cau ({sum(c['doc'] >= 0.4 for c in cau)} cau dang doc dien thoai)", flush=True)
    print("4/4 AI chon lan noi tot nhat cho tung y...", flush=True)
    kq = chon(cau, opt.get("--model", "claude-opus-5-5"), float(opt.get("--dai", 36)))
    json.dump(kq, open(pj("chon.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    out = ghep(cau, kq)
    json.dump(out, open(ra, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    tong = sum(x["e"] - x["s"] for x in out)
    print(f"Giu {len(out)} doan, tong {tong:.1f}s")
    for x in out:
        print(f"  [{x['s']:7.2f}-{x['e']:7.2f}] ({x['y']}) {x['text']}")
    print("Nhan xet AI:", kq.get("nhan_xet", ""))


if __name__ == "__main__":
    main()
