"""Khuôn CapCut cho phong cách Reup Aff: đóng gói trên máy anh Sơn, tự cài trên máy khác.

Gói (zip) gồm:
  khuon/        dự án CapCut "mẫu" đã lược: file cấu hình, subdraft (clip ghép người dẫn...), matting, và chỉ
                những file media mà khuôn thật sự dùng (nền theme, người dẫn...)
  tai_nguyen/   nhạc nền trong TÀI NGUYÊN (không lấy video người dẫn gốc vì khuôn đã có)
  goi.json      tên khuôn, đường dẫn gốc lúc đóng gói (để sửa sang máy mới), mục đăng ký dự án mẫu cho CapCut
Gói đưa lên GitHub Releases (tag khuon-reup-aff); app tải về khi máy thiếu khuôn.
"""
import copy
import json
import os
import re
import shutil
import tempfile
import time
import uuid
import zipfile
from pathlib import Path

from .capcut_draft import CAPCUT_DRAFTS, _LP, capcut_dang_mo, CapCutError

TEN = "mẫu"
TAG = "khuon-reup-aff"
TEN_ZIP = "khuon_reup_aff.zip"
REPO = "soncutevocung1/SonixAuto"
URL = f"https://github.com/{REPO}/releases/download/{TAG}/{TEN_ZIP}"
_JSON_GIU = re.compile(r"\.(json|extra|tmp|bak)$|^draft_settings$|^timeline_layout\.json$", re.I)


def _fwd(p) -> str:
    return str(p).replace("\\", "/")


def _duong_dan(text: str, goc: str) -> set:
    """Các file trong khuôn được nhắc tới (dạng tuyệt đối theo goc hoặc dạng placeholder) -> đường dẫn tương đối."""
    out = set()
    for m in re.finditer(r'"path"\s*:\s*"([^"]+)"', text):
        p = m.group(1).replace("\\\\", "/").replace("\\", "/")
        if p.startswith("##_draftpath_placeholder"):
            out.add(p.split("##/", 1)[1])
        elif p.lower().startswith(goc.lower() + "/"):
            out.add(p[len(goc) + 1:])
    return out


def co_khuon() -> bool:
    return (CAPCUT_DRAFTS / TEN / "draft_content.json").exists()


def dong_goi(out_zip: Path, tai_nguyen: Path, log=print) -> Path:
    """Đóng gói khuôn từ máy này (cần CapCut tắt để file không đang ghi dở)."""
    src = CAPCUT_DRAFTS / TEN
    goc = _fwd(src)
    from .capcut_draft import _Draft, _tracks
    d = json.loads((src / "draft_content.json").read_text(encoding="utf-8"))
    dr = _Draft(d)
    tr = _tracks(d)
    # Chỉ các lớp tool GIỮ lại (lớp video chính, giọng, nhạc luôn bị thay -> không cần file mẫu, rất nặng)
    giu = [tr["theme"], tr["presenter"], tr["sticker"]] + tr["adjust"] + tr["texts"]
    can, sub = set(), set()

    def gom(mat):
        if not mat:
            return
        p = (mat.get("path") or "").replace("\\", "/")
        if p.startswith("##_draftpath_placeholder"):
            can.add(p.split("##/", 1)[1])
        elif p.lower().startswith(goc.lower() + "/"):
            can.add(p[len(goc) + 1:])
        f = (mat.get("draft_file_path") or "").replace("\\", "/")
        m = re.search(r"subdraft/([^/]+)/", f)
        if m and m.group(1) not in sub:  # clip ghép (vd người dẫn) -> lấy media bên trong clip ghép
            sub.add(m.group(1))
            sd = src / "subdraft" / m.group(1) / "draft_content.json"
            if sd.exists():
                t = sd.read_text(encoding="utf-8")
                can.update(_duong_dan(t, goc))
                dd = json.loads(t)
                for lst in dd.get("materials", {}).values():
                    if isinstance(lst, list):
                        for x in lst:
                            if isinstance(x, dict) and x.get("draft_file_path"):
                                gom(x)

    for t in [x for x in giu if x]:
        for s in t["segments"]:
            for mid in [s["material_id"]] + list(s.get("extra_material_refs", [])):
                gom(dr.find(mid)[1])
    root = json.loads((CAPCUT_DRAFTS / "root_meta_info.json").read_text(encoding="utf-8"))
    entry = next(e for e in root["all_draft_store"] if e.get("draft_name") == TEN)
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    tong = 0
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as z:
        for f in Path(_LP + str(src)).rglob("*"):
            if not f.is_file():
                continue
            rel = os.path.relpath(f, _LP + str(src)).replace("\\", "/")
            if rel.startswith("materials/") and rel not in can:
                continue
            if rel.startswith("subdraft/") and rel.split("/")[1] not in sub:
                continue
            if rel.endswith(".locked"):
                continue
            z.write(f, "khuon/" + rel)
            tong += f.stat().st_size
        for f in sorted(tai_nguyen.glob("*")):
            if f.is_file() and "meme" not in f.stem.lower():
                z.write(f, "tai_nguyen/" + f.name)
                tong += f.stat().st_size
        z.writestr("goi.json", json.dumps({"ten": TEN, "goc": goc, "entry": entry, "root_mau": {
            k: v for k, v in root.items() if k != "all_draft_store"}, "luc": time.strftime("%d/%m/%Y %H:%M")},
            ensure_ascii=False))
    log(f"Đã đóng gói {out_zip} ({tong / 1e6:.0f} MB trước nén, {out_zip.stat().st_size / 1e6:.0f} MB sau nén)")
    return out_zip


