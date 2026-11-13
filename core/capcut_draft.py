"""Tạo dự án CapCut mới từ dự án mẫu của bác (Sonix Edit Video).

Cách làm: chép dự án mẫu (vd 'mẫu') sang thư mục mới rồi sửa draft_content.json:
- Lớp video chính: thay bằng các đoạn clip mới (giữ tốc độ, tắt tiếng như mẫu).
- Lớp giọng: thay file giọng mới. Mọi lớp khác (điều chỉnh màu, theme, chữ, người dẫn) kéo dài theo giọng.
- Lớp nhạc: thay nhạc, tự nối lặp nếu nhạc ngắn hơn giọng.
- Tiêu đề: thay chữ, tô màu từng đoạn (vàng / trắng) giữ nguyên font, viền.
- Mũi tên: dời về cuối video.
Sau đó đăng ký dự án vào danh sách của CapCut (root_meta_info.json). CapCut phải TẮT khi tạo.
"""
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import uuid
from pathlib import Path

from core.video_utils import _ffmpeg, probe

CAPCUT_DRAFTS = Path(os.path.expandvars(r"%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft"))
US = 1_000_000  # CapCut tính thời gian bằng micro giây
YELLOW = [0.95686274766922, 0.7803921699523926, 0.05882352963089943]
WHITE = [1.0, 1.0, 1.0]
_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
_LP = "\\\\?\\" if sys.platform == "win32" else ""  # đường dẫn dài trên Windows

# Danh sách vật liệu gắn theo từng đoạn: đoạn bị bỏ thì dọn khỏi danh sách này
_PER_SEGMENT = ("videos", "audios", "speeds", "canvases", "placeholder_infos", "sound_channel_mappings",
                "material_colors", "vocal_separations", "beats", "loudnesses", "audio_fades")


class CapCutError(Exception):
    pass


def capcut_dang_mo() -> bool:
    try:
        p = subprocess.run(["tasklist", "/FI", "IMAGENAME eq CapCut.exe", "/NH"], capture_output=True,
                           text=True, encoding="utf-8", errors="ignore", creationflags=_NO_WINDOW)
        return "CapCut.exe" in p.stdout
    except Exception:
        return False


def danh_sach_du_an() -> list:
    try:
        root = json.loads((CAPCUT_DRAFTS / "root_meta_info.json").read_text(encoding="utf-8"))
        return [e["draft_name"] for e in root.get("all_draft_store", [])]
    except Exception:
        return []


def _uid() -> str:
    return str(uuid.uuid4()).upper()


def _us(sec: float) -> int:
    return int(round(sec * US))


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _fwd(p) -> str:
    return str(p).replace("\\", "/")


def tach_nhac(src: str, out_dir: Path) -> str:
    """Video nhạc (.mp4) -> file âm thanh .m4a (chỉ tách 1 lần)."""
    src = Path(src)
    if src.suffix.lower() in (".mp3", ".m4a", ".wav", ".aac"):
        return str(src)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / (src.stem + ".m4a")
    if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
        subprocess.run([_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-vn",
                        "-c:a", "copy", str(out)], check=True, creationflags=_NO_WINDOW)
    return str(out)


