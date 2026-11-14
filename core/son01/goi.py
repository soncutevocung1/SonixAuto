"""Gói phong cách Sơn 01: đóng gói trên máy anh Sơn (có dự án khuôn trong CapCut), tự cài trên máy khác.

Gói (zip) gồm:
  khuon/    dự án khuôn đã lược: chỉ 1 timeline (vd "Đạm shop Bọ"), clip ghép (khung viền sáng), file Resources
            mà khuôn thật sự dùng. Đường dẫn bộ nhớ đệm CapCut -> ##SONIX_CC##, file ngoài -> ##SONIX_GOI##/ext/...
  cache/    hiệu ứng / font / nhạc + tiếng hiệu ứng (SFX) lấy từ bộ nhớ đệm CapCut (effect/<id>, music/<file>)
  fonts/    font để bản xem trước giống CapCut (UTM Avo, DTPhudu, Montserrat...)
  goi.json  tên, timeline, lúc đóng gói, mục đăng ký dự án mẫu cho CapCut
Gói đưa lên GitHub Releases (tag goi-son01); app tải về khi máy chưa có.

Đóng gói (chạy độc lập được, không cần app bản mới):
  python goi.py dong_goi "E:\\Capcut\\CapCut Drafts\\DAMBOTC01_SONIX" "Đạm shop Bọ" goi_son01.zip [--fonts D:\\...\\05_font]
"""
import json
import os
import re
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path

TAG = "goi-son01"
TEN_ZIP = "goi_son01.zip"
REPO = "soncutevocung1/SonixAuto"
URL = f"https://github.com/{REPO}/releases/download/{TAG}/{TEN_ZIP}"
CC = "##SONIX_CC##"     # thư mục Cache của CapCut trên máy cài
KH = "##SONIX_GOI##"    # thư mục khuon/ của gói trên máy cài
_CACHE_RE = re.compile(r"[A-Za-z]:/(?:[^\"]*?)/CapCut/User Data/Cache/", re.I)
_LP = "\\\\?\\" if sys.platform == "win32" else ""
_VIDEO = (".mp4", ".mov", ".mkv", ".avi", ".m4v", ".webm")


def _fwd(p) -> str:
    return str(p).replace("\\", "/")


def capcut_cache() -> Path:
    return Path(os.path.expandvars(r"%LOCALAPPDATA%\CapCut\User Data\Cache"))


def drafts_dir() -> Path:
    """Thư mục lưu dự án CapCut: 'currentCustomDraftPath' trong cài đặt CapCut, không có thì mặc định."""
    local = Path(os.path.expandvars(r"%LOCALAPPDATA%\CapCut\User Data"))
    try:
        for line in (local / "Config" / "globalSetting").read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("currentCustomDraftPath="):
                p = line.split("=", 1)[1].strip().replace("\\\\", "\\")
                if p and Path(p).exists():
                    return Path(p)
    except OSError:
        pass
    return local / "Projects" / "com.lveditor.draft"


def thu_muc_goi() -> Path:
    try:
        from core.config import DATA_DIR
    except Exception:
        DATA_DIR = Path(__file__).resolve().parents[2] / "data"
    return DATA_DIR / "son01" / "goi"


def thong_tin() -> dict:
    """{} nếu chưa cài; ngược lại nội dung goi.json (+ 'thu_muc')."""
    d = thu_muc_goi()
    if not (d / "khuon" / "draft_content.json").exists():
        return {}
    try:
        g = json.loads((d / "goi.json").read_text(encoding="utf-8"))
    except Exception:
        g = {}
    g["thu_muc"] = str(d)
    return g


