"""Quy trinh tron goi phong cach "Son 01".

python son01.py <video_goc> --sp sp_dam_ca --san-pham "Dam ca Amino (can 5 lit)" --ten "SONIX SON 01 - DAM CA"
    [--thu-vien <thu_vien>/tat_ca.json] [--khuon <thu muc khuon | ten du an CapCut>] [--timeline "Dam shop Bo"]
    [--dai 36] [--model claude-opus-5-5] [--cham claude-sonnet-5-5] [--vong 3] [--dat 8]

Buoc: nghe (Whisper) -> cat tho -> ke hoach (Claude) -> du an CapCut -> xem truoc MP4 -> cham diem (Claude xem khung)
-> neu < dat diem: dua loi vao ke hoach, tao lai (toi da --vong lan).
"""
import sys, os, json, subprocess, shutil
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOOLS = Path(__file__).parent
PY = sys.executable


def chay(*args):
    print(">>", " ".join(str(a) for a in args[:3]), "...", flush=True)
    r = subprocess.run([PY, "-I", *[str(a) for a in args]])
    if r.returncode != 0:
        sys.exit(f"Loi o buoc {args[0]}")


a = sys.argv[1:]
video = a[0]
opt = dict(zip(a[1::2], a[2::2]))
ten = opt.get("--ten", "SONIX SON 01")
sp = opt.get("--sp", "")
DATA = Path(os.environ.get("SONIX_DATA") or Path(__file__).resolve().parents[3] / "data" / "son01")
work = Path(opt.get("--lam-viec", DATA / "viec" / Path(video).stem))
work.mkdir(parents=True, exist_ok=True)
dat, vong = float(opt.get("--dat", 8)), int(opt.get("--vong", 3))

loi, cat, kh = work / "loi.json", work / "cat.json", work / "kehoach.json"
if not loi.exists():
    chay(TOOLS / "nghe_chu.py", video, loi, opt.get("--whisper", "large-v3-turbo"))
if not cat.exists():
    chay(TOOLS / "cat_tho.py", loi, cat)

gop_y = ""
ket_qua = None
for v in range(1, vong + 1):
    print(f"\n===== VONG {v} =====", flush=True)
    args = [TOOLS / "ke_hoach.py", cat, kh, "--san-pham", opt.get("--san-pham", ""), "--dai", opt.get("--dai", "36"),
            "--model", opt.get("--model", "claude-opus-5-5")]
    if gop_y:
        (work / "gop_y.txt").write_text(gop_y, encoding="utf-8")
        args += ["--gop-y", work / "gop_y.txt"]
    chay(*args)
    k = json.loads(kh.read_text(encoding="utf-8"))
    k["sp"] = sp
    kh.write_text(json.dumps(k, ensure_ascii=False, indent=1), encoding="utf-8")

    sys.path.insert(0, str(TOOLS))
    import capcut_son01 as cs
    kq = cs.tao(str(kh), video, f"{ten} (v{v})", opt.get("--khuon"), opt.get("--timeline"),
                opt.get("--thu-vien", str(DATA / "thu_vien" / "tat_ca.json")))
    print("Du an CapCut:", kq["ten"], f"{kq['giay']:.1f}s", flush=True)
    tl = work / f"tl_v{v}.json"
    chay(TOOLS / "xuat_tl.py", Path(kq["thu_muc"]) / "draft_content.json", tl)
    mp4 = work / f"xem_truoc_v{v}.mp4"
    chay(TOOLS / "xem_truoc.py", tl, mp4)
    cham = work / f"cham_v{v}"
    chay(TOOLS / "cham_diem.py", tl, mp4, cham, "--ai", opt.get("--cham", "claude-sonnet-5-5"))
    d = json.loads((cham / "diem.json").read_text(encoding="utf-8"))
    ket_qua = {"vong": v, "du_an": kq["ten"], "xem_truoc": str(mp4), "diem": d["tong"], "loi": d["loi"]}
    print(f"Vong {v}: {d['tong']}/10", flush=True)
    if d["tong"] >= dat:
        break
    gop_y = "Lần dựng trước bị chấm {}/10. Lỗi cần tránh:\n".format(d["tong"]) + "\n".join(
        f"- {l['giay']:.1f}s [{l['tieu_chi']}] {l['mo_ta']} -> {l['cach_sua']}" for l in d["loi"])

(work / "ket_qua.json").write_text(json.dumps(ket_qua, ensure_ascii=False, indent=1), encoding="utf-8")
print("\nKET QUA:", json.dumps(ket_qua, ensure_ascii=False)[:600])