class _Draft:
    def __init__(self, d: dict):
        self.d = d
        self.m = d["materials"]

    def find(self, mid):
        for k, v in self.m.items():
            if isinstance(v, list):
                for x in v:
                    if isinstance(x, dict) and x.get("id") == mid:
                        return k, x
        return None, None

    def clone_seg(self, seg: dict) -> dict:
        """Nhân bản 1 đoạn kèm vật liệu phụ (tốc độ, khung, kênh âm...) với id mới."""
        s = copy.deepcopy(seg)
        s["id"] = _uid()
        refs = []
        for r in seg.get("extra_material_refs", []):
            k, mat = self.find(r)
            if mat is None:
                continue
            n = copy.deepcopy(mat)
            n["id"] = _uid()
            self.m[k].append(n)
            refs.append(n["id"])
        s["extra_material_refs"] = refs
        return s

    def clone_mat(self, mid: str, **changes) -> str:
        k, mat = self.find(mid)
        n = copy.deepcopy(mat)
        n["id"] = _uid()
        n.update(changes)
        self.m[k].append(n)
        return n["id"]

    def prune(self):
        used = set()
        for t in self.d["tracks"]:
            for s in t["segments"]:
                used.add(s["material_id"])
                used.update(s.get("extra_material_refs", []))
        for k in _PER_SEGMENT:
            if isinstance(self.m.get(k), list):
                self.m[k] = [x for x in self.m[k] if x.get("id") in used]


def _set_range(seg, start_us, dur_us, src_start_us=None, src_dur_us=None):
    seg["target_timerange"] = {"start": int(start_us), "duration": int(dur_us)}
    if seg.get("source_timerange") is not None or src_dur_us is not None:
        seg["source_timerange"] = {"start": int(src_start_us or 0), "duration": int(src_dur_us or dur_us)}


def _tracks(d: dict) -> dict:
    """Nhận ra từng lớp của dự án mẫu."""
    dr = _Draft(d)
    out = {"main": None, "theme": None, "presenter": None, "adjust": [], "texts": [], "sticker": None,
           "voice": None, "music": None}
    audios = []
    for t in d["tracks"]:
        typ, segs = t["type"], t["segments"]
        if not segs:
            continue
        if typ == "video":
            _, mat = dr.find(segs[0]["material_id"])
            name = (mat or {}).get("path", "").lower()
            if name.endswith((".png", ".jpg", ".jpeg", ".webp")):
                out["theme"] = t
            elif t.get("flag") == 0 and out["main"] is None:
                out["main"] = t
            else:
                out["presenter"] = t
        elif typ == "adjust":
            out["adjust"].append(t)
        elif typ == "text":
            out["texts"].append(t)
        elif typ == "sticker":
            out["sticker"] = t
        elif typ == "audio":
            audios.append(t)
    if audios:
        out["voice"] = audios[0]
    if len(audios) > 1:
        out["music"] = audios[1]
    if not out["main"] or not out["voice"]:
        raise CapCutError("Dự án mẫu thiếu lớp video chính hoặc lớp giọng")
    return out


def _title_text(d: dict):
    """Tiêu đề = chữ dài nhất (nhãn 'phân bón chính hãng' ngắn hơn)."""
    best = None
    for t in d["materials"]["texts"]:
        c = json.loads(t["content"])
        if best is None or len(c["text"]) > len(best[1]["text"]):
            best = (t, c)
    return best


def title_parts(title: str) -> list:
    """Tiêu đề 3 dòng -> tô màu như anh Sơn: cả dòng 1 vàng, dòng 2-3 trắng."""
    lines = [ln.strip() for ln in _nfc(title).strip().split("\n") if ln.strip()]
    if not lines:
        return []
    parts = [(lines[0], "vang")]
    if len(lines) > 1:
        parts.append(("\n" + "\n".join(lines[1:]), "trang"))
    return parts


def set_title(d: dict, parts):
    """parts = [(chữ, 'vang'|'trang'), ...] hoặc chuỗi tiêu đề (dòng 1 vàng, còn lại trắng)."""
    if isinstance(parts, str):
        parts = title_parts(parts)
    t, c = _title_text(d)
    base = c["styles"][0]
    text, styles, pos = "", [], 0
    for part, color in parts:
        part = _nfc(part)
        if not part:
            continue
        st = copy.deepcopy(base)
        st["range"] = [pos, pos + len(part)]
        st["fill"]["content"]["solid"]["color"] = YELLOW if color in ("vang", "yellow", YELLOW) else WHITE
        styles.append(st)
        text += part
        pos += len(part)
    c["text"], c["styles"] = text, styles
    t["content"] = json.dumps(c, ensure_ascii=False)


