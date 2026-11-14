"""Chon khung de cham diem ban xem truoc + xep bang (va tuy chon: nho Claude cham theo 10 tieu chi).

python cham_diem.py tl.json video.mp4 <thu_muc_ra> [--ai claude-sonnet-5-5]
Ra: bang_1.jpg.. (moi bang 12 khung co ghi giay + ly do), diem.json neu --ai.
"""
import sys, os, json, subprocess, base64
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FF = os.environ.get("SONIX_FFMPEG") or __import__("imageio_ffmpeg").get_ffmpeg_exe()
FONT = "C\\:/Windows/Fonts/arialbd.ttf" if os.name == "nt" else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

tl = json.load(open(sys.argv[1], encoding="utf-8"))
video, out = sys.argv[2], sys.argv[3]
opt = dict(zip(sys.argv[4::2], sys.argv[5::2]))
os.makedirs(out, exist_ok=True)

moc = []  # (giay, ly do)
for s in tl["main"][1:]:
    moc += [(s["t0"] - 0.04, "truoc cat"), (s["t0"] + 0.04, "sau cat")]
for b in tl["broll"]:
    moc += [(b["t0"] + 0.15, "minh hoa vao"), (b["t0"] + 0.8, "minh hoa yen")]
for c in tl["chu"]:
    moc.append((c["t0"] + 0.25, "chu: " + c["text"][:18].replace("\n", " ")))
moc = sorted({round(t, 2): l for t, l in moc if 0 <= t < tl["dai"]}.items())
# bo moc qua sat nhau (< 0.3s) tru diem cat
loc, last = [], -9
for t, l in moc:
    if t - last >= 0.3 or "cat" in l:
        loc.append((t, l))
        last = t

anh = []
for i, (t, l) in enumerate(loc):
    p = os.path.join(out, f"k_{i:03d}.jpg")
    nhan = f"{t:.2f}s {l}".replace(":", "\\:").replace("'", "")
    subprocess.run([FF, "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf",
                    f"scale=270:480,drawtext=fontfile='{FONT}':text='{nhan}':x=4:y=4:fontsize=15:fontcolor=yellow:box=1:boxcolor=black@0.75",
                    p])
    anh.append(p)
bang = []
for b in range(0, len(anh), 12):
    lst = anh[b:b + 12]
    ins = sum([["-i", p] for p in lst], [])
    while len(lst) < 12:
        ins += ["-f", "lavfi", "-i", "color=0x111111:s=270x480:d=1"]
        lst.append(None)
    q = os.path.join(out, f"bang_{b // 12 + 1}.jpg")
    subprocess.run([FF, "-v", "error", "-y", *ins, "-filter_complex", "xstack=inputs=12:layout="
                    + "|".join(f"{(j % 6) * 270}_{(j // 6) * 480}" for j in range(12)), "-frames:v", "1", q])
    bang.append(q)
print(f"{len(loc)} khung -> {len(bang)} bang trong {out}")

if "--ai" in opt:
    APP = os.environ.get("SONIX_APP") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
    sys.path.insert(0, APP)
    from core import config
    from core.analyze import _claude
    TIEU_CHI = ["chu_khong_che_mat_san_pham", "trong_vung_an_toan", "chuyen_dong_muot", "chu_khop_giong",
                "tieng_hieu_ung_dung_luc", "chinh_ta", "mau_dong_deu", "minh_hoa_dung_noi_dung",
                "khong_san_pham_khac_hang", "nhip_khong_chet"]
    schema = {"type": "object", "properties": {
        "diem": {"type": "object", "properties": {k: {"type": "number"} for k in TIEU_CHI}, "required": TIEU_CHI,
                 "additionalProperties": False},
        "loi": {"type": "array", "items": {"type": "object", "properties": {
            "giay": {"type": "number"}, "tieu_chi": {"type": "string", "enum": TIEU_CHI}, "mo_ta": {"type": "string"},
            "cach_sua": {"type": "string"}}, "required": ["giay", "tieu_chi", "mo_ta", "cach_sua"], "additionalProperties": False}}},
        "required": ["diem", "loi"], "additionalProperties": False}
    content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                            "data": base64.b64encode(open(q, "rb").read()).decode()}} for q in bang]
    loi_noi = "\n".join(f"{c['t0']:.2f}s: {c['text']}" for c in tl["chu"])
    content.append({"type": "text", "text": "Đây là các khung trích từ video TikTok phong cách 'Sơn 01' (người mẫu nói trước camera, "
                    "phụ đề trắng, từ khóa vàng, khung minh họa viền sáng). Chấm mỗi tiêu chí 0-1 điểm (tổng 10), "
                    "liệt kê lỗi cụ thể theo giây và cách sửa. Bạn KHÔNG nghe được âm thanh: tiêu chí "
                    "tieng_hieu_ung_dung_luc cho 1 điểm (sẽ đo bằng máy). Phong cách của chủ kênh: tiêu đề đầu "
                    "video dùng màu đỏ-trắng là CỐ Ý; phụ đề đặt trên đầu người mẫu là CỐ Ý. Lời phụ đề:\n" + loi_noi})
    kq = _claude(content, schema, config.load_settings(), opt["--ai"],
                 system="Bạn là người duyệt chất lượng video khắt khe. Chỉ chấm dựa trên điều thấy được.")
    # Tieu chi am thanh: AI chi xem anh tinh -> cham bang do dac (tieng hieu ung lech moc chu/canh/cat <= 1 khung)
    moc = [c["t0"] for c in tl["chu"]] + [b["t0"] for b in tl["broll"]] + [s["t0"] for s in tl["main"]]
    sfx = [a["t0"] for a in tl["am"] if a.get("loai") != "music"]
    lech = [min(abs(s - m) for m in moc) for s in sfx] if sfx and moc else []
    dung = sum(1 for x in lech if x <= 1 / 30 + 1e-3)
    kq["diem"]["tieng_hieu_ung_dung_luc"] = round(dung / len(lech), 2) if lech else 0.5
    kq["loi"] = [l for l in kq["loi"] if l["tieu_chi"] != "tieng_hieu_ung_dung_luc"]
    kq["do_tieng"] = {"so_tieng": len(sfx), "dung_luc": dung}
    kq["tong"] = round(sum(kq["diem"].values()), 1)
    json.dump(kq, open(os.path.join(out, "diem.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("TONG DIEM:", kq["tong"], "/10")
    for l in kq["loi"]:
        print(f"- {l['giay']:.1f}s [{l['tieu_chi']}] {l['mo_ta']} -> {l['cach_sua']}")
