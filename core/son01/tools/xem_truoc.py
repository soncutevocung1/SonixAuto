"""Dung ban xem truoc MP4 tu timeline (xuat_tl.py) bang bo may Sonix + tron am thanh bang FFmpeg.

python xem_truoc.py tl.json out.mp4 [--font-dir file:///.../fonts] [--scale 540:-2]
"""
import sys, os, json, subprocess, tempfile
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("SONIX_RENDER") or os.path.abspath(os.path.join(HERE, "..", "..", "..", "render"))
GOI = os.environ.get("SONIX_KHUON", "")  # goi phong cach da cai (co thu muc fonts/)
FF = os.environ.get("SONIX_FFMPEG") or __import__("imageio_ffmpeg").get_ffmpeg_exe()

tl_path, out = sys.argv[1], sys.argv[2]
opt = dict(zip(sys.argv[3::2], sys.argv[4::2]))
tl = json.load(open(tl_path, encoding="utf-8"))
tmp = tempfile.mkdtemp(prefix="sx_xt_")

media = {}
for i, s in enumerate(tl["main"]):
    media[f"m{i}"] = {"path": s["file"], "start": s["src"], "rate": s.get("speed", 1) or 1, "dur": s["dur"] + 0.1, "scale": "720:-2"}
for i, s in enumerate(tl["broll"]):
    media[f"b{i}"] = {"path": s["file"], "start": s["src"], "rate": s.get("speed", 1) or 1, "dur": s["dur"] + 0.1, "scale": "540:-2"}
props = {"tl": tl, "fontDir": opt.get("--font-dir") or (Path(GOI, "fonts").as_uri() if GOI and os.path.isdir(os.path.join(GOI, "fonts")) else ""), "media": media}
pp = os.path.join(tmp, "props.json")
json.dump(props, open(pp, "w", encoding="utf-8"), ensure_ascii=False)

hinh = os.path.join(tmp, "hinh.mp4")
r = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "render.py"), "--comp", os.path.join(ROOT, "comps", "son01_preview.html"),
                    "--props", pp, "--out", hinh, "--quiet"])
if r.returncode != 0:
    sys.exit("Dung hinh loi")

# ---- am thanh: giong goc theo doan cat + nhac + tieng hieu ung
ins, fl = [], []
n = 0
for s in tl["main"]:
    ins += ["-ss", f"{s['src']:.3f}", "-t", f"{s['dur']:.3f}", "-i", s["file"]]
    fl.append(f"[{n}:a]aresample=48000,asetpts=PTS-STARTPTS,adelay={int(s['t0'] * 1000)}:all=1[a{n}]")
    n += 1
for a in tl["am"]:
    if not a["file"] or not os.path.exists(a["file"]):
        continue
    ins += ["-ss", f"{a['src']:.3f}", "-t", f"{a['dur']:.3f}", "-i", a["file"]]
    fl.append(f"[{n}:a]aresample=48000,asetpts=PTS-STARTPTS,volume={a.get('vol', 1):.3f},adelay={int(a['t0'] * 1000)}:all=1[a{n}]")
    n += 1
mix = "".join(f"[a{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0:dropout_transition=0,alimiter=limit=0.95[am]"
amix = os.path.join(tmp, "am.m4a")
r = subprocess.run([FF, "-v", "error", "-y", *ins, "-filter_complex", ";".join(fl) + ";" + mix, "-map", "[am]",
                    "-t", f"{tl['dai']:.3f}", "-c:a", "aac", "-b:a", "192k", amix])
if r.returncode != 0:
    sys.exit("Tron am loi")
vf = ["-vf", f"scale={opt['--scale']}"] if "--scale" in opt else []
subprocess.run([FF, "-v", "error", "-y", "-i", hinh, "-i", amix, *vf, "-c:v", "libx264", "-crf", "20", "-preset", "fast",
                "-c:a", "copy", "-shortest", "-movflags", "+faststart", out], check=True)
print("Xem truoc ->", out)
