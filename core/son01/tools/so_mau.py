"""Cham bo cat tho: so cac doan tool chon (cat.json) voi doan anh Son tu cat trong 1 timeline cua du an mau.
python so_mau.py cat.json "<thu muc du an khuon>" "<ten timeline>" <ten file video>
In: % thoi luong anh Son giu ma tool cung giu (do phu), % tool giu ma anh Son bo (thua)."""
import sys, os, json, unicodedata
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
nfc = lambda s: unicodedata.normalize("NFC", s)


def doan_mau(khuon, timeline, ten_video):
    lay = json.load(open(os.path.join(khuon, "timeline_layout.json"), encoding="utf-8"))["dockItems"][0]
    tid = next(a for a, b in zip(lay["timelineIds"], lay["timelineNames"]) if nfc(b) == nfc(timeline))
    t = json.load(open(os.path.join(khuon, "Timelines", tid, "draft_content.json"), encoding="utf-8"))
    vids = {m["id"]: m for m in t["materials"]["videos"]}
    out = []
    for tr in t["tracks"]:
        if tr["type"] != "video":
            continue
        for s in tr["segments"]:
            m = vids.get(s["material_id"], {})
            if os.path.basename(m.get("path", "")).lower() == ten_video.lower():
                st = s["source_timerange"]["start"] / 1e6
                out.append((st, st + s["source_timerange"]["duration"] / 1e6))
    return sorted(set(out))


def giao(A, B):
    return sum(max(0, min(a1, b1) - max(a0, b0)) for a0, a1 in A for b0, b1 in B)


def cham(tool, mau):
    tm = sum(b - a for a, b in mau)
    tt = sum(b - a for a, b in tool)
    g = giao(tool, mau)
    return {"phu": g / tm if tm else 0, "thua": (tt - g) / tt if tt else 0, "giay_mau": tm, "giay_tool": tt}


if __name__ == "__main__":
    cat, khuon, tl, ten = sys.argv[1:5]
    tool = [(d["s"], d["e"]) for d in json.load(open(cat, encoding="utf-8"))]
    mau = doan_mau(khuon, tl, ten)
    k = cham(tool, mau)
    print(f"Do phu {k['phu'] * 100:.0f}% | thua {k['thua'] * 100:.0f}% | mau {k['giay_mau']:.1f}s, tool {k['giay_tool']:.1f}s")
    for a, b in mau:
        ok = giao(tool, [(a, b)]) / (b - a)
        print(f"  mau {a:7.2f}-{b:7.2f}  tool phu {ok * 100:4.0f}%")
    for a, b in tool:
        ok = giao(mau, [(a, b)]) / (b - a)
        print(f"  tool {a:7.2f}-{b:7.2f}  trung mau {ok * 100:4.0f}%")