VIDEO_Y = 0.53     # đẩy video lên (anh Sơn chỉnh tay: 0.53) để dải xanh không che sản phẩm
VIDEO_Y_MAX = 0.82  # quá mức này mép dưới video cao hơn dải xanh (theme.png: dải xanh từ ~58.5%)
LUOI_DAY = 0.66     # khung 4 ô phủ từ đỉnh tới 66% chiều cao (lấn xuống phần dải xanh mờ, không hở)


def _o_luoi(j: int, w: int, h: int, cw: int = 1080, ch: int = 1920):
    """Ô thứ j (0-3) của khung 2x2 phía trên dải xanh -> (scale, x, y, crop) theo đơn vị CapCut.
    scale 1 = video vừa khít khung; x, y: 1 = nửa khung, y dương là lên trên; cắt đều 2 bên cho đầy ô."""
    fit = min(cw / w, ch / h)
    bw, bh = w * fit, h * fit                      # kích thước khi scale = 1
    ow, oh = cw / 2, ch * LUOI_DAY / 2             # kích thước 1 ô
    s = max(ow / bw, oh / bh)
    fx, fy = ow / (s * bw), oh / (s * bh)          # phần giữ lại theo chiều ngang / dọc
    x0, y0 = (1 - fx) / 2, (1 - fy) / 2
    crop = {"upper_left_x": x0, "upper_left_y": y0, "upper_right_x": 1 - x0, "upper_right_y": y0,
            "lower_left_x": x0, "lower_left_y": 1 - y0, "lower_right_x": 1 - x0, "lower_right_y": 1 - y0}
    col, row = j % 2, j // 2
    x = -0.5 if col == 0 else 0.5
    top = 1.0 - row * LUOI_DAY                     # mép trên ô (đơn vị nửa khung: 2 = cả khung)
    y = top - LUOI_DAY / 2
    return s, x, y, crop


