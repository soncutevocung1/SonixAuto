"""AI tu gan nhan cho thu vien canh (xem bang anh 30 canh/lan).

python gan_nhan.py <thu_muc_thu_vien> [--model claude-sonnet-5-5]
Doc canh.json + thumbs/, ghi lai canh.json voi truong "nhan".
"""
import sys, os, json, base64, subprocess, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APP = os.environ.get("SONIX_APP") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, APP)
from core import config  # noqa: E402
from core.analyze import _claude  # noqa: E402

lib = sys.argv[1]
opt = dict(zip(sys.argv[2::2], sys.argv[3::2]))
model = opt.get("--model", "claude-sonnet-5-5")
FF = os.environ.get("SONIX_FFMPEG") or __import__("imageio_ffmpeg").get_ffmpeg_exe()
pj = os.path.join(lib, "canh.json")
canh = json.load(open(pj, encoding="utf-8"))

NHAN = {
    "mo_phong_hap_thu": "đồ họa mô phỏng cây/lá hấp thu dinh dưỡng (hạt sáng, trong suốt, nền tối)",
    "mo_phong_re": "đồ họa mô phỏng rễ phát sáng / dòng chảy trong rễ",
    "re_bung": "rễ trắng bung nhiều, nhổ cây lên thấy bộ rễ",
    "ra_dot_la_xanh": "chồi non, đọt mới, lá xanh bóng khỏe",
    "van_de_cay_yeu": "cây vàng lá, héo, còi cọc, rễ thối",
    "dat_kho": "đất khô nứt nẻ, hạn",
    "pha_thuoc": "rót/đong/pha sản phẩm vào nước, ly, xô",
    "phun_tuoi": "phun hoặc tưới cho cây",
    "san_pham_can_canh": "cận cảnh chai/can sản phẩm",
    "con_trung_chich_hut": "rầy, rệp, bọ trĩ, côn trùng trên lá",
    "nong_dan_vuon": "nông dân, vườn cà phê/sầu riêng toàn cảnh",
    "sp_tc01": "sản phẩm là Kích rễ TC01 (chai xanh lá)",
    "sp_dam_ca": "sản phẩm là Đạm cá Amino (can trắng)",
    "sp_khac": "sản phẩm của hãng/loại khác",
    "loai": "KHÔNG DÙNG ĐƯỢC: có người nói/dẫn chương trình nhìn camera, có chữ/logo/khung giá in sẵn, mờ nhòe, màn hình đen",
}
SYSTEM = "Bạn gắn nhãn cảnh video cho thư viện dựng video phân bón. Chỉ dùng nhãn trong danh sách. Một cảnh có thể có nhiều nhãn."
SCHEMA = {"type": "object", "properties": {"canh": {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "string"}, "nhan": {"type": "array", "items": {"type": "string", "enum": list(NHAN)}}},
    "required": ["id", "nhan"], "additionalProperties": False}}}, "required": ["canh"], "additionalProperties": False}

FONT = "C\\:/Windows/Fonts/arialbd.ttf" if os.name == "nt" else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
settings = config.load_settings()
by_id = {c["id"]: c for c in canh}
for c in canh:  # file hong / khong trich duoc anh -> bo
    if not os.path.exists(os.path.join(lib, "thumbs", c["id"] + ".jpg")):
        c["nhan"] = ["loai"]
        c["loi"] = "file_hong"
todo = [c for c in canh if not c.get("nhan")]
B = 30
for b in range(0, len(todo), B):
    lo = todo[b:b + B]
    tmp = tempfile.mkdtemp()
    for n, c in enumerate(lo):
        src = os.path.join(lib, "thumbs", c["id"] + ".jpg")
        dst = os.path.join(tmp, f"{n:04d}.jpg")
        with open(src, "rb") as f1, open(dst, "wb") as f2:
            f2.write(f1.read())
    sheet = os.path.join(tmp, "sheet.jpg")
    subprocess.run([FF, "-v", "error", "-y", "-framerate", "1", "-i", os.path.join(tmp, "%04d.jpg"),
                    "-vf", "tile=10x3:padding=3:color=0x111111", "-frames:v", "1", "-q:v", "3", sheet], check=True)
    img = base64.b64encode(open(sheet, "rb").read()).decode()
    ds = "\n".join(f"- {k}: {v}" for k, v in NHAN.items())
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img}},
        {"type": "text", "text": f"Bảng có {len(lo)} cảnh, mã vàng ở góc trái mỗi ô: {', '.join(c['id'] for c in lo)}.\n"
                                 f"Gắn nhãn cho TỪNG mã. Danh sách nhãn:\n{ds}"},
    ]
    kq = _claude(content, SCHEMA, settings, model, system=SYSTEM)
    for x in kq["canh"]:
        if x["id"] in by_id:
            by_id[x["id"]]["nhan"] = x["nhan"] or ["khong_ro"]
    json.dump(canh, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{min(b + B, len(todo))}/{len(todo)} canh da gan nhan", flush=True)

from collections import Counter
cnt = Counter(n for c in canh for n in c.get("nhan", []))
print("Thong ke:", dict(cnt.most_common()))
