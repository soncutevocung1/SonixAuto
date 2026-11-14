"""Lap danh muc thu vien canh: tach moi video thanh tung canh, anh xem truoc, bang so.

python thu_vien.py <thu_muc_video> <thu_muc_ra> [--nguong 27] [--min 0.8]
Ra:
  <ra>/canh.json      [{id:"28.2", file, s, e, dai, w, h, nhan:[]}]
  <ra>/bang_N.jpg     moi bang 30 canh, danh so id
  <ra>/thumbs/<id>.jpg
"""
import sys, os, json, subprocess, shutil
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scenedetect import open_video, SceneManager
from scenedetect.detectors import ContentDetector

src, out = sys.argv[1], sys.argv[2]
args = dict(zip(sys.argv[3::2], sys.argv[4::2]))
NGUONG = float(args.get("--nguong", 27))
MIN = float(args.get("--min", 0.8))
EXT = (".mp4", ".mov", ".m4v", ".webm", ".mkv")
FF = os.environ.get("SONIX_FFMPEG") or __import__("imageio_ffmpeg").get_ffmpeg_exe()
FONT = "C\\:/Windows/Fonts/arialbd.ttf" if os.name == "nt" else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
os.makedirs(os.path.join(out, "thumbs"), exist_ok=True)

files = sorted(os.path.join(r, f) for r, _, fs in os.walk(src) for f in fs if f.lower().endswith(EXT))
old = {}
pj = os.path.join(out, "canh.json")
if os.path.exists(pj):  # giu nhan da gan
    for c in json.load(open(pj, encoding="utf-8")):
        old[(c["file"], round(c["s"], 1))] = c.get("nhan", [])

canh = []
for vi, f in enumerate(files, 1):
    v = open_video(f)
    sm = SceneManager()
    sm.add_detector(ContentDetector(threshold=NGUONG, min_scene_len=int(MIN * v.frame_rate)))
    sm.detect_scenes(v, show_progress=False)
    sc = sm.get_scene_list()
    sec = lambda t: t.get_seconds() if hasattr(t, 'get_seconds') else t.seconds
    dur = sec(v.duration)
    ranges = [(sec(a), sec(b)) for a, b in sc] or [(0.0, dur)]
    w, h = v.frame_size
    for si, (s, e) in enumerate(ranges, 1):
        if e - s < MIN:
            continue
        cid = f"{vi}.{si}"
        th = os.path.join(out, "thumbs", cid + ".jpg")
        subprocess.run([FF, "-v", "error", "-y", "-ss", f"{(s + e) / 2:.2f}", "-i", f, "-frames:v", "1",
                        "-vf", f"scale=180:320:force_original_aspect_ratio=decrease,pad=180:320:(ow-iw)/2:(oh-ih)/2,"
                               f"drawtext=fontfile='{FONT}':text='{cid}':x=4:y=4:fontsize=24:fontcolor=yellow:box=1:boxcolor=black@0.8",
                        th])
        canh.append({"id": cid, "file": f, "s": round(s, 2), "e": round(e, 2), "dai": round(e - s, 2),
                     "w": w, "h": h, "nhan": old.get((f, round(s, 1)), [])})
    print(vi, len(ranges), "canh", os.path.basename(f), flush=True)

json.dump(canh, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
# bang anh
tmp = os.path.join(out, "_tmp")
os.makedirs(tmp, exist_ok=True)
for b in range(0, len(canh), 30):
    for n, c in enumerate(canh[b:b + 30]):
        shutil.copy(os.path.join(out, "thumbs", c["id"] + ".jpg"), os.path.join(tmp, f"{n:04d}.jpg"))
    subprocess.run([FF, "-v", "error", "-y", "-framerate", "1", "-i", os.path.join(tmp, "%04d.jpg"),
                    "-vf", "tile=10x3:padding=3:color=0x111111", "-frames:v", "1", os.path.join(out, f"bang_{b // 30 + 1}.jpg")])
    for x in os.listdir(tmp):
        os.remove(os.path.join(tmp, x))
shutil.rmtree(tmp, ignore_errors=True)
print("XONG", len(files), "video,", len(canh), "canh")
