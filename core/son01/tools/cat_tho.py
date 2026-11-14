"""Buoc 2 - Tu cat tho tu loi Whisper (moc thoi gian tung chu).

Bo: khoang lang, tieng dem (o, a, um...), cau noi vap / noi lai (giu lan noi cuoi).
Vao: JSON cua nghe_chu.py. Ra: JSON danh sach doan giu {s, e, text, words}.

python cat_tho.py loi.json cat.json [--gap 0.35] [--pad-in 0.06] [--pad-out 0.12]
"""
import json, re, sys, unicodedata
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from difflib import SequenceMatcher

DEM = {"ờ", "à", "ừ", "ừm", "ơ", "ờm", "hử", "ừa", "à à", "ờ ờ", "uhm", "um", "ạ"}


def norm(s):
    s = unicodedata.normalize("NFC", s.lower())
    return re.sub(r"[^\w\s]", "", s).strip()


def tach_cau(words, gap):
    """Chia chuoi chu thanh cau tai cho ngung >= gap giay hoac het cau (. ? !)."""
    out, cur = [], []
    for i, w in enumerate(words):
        if cur and (w["s"] - cur[-1]["e"] >= gap):
            out.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.?!]$", w["w"]) and i + 1 < len(words) and words[i + 1]["s"] - w["e"] > 0.2:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def text_of(ws):
    return " ".join(w["w"] for w in ws)


def la_noi_lai(a, b):
    """a la lan noi hong cua b neu: b bat dau giong a (tien to), hoac 2 cau rat giong nhau."""
    na, nb = norm(text_of(a)).split(), norm(text_of(b)).split()
    if not na or not nb:
        return False
    k = min(len(na), 4)
    if len(na) <= len(nb) and na[:k] == nb[:k]:
        return True
    return SequenceMatcher(None, na, nb).ratio() >= 0.72


def cat(loi, gap=0.35, pad_in=0.06, pad_out=0.12, nhin_truoc=3):
    words = [w for s in loi["segments"] for w in s["words"] if w["w"].strip()]
    # bo tieng dem dung rieng
    words = [w for w in words if norm(w["w"]) not in DEM]
    cau = tach_cau(words, gap)
    giu = []
    for i, c in enumerate(cau):
        sau = cau[i + 1:i + 1 + nhin_truoc]
        if any(la_noi_lai(c, d) for d in sau):
            continue  # cau nay se duoc noi lai ngay sau -> bo
        if len(c) == 1 and c[0]["p"] < 0.5:
            continue  # 1 chu le, nghe khong ro
        giu.append(c)
    doan = []
    for c in giu:
        s, e = max(0, c[0]["s"] - pad_in), c[-1]["e"] + pad_out
        if doan and s - doan[-1]["e"] < 0.12:  # dinh lien thi noi luon
            doan[-1]["e"] = e
            doan[-1]["words"] += c
            doan[-1]["text"] += " " + text_of(c)
        else:
            doan.append({"s": round(s, 3), "e": round(e, 3), "text": text_of(c), "words": c})
    for d in doan:
        d["s"], d["e"] = round(d["s"], 3), round(d["e"], 3)
    return doan


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = {k[2:].replace("-", "_"): float(v) for k, v in zip(a[2::2], a[3::2])}
    loi = json.load(open(a[0], encoding="utf-8"))
    d = cat(loi, **opt)
    json.dump(d, open(a[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    tong = sum(x["e"] - x["s"] for x in d)
    print(f"Giu {len(d)} doan, tong {tong:.1f}s / goc {loi.get('duration', 0):.1f}s")
    for x in d:
        print(f"[{x['s']:7.2f}-{x['e']:7.2f}] {x['text']}")
