"""Kiem tra chu chong nhau trong du an CapCut: 2 doan chu hien cung luc ma khoang doc giao nhau.
python kiem_chong.py "<ten du an (glob)>" [thu_muc_drafts]
Chieu cao 1 dong ~0.12 (toa do CapCut) o scale 0.66; chu mo dau 2 dong cua khuon (0.47 / 0.34) la thiet ke cua anh Son."""
import sys, json, glob, os
sys.stdout.reconfigure(encoding="utf-8")
goc = sys.argv[2] if len(sys.argv) > 2 else r"E:\Capcut\CapCut Drafts"
d = glob.glob(os.path.join(goc, sys.argv[1]))[0]
t = json.load(open(os.path.join(d, "draft_content.json"), encoding="utf-8"))
M = {m["id"]: m for m in t["materials"]["texts"]}
L = []
for tr in t["tracks"]:
    if tr["type"] != "text":
        continue
    for s in tr["segments"]:
        tx = json.loads(M[s["material_id"]]["content"])["text"]
        sc = s["clip"]["scale"]["x"]
        h = (tx.count("\n") + 1) * 0.12 * sc / 0.66 if not tx.isdigit() else 0.18
        y, x = s["clip"]["transform"]["y"], s["clip"]["transform"]["x"]
        a = s["target_timerange"]["start"] / 1e6
        L.append((a, a + s["target_timerange"]["duration"] / 1e6, y - h / 2, y + h / 2, x, tx))
loi = 0
for i, p in enumerate(L):
    for q in L[i + 1:]:
        if min(p[1], q[1]) - max(p[0], q[0]) > 0.05 and min(p[3], q[3]) - max(p[2], q[2]) > 0.01:
            if p[5].isdigit() and abs(p[4] - q[4]) > 0.3 and abs(q[4]) < 0.1 and len(q[5]) < 12:
                continue
            loi += 1
            print(f"CHONG {max(p[0], q[0]):5.1f}s  {p[5]!r} (y {(p[2]+p[3])/2:+.2f})  x  {q[5]!r} (y {(q[2]+q[3])/2:+.2f})")
print("so cho chong:", loi)