# ------------------------------------------------------------------ đóng gói
def dong_goi(src, timeline, out_zip, fonts_dir=None, log=print) -> Path:
    src, out_zip = Path(src), Path(out_zip)
    lay = src / "timeline_layout.json"
    tid = None
    if lay.exists():
        L = json.loads(lay.read_text(encoding="utf-8"))
        dock = L["dockItems"][0]
        pairs = list(zip(dock["timelineIds"], dock["timelineNames"]))
        import unicodedata
        nfc = lambda s: unicodedata.normalize("NFC", s or "")  # noqa: E731
        tid, tname = next(((a, b) for a, b in pairs if nfc(b) == nfc(timeline)), pairs[0])
        log(f"Timeline khuôn: {tname}")
    cpath = src / "Timelines" / tid / "draft_content.json" if tid else src / "draft_content.json"
    content = cpath.read_text(encoding="utf-8")

    # clip ghép (subdraft) + file Resources được nhắc tới (kể cả bên trong clip ghép)
    texts = [content]
    subs = set()
    sd_root = src / "subdraft"
    if sd_root.is_dir():
        changed = True
        while changed:
            changed = False
            for sd in sd_root.iterdir():
                if sd.name not in subs and any(sd.name in t for t in texts):
                    subs.add(sd.name)
                    f = sd / "draft_content.json"
                    if f.exists():
                        texts.append(f.read_text(encoding="utf-8"))
                    changed = True
    alltext = "\n".join(texts)
    res = set()
    for f in (src / "Resources").rglob("*") if (src / "Resources").is_dir() else []:
        if f.is_file() and (f.name in alltext or f.name.replace(".alpha.mp4", "") in alltext
                            or f.name == "defaultPlaceholder.png"):
            res.add(_fwd(f.relative_to(src)))

    # đường dẫn tuyệt đối: bộ nhớ đệm CapCut + file ngoài (ảnh nền trắng...); video nguồn bỏ (tool thay khi dựng)
    cache_files, ext_map = {}, {}
    goc = _fwd(src)
    for m in re.finditer(r'"([A-Za-z]:[/\\][^"]+)"', alltext):
        p = m.group(1).replace("\\\\", "/").replace("\\", "/")
        cm = _CACHE_RE.match(p)
        if p.lower().startswith(goc.lower() + "/") or p in ext_map:
            continue  # file nam trong khuon -> di theo khuon (doi ##SONIX_GOI##)
        if cm:
            rel = p[cm.end():]
            parts = rel.split("/")
            # effect/<id>/... -> lấy cả thư mục id (hiệu ứng gồm nhiều file); music/<file> -> 1 file
            key = "/".join(parts[:2])
            cache_files[key] = Path(p[:cm.end()] + key)
        elif os.path.isfile(p) and not p.lower().endswith(_VIDEO) and os.path.getsize(p) < 30e6:
            ext_map[p] = f"ext/{len(ext_map):02d}_{os.path.basename(p)}"

    def sua(t: str) -> str:
        t = _CACHE_RE.sub(CC + "/", t)
        t = t.replace(goc + "/", KH + "/").replace(goc.replace("/", "\\\\") + "\\\\", KH + "/")
        for a, b in ext_map.items():
            t = t.replace(a, f"{KH}/{b}").replace(a.replace("/", "\\\\"), f"{KH}/{b}")
        return t

    out_zip.parent.mkdir(parents=True, exist_ok=True)
    tong = 0
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as z:
        def ghi(f: Path, arc: str):
            nonlocal tong
            if f.suffix.lower() == ".json" or f.name == "draft_settings":
                z.writestr(arc, sua(f.read_text(encoding="utf-8", errors="ignore")))
            else:
                z.write(_LP + str(f), arc)
            tong += f.stat().st_size

        for f in src.iterdir():
            if f.is_file() and not f.name.endswith((".bak", ".tmp", ".locked")) and f.name not in (
                    "timeline_layout.json", "draft_content.json", "crypto_key_store.dat"):
                ghi(f, "khuon/" + f.name)
        z.writestr("khuon/draft_content.json", sua(content))
        for d in ("common_attachment", "draft_settings"):
            p = src / d
            if p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file():
                        ghi(f, "khuon/" + _fwd(f.relative_to(src)))
        for r in sorted(res):
            ghi(src / r, "khuon/" + r)
        for s in sorted(subs):
            for f in (sd_root / s).rglob("*"):
                if f.is_file() and not f.name.endswith((".bak", ".tmp")):
                    ghi(f, "khuon/" + _fwd(f.relative_to(src)))
        if tid:
            for f in (src / "Timelines" / tid).rglob("*"):
                if f.is_file() and not f.name.endswith((".bak", ".tmp")) and f.name != "draft_content.json":
                    ghi(f, "khuon/" + _fwd(f.relative_to(src)))
            z.writestr(f"khuon/Timelines/{tid}/draft_content.json", sua(content))
            L["dockItems"] = [{"dockIndex": 0, "ratio": 1, "timelineIds": [tid], "timelineNames": ["Sơn 01"]}]
            z.writestr("khuon/timeline_layout.json", json.dumps(L, ensure_ascii=False))
        for a, b in ext_map.items():
            ghi(Path(a), "khuon/" + b)
        so_cache, fonts = 0, set()
        for key, p in sorted(cache_files.items()):
            if p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file():
                        ghi(f, f"cache/{key}/" + _fwd(f.relative_to(p)))
                        so_cache += 1
                        if f.suffix.lower() in (".otf", ".ttf") and f.name not in fonts:
                            fonts.add(f.name)
                            z.write(_LP + str(f), "fonts/" + f.name)
            elif p.is_file():
                ghi(p, f"cache/{key}")
                so_cache += 1
        if fonts_dir and Path(fonts_dir).is_dir():
            for f in Path(fonts_dir).iterdir():
                if f.suffix.lower() in (".otf", ".ttf") and f.name not in fonts:
                    fonts.add(f.name)
                    z.write(_LP + str(f), "fonts/" + f.name)
        entry = {}
        for rp in (src.parent / "root_meta_info.json",
                   Path(os.path.expandvars(r"%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft"))
                   / "root_meta_info.json"):
            try:
                r = json.loads(rp.read_text(encoding="utf-8"))
                entry = next(e for e in r["all_draft_store"] if e.get("draft_name") == src.name)
                break
            except Exception:
                continue
        z.writestr("goi.json", json.dumps({"ten": "Sơn 01", "khuon_goc": src.name, "timeline": timeline,
                                           "luc": time.strftime("%d/%m/%Y %H:%M"), "entry": entry},
                                          ensure_ascii=False, indent=1))
    log(f"Đã đóng gói {out_zip}: {len(subs)} clip ghép, {len(res)} file Resources, {len(cache_files)} mục bộ nhớ "
        f"đệm ({so_cache} file), {len(ext_map)} file ngoài · {tong / 1e6:.1f} MB trước nén, "
        f"{out_zip.stat().st_size / 1e6:.1f} MB sau nén")
    return out_zip


