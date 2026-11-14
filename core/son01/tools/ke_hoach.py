"""Buoc 3 - AI len ke hoach dung (chon noi dung + gan nhan) cho phong cach Son 01.

python ke_hoach.py cat.json ke_hoach.json [--san-pham "Dam ca Amino"] [--dai 36] [--model claude-opus-5-5]
Dung lai ham _claude cua Sonix Auto (key trong cai dat app, co model du phong).
"""
import sys, os, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APP = os.environ.get("SONIX_APP") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, APP)
from core import config  # noqa: E402
from core.analyze import _claude  # noqa: E402

a = sys.argv[1:]
opt = dict(zip(a[2::2], a[3::2]))
doan = json.load(open(a[0], encoding="utf-8"))
san_pham = opt.get("--san-pham", "")
dai = float(opt.get("--dai", 36))
model = opt.get("--model", "claude-opus-5-5")

NHAN_MINH_HOA = ["mo_phong_hap_thu", "mo_phong_re", "re_bung", "ra_dot_la_xanh", "van_de_cay_yeu",
                 "dat_kho", "pha_thuoc", "phun_tuoi", "san_pham_can_canh", "con_trung_chich_hut",
                 "truoc_sau", "nong_dan_vuon"]

SYSTEM = f"""Bạn là biên tập viên video TikTok ngành phân bón, dựng theo phong cách "Sơn 01":
người mẫu (anh Sơn) nói trước camera bằng giọng miền Nam, xưng "em", gọi khách là "bác/bà con".
Khán giả: nông dân 25-45 tuổi ở Tây Nguyên (cà phê, sầu riêng, tiêu, rau màu).

Nhiệm vụ: từ các đoạn lời đã cắt sạch (mỗi đoạn có id, thời gian, lời), CHỌN và SẮP XẾP các đoạn
để ra video dài khoảng {dai:.0f} giây (chấp nhận 30-40 giây), theo mạch:
  1) MỞ ĐẦU nêu vấn đề gây tò mò (2-5 giây đầu phải giữ chân người xem)
  2) VẤN ĐỀ / nguyên nhân
  3) GIẢI PHÁP + sản phẩm (nếu có các ý 1-2-3 thì đánh dấu dem_y)
  4) CÁCH DÙNG (liều lượng, thời điểm)
  5) KÊU GỌI bình luận / mua hàng
Luật:
- Chỉ dùng id có sẵn, có thể cắt bớt đầu/cuối đoạn bằng tu_chu/den_chu (chỉ số chữ, tính từ 0, gồm cả 2 đầu).
- Không lặp ý. Bỏ câu nói lại, câu vấp, câu lạc đề.
- tu_khoa: 0-2 cụm ngắn (1-4 chữ) PHẢI xuất hiện nguyên văn trong lời, là chỗ muốn người xem chú ý
  (vấn đề của cây, thời điểm, liều lượng, lợi ích, tên sản phẩm).
- zoom: "manh" khi nhấn mạnh/giới thiệu sản phẩm, "nhe" khi cần đổi nhịp, "khong" còn lại.
  Không để quá 3 giây liền không có zoom hoặc minh họa.
- minh_hoa: chọn 1 nhãn trong {NHAN_MINH_HOA} hoặc null, khi lời nói tả điều người xem cần THẤY.
- Không chọn đoạn ngắn dưới 1 giây (trừ khi nối liền câu với đoạn kế). dem_y chỉ gắn cho ĐOẠN ĐẦU của mỗi ý.
- tu_khoa phải là cụm có nghĩa (vấn đề, thời điểm, liều lượng, lợi ích), KHÔNG lấy từ nối như "sau khi",
  "trước và trong", KHÔNG kèm dấu câu.
- minh_hoa = null cho đoạn mo_dau và keu_goi (giữ mặt người mẫu để tạo tin tưởng).
- chu_mo_dau: 2 dòng chữ lớn in hoa cho 2-3 giây đầu (dòng 2 là phần gây sốc), lấy ý từ lời mở đầu.
- loi_sua: lời của đúng khoảng chữ đã chọn, SỬA LỖI NGHE NHẦM của máy (chính tả, từ chuyên ngành
  như "dễ hấp thu", "hao phân", "đong", "phun", "tránh", "tham khảo", "thu hoạch"), giữ nguyên giọng
  nói và thứ tự, KHÔNG thêm bớt ý; cố giữ số chữ gần bằng bản gốc để khớp thời gian.
Sản phẩm: {san_pham or "theo lời nói"}."""

