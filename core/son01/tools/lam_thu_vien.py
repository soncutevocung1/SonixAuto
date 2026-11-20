"""Lap thu vien canh minh hoa v3: tach canh + do NET/do phan giai + AI gan nhan ky (chai san pham, chu in,
mo, co nguoi, mo ta) - de chon canh dep, dung noi dung, khong lo chai san pham khac.

python lam_thu_vien.py <thu_muc_ra> <thu_muc_video_1> [<thu_muc_video_2> ...] [--model claude-sonnet-5-5] [--luong 4]
Ra: <ra>/<ten thu muc>/canh.json + anh/, <ra>/tat_ca.json (gop). Chay lai = lam tiep cho do (khong lam lai).
"""
import sys, os, json, base64, subprocess, tempfile, threading, time
from concurrent.futures import ThreadPoolExecutor
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APP = os.environ.get("SONIX_APP") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, APP)

a = [x for x in sys.argv[1:]]
opt = {}
while "--model" in a or "--luong" in a:
    for k in ("--model", "--luong"):
        if k in a:
            i = a.index(k)
            opt[k] = a[i + 1]
            del a[i:i + 2]
OUT, SRCS = a[0], a[1:]
MODEL = opt.get("--model", "claude-sonnet-5-5")
LUONG = int(opt.get("--luong", 4))
FF = os.environ.get("SONIX_FFMPEG") or __import__("imageio_ffmpeg").get_ffmpeg_exe()
EXT = (".mp4", ".mov", ".m4v", ".webm", ".mkv")
MAX_CANH = 8.0   # canh dai hon -> chia nho (cuon phim dai cua anh Son)

NHAN = {
    "mo_phong_hap_thu": "đồ họa/3D mô phỏng cây, lá hấp thu dinh dưỡng",
    "mo_phong_re": "đồ họa/3D mô phỏng rễ",
    "re_bung": "rễ trắng bung nhiều, nhổ cây thấy bộ rễ, rễ tơ",
    "ra_dot_la_xanh": "chồi non, đọt mới, lá xanh bóng khỏe",
    "van_de_cay_yeu": "cây vàng lá, héo, còi cọc, rễ thối, sâu bệnh",
    "dat_kho": "đất khô nứt nẻ, hạn, đất cứng",
    "pha_thuoc": "rót/đong/pha phân thuốc vào nước, nắp, ly, bình, xô",
    "phun_tuoi": "phun hoặc tưới cho cây",
    "san_pham_can_canh": "cận cảnh chai/can sản phẩm",
    "con_trung_chich_hut": "rầy, rệp, bọ trĩ, côn trùng",
    "nong_dan_vuon": "nông dân làm vườn, vườn cà phê/sầu riêng/tiêu toàn cảnh đẹp",
    "ra_hoa_dau_qua": "cây ra hoa, đậu quả, trái non, trái chín",
    "thu_hoach": "thu hoạch, hái trái, sau thu hoạch",
    "buoi_sang_chieu": "ánh nắng sớm, chiều mát, hoàng hôn trong vườn",
    "nang_gat": "nắng gắt buổi trưa",
    "loai_han": "KHÔNG DÙNG: màn hình đen, chuyển cảnh, chỉ có chữ, giao diện điện thoại",
}
SYSTEM = ("Bạn gắn nhãn cảnh video cho thư viện dựng video phân bón TikTok. Xem KỸ từng ô (mã vàng góc trái). "
          "chai: liệt kê sản phẩm có bao bì THẤY ĐƯỢC trong ô: 'dam_ca' (can/chai trắng nhãn xanh ĐẠM CÁ AMINO), "
          "'tc01' (chai/lọ xanh lá KÍCH RỄ TC01, kể cả nhỏ ở góc, cầm trên tay), 'khac' (bất kỳ chai/gói/bao phân thuốc khác). "
          "Không thấy bao bì nào thì []. chu_in: có chữ/logo/giá/phụ đề in sẵn trên video. mo: ảnh mờ nhòe, vỡ hạt, thiếu nét. "
          "nguoi: có người trong khung. nguoi_noi: có người nhìn thẳng camera nói (dẫn chương trình). "
          "mo_ta: 6-14 chữ tiếng Việt tả cảnh (cây gì, làm gì, cận/toàn, sáng/chiều).")
