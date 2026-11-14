"""Ap lai luat san pham tren chu da doc (truong 'ocr') - khong can doc lai.
TC01 chi nhan khi thay 'TC01' (ke ca kieu doc lech TCO1/7CO1) hoac 'GIAM CANH'
(nhan Dam ca co in cong dung 'kich re, vot dot' -> khong dung 'KICH RE' de nhan dien TC01)."""
import sys, json, re, unicodedata
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
pj = sys.argv[1]
canh = json.load(open(pj, encoding="utf-8"))


def bo_dau(s):
    s = unicodedata.normalize("NFD", s.upper().replace("Đ", "D").replace("đ", "D"))
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


TC01 = [r"[T7]\s*C\s*[O0]\s*1\b", r"GIAM\s*CANH"]
doi = 0
for c in canh:
    if "ocr" not in c:
        continue
    txt = bo_dau(c["ocr"])
    co_tc = any(re.search(p, txt) for p in TC01)
    nhan_dam_ca_co_chu_kich_re = re.search(r"KICH\s*RE", txt) and re.search(r"DAM\s*CA|AMINO", txt)
    if "sp_tc01" in c["nhan"] and not co_tc and nhan_dam_ca_co_chu_kich_re:
        # 'kich re' la chu cong dung in tren nhan can Dam ca, khong phai chai TC01 -> go nhan nham
        c["nhan"].remove("sp_tc01"); doi += 1
    if co_tc and "sp_tc01" not in c["nhan"]:
        c["nhan"].append("sp_tc01"); doi += 1
json.dump(canh, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
dung = [c for c in canh if "loai" not in c["nhan"]]
print("doi", doi, "nhan | dung duoc", len(dung), "|", dict(Counter(t for c in dung for t in c["nhan"] if t.startswith("sp_"))))
print("Dam ca sach (khong TC01/khac):", sum(1 for c in dung if "sp_dam_ca" in c["nhan"] and not {"sp_tc01", "sp_khac"} & set(c["nhan"])))