SCHEMA = {
    "type": "object",
    "properties": {
        "chu_mo_dau": {"type": "array", "items": {"type": "string"}},
        "doan": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "tu_chu": {"type": "integer"},
                "den_chu": {"type": "integer"},
                "vai": {"type": "string", "enum": ["mo_dau", "van_de", "giai_phap", "cach_dung", "keu_goi"]},
                "tu_khoa": {"type": "array", "items": {"type": "string"}},
                "zoom": {"type": "string", "enum": ["khong", "nhe", "manh"]},
                "minh_hoa": {"type": ["string", "null"]},
                "dem_y": {"type": ["integer", "null"]},
                "loi_sua": {"type": "string"},
            },
            "required": ["id", "tu_chu", "den_chu", "vai", "tu_khoa", "zoom", "minh_hoa", "dem_y", "loi_sua"],
            "additionalProperties": False,
        }},
        "ly_do": {"type": "string"},
    },
    "required": ["chu_mo_dau", "doan", "ly_do"],
    "additionalProperties": False,
}

lines = []
for i, d in enumerate(doan):
    ws = " ".join(f"{k}:{w['w']}" for k, w in enumerate(d["words"]))
    lines.append(f"id={i} [{d['s']:.2f}-{d['e']:.2f}s, {d['e'] - d['s']:.1f}s] {d['text']}\n   chu: {ws}")
content = [{"type": "text", "text": "CÁC ĐOẠN LỜI:\n" + "\n".join(lines)}]
if opt.get("--gop-y") and os.path.exists(opt["--gop-y"]):
    content.append({"type": "text", "text": "GÓP Ý TỪ LẦN DỰNG TRƯỚC (bắt buộc khắc phục):\n"
                    + open(opt["--gop-y"], encoding="utf-8").read()})

settings = config.load_settings()
kq = _claude(content, SCHEMA, settings, model, system=SYSTEM)

# Doi ra moc thoi gian that tren video goc + kiem tra tu khoa
tong = 0.0
for x in kq["doan"]:
    d = doan[x["id"]]
    ws = d["words"]
    a_, b_ = max(0, x["tu_chu"]), min(len(ws) - 1, x["den_chu"])
    x["s"] = round(max(d["s"], ws[a_]["s"] - 0.06), 3)
    x["e"] = round(min(d["e"], ws[b_]["e"] + 0.12), 3)
    goc = [dict(w) for w in ws[a_:b_ + 1]]
    moi = (x.get("loi_sua") or "").split()
    if moi and len(moi) == len(goc):
        for w, m in zip(goc, moi):
            w["w"] = m
    elif moi:
        # so chu khac nhau: chia lai thoi gian theo do dai ky tu
        s0, e0 = goc[0]["s"], goc[-1]["e"]
        L = sum(len(m) + 1 for m in moi)
        t, ws2 = s0, []
        for m in moi:
            dt = (e0 - s0) * (len(m) + 1) / L
            ws2.append({"w": m, "s": round(t, 3), "e": round(t + dt * 0.92, 3), "p": 1.0})
            t += dt
        goc = ws2
    x["words"] = goc
    x["text"] = " ".join(w["w"] for w in x["words"])
    x["tu_khoa"] = [k for k in x["tu_khoa"] if k.lower() in x["text"].lower()]
    tong += x["e"] - x["s"]
kq["tong_giay"] = round(tong, 2)
json.dump(kq, open(a[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("Chu mo dau:", " / ".join(kq["chu_mo_dau"]))
for x in kq["doan"]:
    print(f"[{x['s']:7.2f}-{x['e']:7.2f}] {x['vai']:9s} zoom={x['zoom']:5s} mh={x['minh_hoa']} kw={x['tu_khoa']} | {x['text']}")
print(f"Tong {tong:.1f}s | {kq['ly_do']}")