# ------------------------------------------------------------------ cài
def _tai(dst: Path, log=print):
    import requests
    with requests.get(URL, stream=True, timeout=60) as r:
        if r.status_code == 404:
            raise RuntimeError("Trên GitHub chưa có gói Sơn 01 (Releases > goi-son01). Nhờ anh Sơn đóng gói + đưa lên, "
                               "hoặc chọn file gói .zip có sẵn.")
        r.raise_for_status()
        n = int(r.headers.get("content-length") or 0)
        done, last = 0, 0
        with open(dst, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                done += len(chunk)
                if n and done - last > n / 5:
                    last = done
                    log(f"   tải {done * 100 // n}%")


def cai_dat(zip_path=None, log=print) -> str:
    tmp = Path(tempfile.mkdtemp(prefix="sonix_goi_"))
    try:
        if not zip_path:
            zip_path = tmp / TEN_ZIP
            log("Tải gói Sơn 01 từ GitHub...")
            _tai(zip_path, log)
        log("Giải nén...")
        x = tmp / "x"
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(_LP + str(x))
        dst = thu_muc_goi()
        if dst.exists():
            shutil.rmtree(_LP + str(dst), ignore_errors=True)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(_LP + str(x), _LP + str(dst))
        # hiệu ứng / nhạc: chép vào bộ nhớ đệm CapCut (chưa có mới chép) để CapCut mở là thấy ngay
        cc = capcut_cache()
        moi = 0
        if (dst / "cache").is_dir() and sys.platform == "win32":
            for f in (dst / "cache").rglob("*"):
                if f.is_file():
                    t = cc / f.relative_to(dst / "cache")
                    if not t.exists():
                        t.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(f, t)
                        moi += 1
        cc_path = _fwd(cc) if sys.platform == "win32" else _fwd(dst / "cache")
        kh = _fwd(dst / "khuon")
        for f in (dst / "khuon").rglob("*"):
            if f.is_file() and (f.suffix.lower() == ".json" or f.name == "draft_settings"):
                t = f.read_text(encoding="utf-8", errors="ignore")
                t2 = t.replace(CC, cc_path).replace(KH, kh)
                if t2 != t:
                    f.write_text(t2, encoding="utf-8")
        g = thong_tin()
        return (f"Đã cài gói Sơn 01 (đóng gói {g.get('luc', '?')}, timeline '{g.get('timeline', '')}'), "
                f"chép {moi} file hiệu ứng/nhạc vào CapCut")
    finally:
        shutil.rmtree(_LP + str(tmp), ignore_errors=True)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    a = sys.argv[1:]
    if a and a[0] == "dong_goi":
        opt = dict(zip(a[4::2], a[5::2]))
        dong_goi(a[1], a[2], a[3], opt.get("--fonts"))
    elif a and a[0] == "cai":
        print(cai_dat(a[1] if len(a) > 1 else None))
    else:
        print(__doc__)