SCHEMA = {"type": "object", "properties": {"canh": {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "string"},
    "nhan": {"type": "array", "items": {"type": "string", "enum": list(NHAN)}},
    "chai": {"type": "array", "items": {"type": "string", "enum": ["dam_ca", "tc01", "khac"]}},
    "chu_in": {"type": "boolean"}, "mo": {"type": "boolean"}, "nguoi": {"type": "boolean"},
    "nguoi_noi": {"type": "boolean"}, "mo_ta": {"type": "string"}},
    "required": ["id", "nhan", "chai", "chu_in", "mo", "nguoi", "nguoi_noi", "mo_ta"], "additionalProperties": False}}},
    "required": ["canh"], "additionalProperties": False}


def tach(src, lib):
    """Tach canh (PySceneDetect) + anh 270x480 + do net (phuong sai Laplacian tren khung rong 540)."""
    import cv2
    from scenedetect import open_video, SceneManager
    from scenedetect.detectors import ContentDetector
    pj = os.path.join(lib, "canh.json")
    canh = json.load(open(pj, encoding="utf-8")) if os.path.exists(pj) else []
    xong = {c["file"] for c in canh}
    os.makedirs(os.path.join(lib, "anh"), exist_ok=True)
    files = sorted(os.path.join(r, f) for r, _, fs in os.walk(src) for f in fs if f.lower().endswith(EXT))
    vi0 = len({c["file"] for c in canh})
    for vi, f in enumerate([f for f in files if f not in xong], vi0 + 1):
        try:
            v = open_video(f)
            sm = SceneManager()
            sm.add_detector(ContentDetector(threshold=27, min_scene_len=int(0.8 * v.frame_rate)))
            sm.auto_downscale = True
            sm.detect_scenes(v, show_progress=False)
            sec = lambda t: t.get_seconds() if hasattr(t, "get_seconds") else t.seconds
            dur = sec(v.duration)
            ranges = [(sec(x), sec(y)) for x, y in sm.get_scene_list()] or [(0.0, dur)]
            w, h = v.frame_size
        except Exception as e:
            print("  loi", os.path.basename(f), e, flush=True)
            continue
        cap = cv2.VideoCapture(f)
        si = 0
        for s, e in ranges:
            # canh dai -> chia khuc <= MAX_CANH
            n = max(1, int((e - s) // MAX_CANH) + (1 if (e - s) % MAX_CANH > 2 else 0))
            for q in range(n):
                s1, e1 = s + (e - s) * q / n, s + (e - s) * (q + 1) / n
                if e1 - s1 < 0.8:
                    continue
                si += 1
                cid = f"{vi}.{si}"
                nets = []
                for p in (0.3, 0.7):
                    cap.set(cv2.CAP_PROP_POS_MSEC, (s1 + (e1 - s1) * p) * 1000)
                    ok, img = cap.read()
                    if not ok:
                        continue
                    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    g = cv2.resize(g, (540, int(540 * g.shape[0] / g.shape[1])))
                    nets.append(float(cv2.Laplacian(g, cv2.CV_64F).var()))
                    if p == 0.3:
                        th = cv2.resize(img, (270, int(270 * img.shape[0] / img.shape[1])))
                        canvas = cv2.copyMakeBorder(th, 0, max(0, 480 - th.shape[0]), 0, 0, cv2.BORDER_CONSTANT) if th.shape[0] < 480 else th[:480]
                        cv2.putText(canvas, cid, (4, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 5)
                        cv2.putText(canvas, cid, (4, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                        cv2.imencode(".jpg", canvas)[1].tofile(os.path.join(lib, "anh", cid + ".jpg"))
                if not nets:
                    continue
                canh.append({"id": cid, "file": f, "s": round(s1, 2), "e": round(e1, 2), "dai": round(e1 - s1, 2),
                             "w": w, "h": h, "net": round(min(nets), 1)})
        cap.release()
        print(f"  {vi}/{len(files)} {os.path.basename(f)}: {si} canh", flush=True)
        if vi % 10 == 0:
            json.dump(canh, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    json.dump(canh, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    return canh


def gan_nhan(lib, canh):
    from core import config
    from core.analyze import _claude
    settings = config.load_settings()
    pj = os.path.join(lib, "canh.json")
    by = {c["id"]: c for c in canh}
    todo = [c for c in canh if "mo_ta" not in c and os.path.exists(os.path.join(lib, "anh", c["id"] + ".jpg"))]
    B = 12
    khoa = threading.Lock()
    dem = [0]

    def lo(b):
        ds = todo[b:b + B]
        tmp = tempfile.mkdtemp()
        for n, c in enumerate(ds):
            with open(os.path.join(lib, "anh", c["id"] + ".jpg"), "rb") as f1, open(os.path.join(tmp, f"{n:04d}.jpg"), "wb") as f2:
                f2.write(f1.read())
        sheet = os.path.join(tmp, "sheet.jpg")
        subprocess.run([FF, "-v", "error", "-y", "-framerate", "1", "-i", os.path.join(tmp, "%04d.jpg"),
                        "-vf", "scale=270:480:force_original_aspect_ratio=decrease,pad=270:480:(ow-iw)/2:(oh-ih)/2,tile=6x2:padding=4:color=0x111111",
                        "-frames:v", "1", "-q:v", "3", sheet], check=True)
        img = base64.b64encode(open(sheet, "rb").read()).decode()
        nh = "\n".join(f"- {k}: {v}" for k, v in NHAN.items())
        content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img}},
                   {"type": "text", "text": f"Bảng {len(ds)} cảnh, mã: {', '.join(c['id'] for c in ds)}.\nNhãn nội dung:\n{nh}"}]
        for thu in range(3):
            try:
                kq = _claude(content, SCHEMA, settings, MODEL, system=SYSTEM)
                break
            except Exception as e:
                print("  thu lai", e, flush=True)
                time.sleep(5 * (thu + 1))
        else:
            return
        with khoa:
            for x in kq["canh"]:
                c = by.get(x["id"])
                if c:
                    c.update({k: x[k] for k in ("nhan", "chai", "chu_in", "mo", "nguoi", "nguoi_noi", "mo_ta")})
            dem[0] += len(ds)
            json.dump(canh, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
            print(f"  nhan {dem[0]}/{len(todo)}", flush=True)

    with ThreadPoolExecutor(LUONG) as ex:
        list(ex.map(lo, range(0, len(todo), B)))


tat_ca = []
for src in SRCS:
    ten = os.path.basename(src.rstrip("\\/")).replace(" ", "_")
    lib = os.path.join(OUT, ten)
    os.makedirs(lib, exist_ok=True)
    print("==", src, flush=True)
    canh = tach(src, lib)
    print(f"  {len(canh)} canh, gan nhan...", flush=True)
    gan_nhan(lib, canh)
    for c in canh:
        c = dict(c)
        c["id"] = f"{ten}:{c['id']}"
        tat_ca.append(c)
    json.dump(tat_ca, open(os.path.join(OUT, "tat_ca.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
from collections import Counter
print("XONG", len(tat_ca), "canh |", dict(Counter(n for c in tat_ca for n in c.get("nhan", [])).most_common()))
print("lo chai:", dict(Counter(x for c in tat_ca for x in c.get("chai", []))), "| mo:", sum(bool(c.get("mo")) for c in tat_ca))