def _tai(dst: Path, log=print):
    import requests
    with requests.get(URL, stream=True, timeout=60) as r:
        r.raise_for_status()
        n = int(r.headers.get("content-length") or 0)
        done, last = 0, 0
        with open(dst, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                done += len(chunk)
                if n and done - last > n / 10:
                    last = done
                    log(f"   tải {done * 100 // n}%")


def cai_dat(tai_nguyen: Path, zip_path: Path = None, log=print, ten: str = "") -> str:
    """Cài khuôn vào CapCut (nếu chưa có) + chép nhạc vào TÀI NGUYÊN (file chưa có). Trả về thông báo."""
    if capcut_dang_mo():
        raise CapCutError("CapCut đang mở. Bác tắt CapCut rồi bấm lại.")
    tmp = Path(tempfile.mkdtemp(prefix="sonix_khuon_"))
    try:
        if zip_path is None:
            zip_path = tmp / TEN_ZIP
            log("Tải khuôn Reup Aff từ GitHub...")
            _tai(zip_path, log)
        log("Giải nén...")
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(_LP + str(tmp / "x"))
        x = tmp / "x"
        goi = json.loads((x / "goi.json").read_text(encoding="utf-8"))
        if ten:  # cài dưới tên khác (để thử)
            goi["ten"] = ten
        msg = []
        # nhạc / ảnh tài nguyên
        tai_nguyen.mkdir(parents=True, exist_ok=True)
        for f in (x / "tai_nguyen").glob("*") if (x / "tai_nguyen").exists() else []:
            if not (tai_nguyen / f.name).exists():
                shutil.copy2(f, tai_nguyen / f.name)
                msg.append(f"chép {f.name}")
        # khuôn CapCut
        dst = CAPCUT_DRAFTS / goi["ten"]
        if (dst / "draft_content.json").exists():
            msg.append(f"khuôn '{goi['ten']}' đã có sẵn trong CapCut, giữ nguyên")
            return ", ".join(msg)
        CAPCUT_DRAFTS.mkdir(parents=True, exist_ok=True)
        shutil.copytree(_LP + str(x / "khuon"), _LP + str(dst))
        moi = _fwd(dst)
        for f in Path(_LP + str(dst)).rglob("*"):
            if f.is_file() and (f.suffix.lower() == ".json" or f.name == "draft_settings"):
                t = f.read_text(encoding="utf-8", errors="ignore")
                t2 = t.replace(goi["goc"], moi).replace(goi["goc"].replace("/", "\\\\"), moi.replace("/", "\\\\"))
                if t2 != t:
                    f.write_text(t2, encoding="utf-8")
        now = int(time.time() * 1_000_000)
        new_id = str(uuid.uuid4()).upper()
        mp = dst / "draft_meta_info.json"
        meta = json.loads(mp.read_text(encoding="utf-8"))
        meta.update({"draft_id": new_id, "draft_name": goi["ten"], "draft_fold_path": moi,
                     "draft_root_path": _fwd(CAPCUT_DRAFTS), "tm_draft_create": now, "tm_draft_modified": now,
                     "tm_draft_cloud_entry_id": -1, "tm_draft_cloud_space_id": -1, "cloud_draft_sync": False})
        mp.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        rp = CAPCUT_DRAFTS / "root_meta_info.json"
        if rp.exists():
            shutil.copy2(rp, CAPCUT_DRAFTS / "root_meta_info.json.sonix_backup")
            root = json.loads(rp.read_text(encoding="utf-8"))
        else:
            root = copy.deepcopy(goi.get("root_mau") or {})
            root["root_path"] = _fwd(CAPCUT_DRAFTS)
        root.setdefault("all_draft_store", [])
        e = copy.deepcopy(goi["entry"])
        e.update({"draft_id": new_id, "draft_name": goi["ten"], "draft_fold_path": moi,
                  "draft_root_path": _fwd(CAPCUT_DRAFTS), "draft_json_file": moi + "\\draft_content.json",
                  "draft_cover": moi + "\\draft_cover.jpg", "tm_draft_create": now, "tm_draft_modified": now,
                  "tm_draft_cloud_entry_id": -1, "tm_draft_cloud_space_id": -1, "cloud_draft_sync": False})
        root["all_draft_store"].insert(0, e)
        t = rp.with_suffix(".json.sonix_tmp")
        t.write_text(json.dumps(root, ensure_ascii=False), encoding="utf-8")
        os.replace(t, rp)
        msg.append(f"đã cài khuôn '{goi['ten']}' vào CapCut")
        return ", ".join(msg)
    finally:
        shutil.rmtree(_LP + str(tmp), ignore_errors=True)
