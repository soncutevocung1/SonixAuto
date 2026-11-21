"""Ghep ke hoach Claude viet tay (trong cuoc tro chuyen, KHONG goi API) + moc chu cua cau.json -> kehoach.json.
python ghep_ke_hoach.py <thu_muc_viec>   (doc cau.json + ke_hoach_tay.json)
ke_hoach_tay.json: xem mau/C3432_kich_re_thu4.json. Moi doan: cau, tu, den (chi so chu trong cau goc),
vai, zoom, minh_hoa (null = giu hinh goc), goi_y (cum mo ta canh can tim), sua {chi so: chu dung}, gop [[a,b,chu]],
phu_de [[tu, den, xuong_dong, nhan, noi]] tinh tren chi so chu SAU khi gop (noi=true: xep duoi cau truoc)."""
import sys, json, os
sys.stdout.reconfigure(encoding="utf-8")
lv = sys.argv[1]
cau = {c["id"]: c for c in json.load(open(os.path.join(lv, "cau.json"), encoding="utf-8"))}
kt = json.load(open(os.path.join(lv, "ke_hoach_tay.json"), encoding="utf-8"))
out = []
for d in kt["doan"]:
    c = cau[d["cau"]]
    n = len(c["words"])
    ws = [dict(w, w=d.get("sua", {}).get(str(i), w["w"].strip())) for i, w in enumerate(c["words"])]
    for a, b, moi in sorted(d.get("gop", []), reverse=True):
        ws[a:b + 1] = [{"w": moi, "s": ws[a]["s"], "e": ws[b]["e"], "p": 1.0}]
    tu = d["tu"] - sum(b - a for a, b, _ in d.get("gop", []) if b < d["tu"])
    den = d["den"] - sum(b - a for a, b, _ in d.get("gop", []) if b <= d["den"])
    seg = ws[tu:den + 1]
    s = c["s"] if d["tu"] == 0 else round(max(c["s"], seg[0]["s"] - 0.08), 3)
    e = c["e"] if d["den"] == n - 1 else round(min(c["e"], seg[-1]["e"] + 0.15), 3)
    pd = [{"tu": p[0], "den": p[1], "xuong_dong": p[2], "nhan": bool(p[3]), "noi": bool(p[4]) if len(p) > 4 else False}
          for p in d["phu_de"]]
    assert pd[0]["tu"] == 0 and pd[-1]["den"] == len(seg) - 1, (d["cau"], len(seg), pd[-1])
    out.append({"id": len(out), "s": s, "e": e, "words": seg, "text": " ".join(w["w"] for w in seg),
                "vai": d["vai"], "zoom": d["zoom"], "minh_hoa": d["minh_hoa"], "dem_y": d.get("dem_y"), "so": d.get("so"),
                "tu_khoa": [], "phu_de": pd, "goi_y": d.get("goi_y", []), "tu_chu": 0, "den_chu": len(seg) - 1, "loi_sua": ""})
kh = {"chu_mo_dau": kt["chu_mo_dau"], "doan": out, "ly_do": "Claude viết tay trong cuộc trò chuyện (không gọi API)",
      "tong_giay": round(sum(x["e"] - x["s"] for x in out), 2)}
json.dump(kh, open(os.path.join(lv, "kehoach.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for x in out:
    w = [v["w"] for v in x["words"]]
    print(f"[{x['s']:6.1f}-{x['e']:6.1f}] {x['vai']:9s} | " + " | ".join(
        ("*" if c["nhan"] else "") + ("↳" if c["noi"] else "") + " ".join(w[c["tu"]:c["den"] + 1]) for c in x["phu_de"]))
print("tong", kh["tong_giay"], "s")
