"""Gop nhieu thu vien canh thanh 1 file (id co tien to ten thu vien).
python gop_thu_vien.py out.json thu_vien1 thu_vien2 ..."""
import sys, os, json
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
out, libs = sys.argv[1], sys.argv[2:]
all_ = []
for lib in libs:
    ten = os.path.basename(lib.rstrip("\\/"))
    for c in json.load(open(os.path.join(lib, "canh.json"), encoding="utf-8")):
        c = dict(c)
        c["id"] = f"{ten}:{c['id']}"
        all_.append(c)
json.dump(all_, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
dung = [c for c in all_ if "loai" not in c.get("nhan", [])]
print(len(all_), "canh,", len(dung), "dung duoc")
print(dict(Counter(n for c in dung for n in c.get("nhan", [])).most_common()))