def build_content(d: dict, clips: list, voice: str, music: str = "", title_parts=None,
                  music_volume: float = None, video_y: float = VIDEO_Y) -> int:
    """Sửa draft_content (dict) tại chỗ.
    clips = [(đường dẫn, giây bắt đầu, số giây lấy ở video gốc[, độ đẩy lên riêng]), ...].
    Trả về độ dài video (micro giây)."""
    dr = _Draft(d)
    tr = _tracks(d)
    vinfo = probe(voice)
    total = _us(vinfo["duration"])
    if total <= 0:
        raise CapCutError(f"Không đọc được độ dài file giọng: {voice}")

    # 1) Lớp video chính
    main = tr["main"]
    tseg = main["segments"][0]
    tmat_id = tseg["material_id"]
    speed = float(tseg.get("speed") or 1.0)
    new_segs, pos, i, mats = [], 0, 0, {}
    if not clips:
        raise CapCutError("Chưa có clip nào")
    luoi_tracks = []

    def _luoi(cells, pos):
        """Khung 4 ô trên 4 lớp chồng; lớp chính chạy video ô 1 phủ kín khung làm nền
        (để phần dưới dải xanh không lộ nền đen)."""
        g = min(_us(c[2] / speed) for c in cells)
        g = min(g, total - pos)
        path0, start0, _ = cells[0]
        info0 = probe(path0)
        nen = dr.clone_seg(tseg)
        nen["material_id"] = dr.clone_mat(tmat_id, path=_fwd(path0), duration=_us(info0["duration"]),
                                          width=info0["width"], height=info0["height"],
                                          material_name=Path(path0).name, local_material_id=str(uuid.uuid4()),
                                          media_path="", material_id="", origin_material_id="")
        _set_range(nen, pos, g, _us(start0), int(g * speed))
        nen["clip"]["transform"] = {"x": 0.0, "y": 0.0}
        new_segs.append(nen)
        while len(luoi_tracks) < 4:
            t = {k: v for k, v in main.items() if k != "segments"}
            t.update(id=str(uuid.uuid4()).upper(), flag=2, segments=[])
            luoi_tracks.append(t)
        for j, (path, src_start, _) in enumerate(cells):
            info = probe(path)
            sc, x, y, crop = _o_luoi(j, info["width"] or 1080, info["height"] or 1920)
            mid = dr.clone_mat(tmat_id, path=_fwd(path), duration=_us(info["duration"]),
                               width=info["width"], height=info["height"], material_name=Path(path).name,
                               local_material_id=str(uuid.uuid4()), media_path="", material_id="",
                               origin_material_id="", crop=crop, crop_ratio="free", crop_scale=1.0)
            s = dr.clone_seg(tseg)
            s["material_id"] = mid
            _set_range(s, pos, g, _us(src_start), int(g * speed))
            s["clip"]["scale"] = {"x": sc, "y": sc}
            s["clip"]["transform"] = {"x": x, "y": y}
            luoi_tracks[j]["segments"].append(s)
        return g

    while pos < total:
        clip = clips[i % len(clips)]
        if isinstance(clip, dict):
            i += 1
            pos += _luoi(clip["luoi"], pos)
            continue
        path, src_start, src_len = clip[0], clip[1], clip[2]
        y = clip[3] if len(clip) > 3 and clip[3] is not None else video_y
        i += 1
        if path not in mats:
            info = probe(path)
            mats[path] = (dr.clone_mat(tmat_id, path=_fwd(path), duration=_us(info["duration"]),
                                       width=info["width"], height=info["height"],
                                       material_name=Path(path).name, local_material_id=str(uuid.uuid4()),
                                       media_path="", material_id="", origin_material_id=""), info)
        mid, info = mats[path]
        src_len = min(src_len, max(0.2, info["duration"] - src_start))
        dur = min(_us(src_len / speed), total - pos)
        s = dr.clone_seg(tseg)
        s["material_id"] = mid
        _set_range(s, pos, dur, _us(src_start), int(dur * speed))
        if s.get("clip"):
            s["clip"].setdefault("transform", {"x": 0.0, "y": 0.0})
            s["clip"]["transform"]["y"] = max(0.0, min(float(y), VIDEO_Y_MAX))
        new_segs.append(s)
        pos += dur
        if i > 2000:
            raise CapCutError("Clip quá ngắn")
    main["segments"] = new_segs
    if luoi_tracks:
        k = d["tracks"].index(main)
        d["tracks"][k + 1:k + 1] = luoi_tracks

    # 2) Lớp kéo dài hết video
    for t in tr["adjust"] + tr["texts"] + ([tr["theme"]] if tr["theme"] else []):
        for s in t["segments"][:1]:
            src = s.get("source_timerange")
            _set_range(s, 0, total, (src or {}).get("start", 0) if src else None, total if src else None)
        t["segments"] = t["segments"][:1]

    # 3) Người dẫn: nối lặp như mẫu (đoạn đầu dùng đoạn 1, các đoạn sau dùng đoạn 2 có hiệu ứng)
    if tr["presenter"]:
        ps = tr["presenter"]["segments"]
        first, later = ps[0], ps[1] if len(ps) > 1 else ps[0]
        piece = first["target_timerange"]["duration"]
        src0 = first["source_timerange"]["start"]
        segs, pos, k = [], 0, 0
        while pos < total:
            s = dr.clone_seg(first if k == 0 else later)
            dur = min(piece, total - pos)
            _set_range(s, pos, dur, src0, dur)
            segs.append(s)
            pos += dur
            k += 1
        tr["presenter"]["segments"] = segs

    # 4) Mũi tên: giữ độ dài, dời về cuối
    if tr["sticker"]:
        s = tr["sticker"]["segments"][0]
        dur = min(s["target_timerange"]["duration"], total)
        _set_range(s, total - dur, dur, 0 if s.get("source_timerange") is not None else None,
                   dur if s.get("source_timerange") is not None else None)
        tr["sticker"]["segments"] = [s]

    # 5) Giọng
    vseg = tr["voice"]["segments"][0]
    vid = dr.clone_mat(vseg["material_id"], path=_fwd(voice), duration=total, name=Path(voice).stem,
                       type="extract_music", music_id=str(uuid.uuid4()))
    s = dr.clone_seg(vseg)
    s["material_id"] = vid
    _set_range(s, 0, total, 0, total)
    tr["voice"]["segments"] = [s]

    # 6) Nhạc: nối lặp nếu ngắn
    if tr["music"] and music:
        mseg = tr["music"]["segments"][0]
        mdur = _us(probe(music)["duration"])
        if mdur > 0:
            mid = dr.clone_mat(mseg["material_id"], path=_fwd(music), duration=mdur, name=Path(music).stem,
                               type="extract_music", music_id=str(uuid.uuid4()))
            segs, pos = [], 0
            while pos < total:
                s = dr.clone_seg(mseg)
                s["material_id"] = mid
                dur = min(mdur, total - pos)
                _set_range(s, pos, dur, 0, dur)
                if music_volume is not None:
                    s["volume"] = music_volume
                segs.append(s)
                pos += dur
            tr["music"]["segments"] = segs

    if title_parts:
        set_title(d, title_parts)
    d["duration"] = total
    dr.prune()
    return total


