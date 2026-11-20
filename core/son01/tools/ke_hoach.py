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
giu_het = opt.get("--giu-het", "0") == "1"  # cat_tho2 da chon lan noi: giu du, dung thu tu, khong cat bot

NHAN_MINH_HOA = ["mo_phong_hap_thu", "mo_phong_re", "re_bung", "ra_dot_la_xanh", "van_de_cay_yeu",
                 "dat_kho", "pha_thuoc", "phun_tuoi", "san_pham_can_canh", "con_trung_chich_hut",
                 "truoc_sau", "nong_dan_vuon", "ra_hoa_dau_qua", "thu_hoach", "buoi_sang_chieu", "nang_gat"]

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
Sản phẩm: {san_pham or "theo lời nói"}.
PHỤ ĐỀ (học từ bản anh Sơn tự làm) - trường phu_de của mỗi đoạn, chỉ số chữ tính trên dòng 'chu' của đoạn đó:
- Chia lời thành CỤM THEO NGHĨA 2-7 chữ, đủ ý để người xem hiểu ngay (vd "đạm cá là | một dòng đạm | dễ hấp thu",
  "bón đạm cá trong 3 giai đoạn"). KHÔNG tách số khỏi danh từ ("3 giai đoạn", "4 - 5 nắp", "16 lít"),
  không tách cụm danh từ/tên sản phẩm, không để cụm kết thúc bằng từ nối (là, và, của, trong, vào, thì, mà).
- Các cụm phủ liên tục mọi chữ của đoạn từ tu_chu đến den_chu, không chồng nhau, theo thứ tự.
- xuong_dong: chỉ số chữ bắt đầu dòng 2 khi cụm dài hơn khoảng 18 ký tự (ngắt ở chỗ ngắt nghĩa, vd
  "tránh đi vào / buổi trưa nắng nóng"); -1 nếu 1 dòng. Mỗi dòng tối đa ~20 ký tự.
- nhan=true cho cụm là ĐIỂM NHẤN (vấn đề, lợi ích, thời điểm, liều lượng): sẽ hiện chữ vàng nghiêng nổi riêng.
  Khoảng 1/3 số cụm, không 2 cụm nhấn liền nhau.
- so: khi đoạn là 1 mục trong danh sách con (vd 3 giai đoạn: cây con=1, nuôi hoa dưỡng quả=2, sau thu hoạch=3)
  thì ghi số thứ tự mục để hiện số to bên phải; còn lại null."""
if giu_het:
    SYSTEM += """
CHẾ ĐỘ GIỮ HẾT: các đoạn đã được biên tập viên chọn sẵn (mỗi ý 1 lần nói tốt nhất, đúng mạch).
BẮT BUỘC trả về MỌI id theo đúng thứ tự, tu_chu=0, den_chu=chữ cuối; chỉ gắn vai, tu_khoa, zoom, minh_hoa,
dem_y và sửa chính tả trong loi_sua."""

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
                "so": {"type": ["integer", "null"]},
                "phu_de": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "tu": {"type": "integer"},
                        "den": {"type": "integer"},
                        "xuong_dong": {"type": "integer"},
                        "nhan": {"type": "boolean"},
                    },
                    "required": ["tu", "den", "xuong_dong", "nhan"],
                    "additionalProperties": False,
                }},
            },
            "required": ["id", "tu_chu", "den_chu", "vai", "tu_khoa", "zoom", "minh_hoa", "dem_y", "loi_sua", "so", "phu_de"],
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
if giu_het:
    # ep giu du: moi id 1 lan, dung thu tu, tron cau (AI chi gan nhan)
    theo_id = {}
    for x in kq["doan"]:
        if 0 <= x["id"] < len(doan) and x["id"] not in theo_id:
            theo_id[x["id"]] = x
    ds = []
    for i, d in enumerate(doan):
        x = theo_id.get(i) or {"id": i, "vai": "giai_phap", "tu_khoa": [], "zoom": "khong", "minh_hoa": None,
                               "dem_y": None, "loi_sua": d["text"]}
        x["tu_chu"], x["den_chu"] = 0, len(d["words"]) - 1
        ds.append(x)
    kq["doan"] = ds

# Doi ra moc thoi gian that tren video goc + kiem tra tu khoa
tong = 0.0
for x in kq["doan"]:
    d = doan[x["id"]]
    ws = d["words"]
    a_, b_ = max(0, x["tu_chu"]), min(len(ws) - 1, x["den_chu"])
    if giu_het:
        x["s"], x["e"] = d["s"], d["e"]  # moc da tinh chinh theo nang luong am
    else:
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
    # phu_de: doi chi so chu ve he cua x["words"] (bat dau tu a_), phu kin, khong chong
    n = len(x["words"])
    r = n / (b_ - a_ + 1)  # loi_sua khac so chu -> co gian chi so theo ti le
    ch = lambda i: int(round((i - a_) * r))
    cum, pos = [], 0
    for c in sorted(x.get("phu_de") or [], key=lambda c: c["tu"]):
        t0, t1 = max(ch(c["tu"]), pos), min(ch(c["den"] + 1) - 1, n - 1)
        if t1 < t0:
            continue
        if t0 > pos:  # lo trong -> gop vao cum truoc / tao cum moi
            cum.append({"tu": pos, "den": t0 - 1, "xuong_dong": -1, "nhan": False})
        xd = ch(c["xuong_dong"]) if c["xuong_dong"] >= 0 else -1
        cum.append({"tu": t0, "den": t1, "xuong_dong": xd if t0 < xd <= t1 else -1, "nhan": bool(c["nhan"])})
        pos = t1 + 1
    if pos < n:
        if cum and n - pos <= 1:
            cum[-1]["den"] = n - 1
        else:
            cum.append({"tu": pos, "den": n - 1, "xuong_dong": -1, "nhan": False})
    x["phu_de"] = cum
    tong += x["e"] - x["s"]
kq["tong_giay"] = round(tong, 2)
json.dump(kq, open(a[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("Chu mo dau:", " / ".join(kq["chu_mo_dau"]))
for x in kq["doan"]:
    print(f"[{x['s']:7.2f}-{x['e']:7.2f}] {x['vai']:9s} zoom={x['zoom']:5s} mh={x['minh_hoa']} so={x.get('so')} | {x['text']}")
    ws_ = [w["w"].strip() for w in x["words"]]
    print("     pd:", " | ".join(("*" if c["nhan"] else "") + " ".join(ws_[c["tu"]:c["xuong_dong"]] if c["xuong_dong"] > 0 else ws_[c["tu"]:c["den"] + 1])
                              + (" / " + " ".join(ws_[c["xuong_dong"]:c["den"] + 1]) if c["xuong_dong"] > 0 else "") for c in x["phu_de"]))
print(f"Tong {tong:.1f}s | {kq['ly_do']}")
