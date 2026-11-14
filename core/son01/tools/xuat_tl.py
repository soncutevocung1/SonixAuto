"""Doc du an CapCut (draft_content.json) -> timeline JSON gon cho bo dung xem truoc.

python xuat_tl.py <draft_content.json> <tl.json>
"""
import sys, json, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
US = 1_000_000

d = json.load(open(sys.argv[1], encoding="utf-8"))
m = d["materials"]
idx = {}
for k, lst in m.items():
    if isinstance(lst, list):
        for x in lst:
            if isinstance(x, dict) and x.get("id"):
                idx[x["id"]] = (k, x)


def s(us):
    return round(us / US, 4)


tl = {"dai": s(d["duration"]), "fps": d.get("fps", 30), "w": d["canvas_config"]["width"], "h": d["canvas_config"]["height"],
      "main": [], "broll": [], "mo": [], "glow": [], "chu": [], "am": []}
vids = [t for t in d["tracks"] if t["type"] == "video" and t["segments"]]
main = max(vids, key=lambda t: sum(x["target_timerange"]["duration"] for x in t["segments"])) if vids else None
for t in d["tracks"]:
    for sg in t["segments"]:
        k, mat = idx.get(sg["material_id"], (None, {}))
        tr = sg["target_timerange"]
        src = sg.get("source_timerange") or {"start": 0, "duration": tr["duration"]}
        clip = sg.get("clip") or {}
        base = {"t0": s(tr["start"]), "dur": s(tr["duration"])}
        refs = [idx.get(r, (None, {}))[0] for r in sg.get("extra_material_refs", [])]
        if t["type"] == "video":
            item = dict(base, file=mat.get("path", ""), src=s(src["start"]), src_dur=s(src["duration"]),
                        speed=sg.get("speed", 1), scale=clip.get("scale", {}).get("x", 1),
                        x=clip.get("transform", {}).get("x", 0), y=clip.get("transform", {}).get("y", 0),
                        w=mat.get("width"), h=mat.get("height"))
            kf = []
            for ck in sg.get("common_keyframes") or []:
                if ck.get("property_type") == "KFTypeScaleX":
                    kf = [(s(p["time_offset"] - src["start"]), p["values"][0]) for p in ck["keyframe_list"]]
            item["kf_scale"] = kf
            if t is main:
                tl["main"].append(item)
            elif "drafts" in refs or "combination" in item["file"]:
                tl["glow"].append(dict(base, scale=item["scale"], y=item["y"]))
            else:
                tl["broll"].append(item)
        elif t["type"] == "effect":
            tl["mo"].append(base)
        elif t["type"] == "text":
            c = json.loads(mat.get("content", "{}"))
            sty = []
            for st in c.get("styles", []):
                sty.append({"a": st["range"][0], "b": st["range"][1],
                            "color": st.get("fill", {}).get("content", {}).get("solid", {}).get("color", [1, 1, 1]),
                            "bold": bool(st.get("bold")), "font": os.path.basename(st.get("font", {}).get("path", "")),
                            "size": st.get("size", 15)})
            tl["chu"].append(dict(base, text=c.get("text", ""), styles=sty, scale=clip.get("scale", {}).get("x", 1),
                                  x=clip.get("transform", {}).get("x", 0), y=clip.get("transform", {}).get("y", 0)))
        elif t["type"] == "audio":
            tl["am"].append(dict(base, file=mat.get("path", ""), src=s(src["start"]), vol=sg.get("volume", 1),
                                 loai=mat.get("type"), ten=mat.get("name", "")))
json.dump(tl, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"dai {tl['dai']}s | main {len(tl['main'])} | broll {len(tl['broll'])} | chu {len(tl['chu'])} | am {len(tl['am'])}")