def _copy_tree(src: Path, dst: Path, needed_media: set):
    """Chép dự án mẫu: file cấu hình chép thật; media (matting, materials) dùng hard link; bỏ media không dùng."""
    s_l, d_l = _LP + str(src), _LP + str(dst)

    def cp(a, b):
        rel = os.path.relpath(a, s_l).replace("\\", "/")
        if rel.startswith("materials/"):
            if rel not in needed_media:
                return b
        elif not rel.startswith("matting/"):
            return shutil.copy2(a, b)
        try:
            os.link(a, b)
        except OSError:
            shutil.copy2(a, b)
        return b

    shutil.copytree(s_l, d_l, copy_function=cp, ignore=shutil.ignore_patterns(".locked", "draft_content.json.bak", "template-2.tmp"))


def _needed_media(d: dict) -> set:
    out = set()
    for k in ("videos", "audios"):
        for x in d["materials"].get(k, []):
            p = x.get("path", "")
            if p.startswith("##_draftpath_placeholder"):
                out.add(p.split("##/", 1)[1])
    return out


def _tu_du(dst: Path, khuon: Path = None):
    """Cho dự án tự đủ file: media mà clip ghép (vd người dẫn) trỏ tới thư mục dự án KHÁC (khuôn) -> hard link vào
    materials của chính dự án và sửa đường dẫn. File trỏ về chính dự án mà thiếu -> tìm trong khuôn để link.
    (CapCut có lúc tự đổi đường dẫn clip ghép về thư mục dự án mà không chép file -> báo 'Media Not Found'.)"""
    goc = _fwd(CAPCUT_DRAFTS) + "/"
    moi = _fwd(dst) + "/"
    tim = [p for p in ([khuon] if khuon else []) + [CAPCUT_DRAFTS / "mẫu"] if p]
    for f in Path(_LP + str(dst)).rglob("draft_content.json"):
        t = f.read_text(encoding="utf-8")
        t2 = t
        for m in set(re.findall(re.escape(goc) + r'([^/"]+)/((?:materials|matting)/[^"]+)', t)):
            ten, rel = m
            rel_os = rel.replace("/", os.sep)
            dich = Path(_LP + str(dst / rel_os))
            if not dich.exists():
                nguon = [CAPCUT_DRAFTS / ten / rel_os] + [p / rel_os for p in tim]
                for s in nguon:
                    if os.path.exists(_LP + str(s)):
                        dich.parent.mkdir(parents=True, exist_ok=True)
                        try:
                            os.link(_LP + str(s), dich)
                        except OSError:
                            shutil.copy2(_LP + str(s), dich)
                        break
            if ten != dst.name:
                t2 = t2.replace(goc + ten + "/" + rel, moi + rel)
        if t2 != t:
            f.write_text(t2, encoding="utf-8")


def tao_du_an(template: str, name: str, clips: list, voice: str, music: str = "", title_parts=None,
              music_volume: float = None, video_y: float = VIDEO_Y) -> dict:
    """Tạo dự án CapCut mới. Trả về {'name', 'path', 'duration'}."""
    if capcut_dang_mo():
        raise CapCutError("CapCut đang mở. Bác tắt CapCut rồi bấm lại.")
    src = CAPCUT_DRAFTS / template
    if not (src / "draft_content.json").exists():
        raise CapCutError(f"Không thấy dự án mẫu '{template}' trong CapCut")
    base, n = name, 2
    while (CAPCUT_DRAFTS / name).exists() or name in danh_sach_du_an():
        name, n = f"{base} ({n})", n + 1
    dst = CAPCUT_DRAFTS / name

    d = json.loads((src / "draft_content.json").read_text(encoding="utf-8"))
    total = build_content(d, clips, voice, music, title_parts, music_volume, video_y)
    content = json.dumps(d, ensure_ascii=False)

    _copy_tree(src, dst, _needed_media(d))
    try:
        _tu_du(dst, src)
        targets = [dst / "draft_content.json"]
        tl = dst / "Timelines"
        if tl.exists():
            targets += [p for p in tl.glob("*/draft_content.json")]
        for f in targets:
            Path(_LP + str(f)).write_text(content, encoding="utf-8")
            patch = f.parent / "attachment" / "patch" / "mini_draft.json"
            if patch.exists():
                os.remove(_LP + str(patch))

        now = int(time.time() * US)
        new_id = _uid()
        cloud_reset = {"tm_draft_cloud_entry_id": -1, "tm_draft_cloud_parent_entry_id": -1,
                       "tm_draft_cloud_space_id": -1, "tm_draft_cloud_user_id": -1,
                       "tm_draft_cloud_modified": 0, "tm_draft_cloud_completed": "",
                       "cloud_draft_sync": False, "draft_cloud_last_action_download": False}
        mp = dst / "draft_meta_info.json"
        meta = json.loads(mp.read_text(encoding="utf-8"))
        meta.update(cloud_reset)
        meta.update({"draft_id": new_id, "draft_name": name, "draft_fold_path": _fwd(dst),
                     "tm_draft_create": now, "tm_draft_modified": now, "tm_duration": total})
        mp.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

        rp = CAPCUT_DRAFTS / "root_meta_info.json"
        shutil.copy2(rp, CAPCUT_DRAFTS / "root_meta_info.json.sonix_backup")
        root = json.loads(rp.read_text(encoding="utf-8"))
        tmpl = next((e for e in root["all_draft_store"] if e.get("draft_name") == template),
                    root["all_draft_store"][0])
        e = copy.deepcopy(tmpl)
        e.update(cloud_reset)
        e.update({"draft_id": new_id, "draft_name": name, "draft_fold_path": _fwd(dst),
                  "draft_json_file": _fwd(dst) + "\\draft_content.json",
                  "draft_cover": _fwd(dst) + "\\draft_cover.jpg",
                  "tm_draft_create": now, "tm_draft_modified": now, "tm_duration": total})
        root["all_draft_store"].insert(0, e)
        tmp = rp.with_suffix(".json.sonix_tmp")
        tmp.write_text(json.dumps(root, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, rp)
    except Exception:
        shutil.rmtree(_LP + str(dst), ignore_errors=True)
        raise
    return {"name": name, "path": str(dst), "duration": total / US}
