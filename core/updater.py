"""Tự cập nhật Sonix Auto từ GitHub.

Trên GitHub có file manifest.json: phiên bản + mã SHA-256 của từng file chương trình.
Tool so với file trên máy, chỉ tải file khác, kiểm tra mã từng file, chờ lúc không có video đang đăng,
sao lưu file cũ rồi mới thay. Lỗi thì quay lại bản trước được.
Thư mục data (đăng nhập TikTok, khoá AI, hàng chờ, thống kê), .venv, static KHÔNG BAO GIỜ bị đụng tới.

Chạy riêng: python -m core.updater --khoi-dong-lai <pid giao diện> [--pip]
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from .config import BASE_DIR, DATA_DIR, HEARTBEAT_FILE

# Kho đổi tên từ SonixDangVideo (13/11/2026); máy bản cũ vẫn tìm thấy nhờ GitHub tự chuyển link tên cũ.
DEFAULT_REPO = "soncutevocung1/SonixAuto"
CHANNELS = {"main": "Ổn định", "thu-nghiem": "Thử nghiệm"}
VERSION_FILE = BASE_DIR / "VERSION"
ROOT = DATA_DIR / "capnhat"
STAGE = ROOT / "tai_ve"
BACKUP = ROOT / "sao_luu"
CURRENT = ROOT / "manifest_dang_dung.json"
JOURNAL = ROOT / "nhat_ky.json"
SKIP_DIRS = {"data", ".venv", "python", "static", "patches", "__pycache__", ".git", ".github", "installer", "build", "dist"}
SKIP_FILES = {"manifest.json", "unins000.exe", "unins000.dat"}  # unins000: do bộ cài tạo trên từng máy


class UpdateError(Exception):
    pass


def local_version() -> str:
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip() or "0.0.0"
    except Exception:
        return "0.0.0"


def vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v))[:3]) or (0,)


def digest(data: bytes) -> str:
    """Mã SHA-256 (bỏ khác biệt xuống dòng Windows/Linux để file giống nhau không bị coi là khác)."""
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def _safe(rel: str) -> Path:
    p = (BASE_DIR / rel).resolve()
    if BASE_DIR.resolve() not in p.parents or set(Path(rel).parts) & SKIP_DIRS:
        raise UpdateError(f"Đường dẫn không hợp lệ trong bản cập nhật: {rel}")
    return p


# ------------------------------- tải từ GitHub -------------------------------
def _get(url: str, token: str, timeout=60) -> bytes:
    h = {"Accept": "application/vnd.github.raw", "User-Agent": "SonixAuto-capnhat",
         "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise UpdateError("Mã đọc GitHub sai hoặc đã hết hạn. Tạo mã mới rồi dán lại ở mục Cập nhật.")
        if e.code == 404:
            raise UpdateError("Không thấy kho cập nhật, hoặc mã đọc không có quyền đọc kho này.")
        if e.code == 403:
            raise UpdateError("GitHub tạm chặn (hỏi quá nhiều lần hoặc mã thiếu quyền). Thử lại sau ít phút.")
        raise UpdateError(f"GitHub báo lỗi {e.code}")
    except urllib.error.URLError as e:
        raise UpdateError(f"Không kết nối được GitHub (mạng?): {e.reason}")


def fetch(rel: str, settings) -> bytes:
    src = settings.get("update_source")  # chỉ dùng khi thử nghiệm: thư mục chứa bản mới
    if src:
        return (Path(src) / rel).read_bytes()
    repo = settings.get("update_repo") or DEFAULT_REPO
    ref = settings.get("update_channel") or "main"
    url = f"https://api.github.com/repos/{repo}/contents/{urllib.parse.quote(rel)}?ref={urllib.parse.quote(ref)}"
    return _get(url, (settings.get("github_token") or "").strip())


# ------------------------------- kiểm tra / tải / thay -------------------------------
def check(settings) -> dict:
    """Hỏi GitHub bản mới nhất. Trả về {current, latest, notes, newer, changed:[...], removed:[...], manifest}."""
    try:
        man = json.loads(fetch("manifest.json", settings).decode("utf-8"))
    except UpdateError:
        raise
    except Exception as e:
        raise UpdateError(f"Không đọc được thông tin bản cập nhật: {e}")
    changed = []
    for f in man.get("files", []):
        p = _safe(f["path"])
        if not p.exists() or digest(p.read_bytes()) != f["sha256"]:
            changed.append(f)
    removed = []
    try:
        old = json.loads(CURRENT.read_text(encoding="utf-8"))
        new_paths = {f["path"] for f in man.get("files", [])}
        removed = [f["path"] for f in old.get("files", []) if f["path"] not in new_paths and (BASE_DIR / f["path"]).exists()]
    except Exception:
        pass
    cur = local_version()
    return {"current": cur, "latest": man.get("version", "?"), "notes": man.get("notes", ""),
            "newer": vtuple(man.get("version", "0")) > vtuple(cur), "changed": changed, "removed": removed,
            "deps": any(f["path"] == "requirements.txt" for f in changed), "manifest": man}


def download(info, settings, progress=lambda i, n, name: None) -> Path:
    """Tải các file khác vào thư mục tạm, kiểm tra mã từng file. Sai 1 file là dừng, không thay gì."""
    stage = STAGE / info["latest"]
    shutil.rmtree(stage, ignore_errors=True)
    n = len(info["changed"])
    for i, f in enumerate(info["changed"], 1):
        progress(i, n, f["path"])
        _safe(f["path"])
        data = fetch(f["path"], settings)
        if digest(data) != f["sha256"]:
            raise UpdateError(f"File {f['path']} tải về bị sai mã kiểm tra, đã dừng (chưa thay gì).")
        dst = stage / f["path"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
    return stage


def _journal(entry):
    try:
        j = json.loads(JOURNAL.read_text(encoding="utf-8")) if JOURNAL.exists() else []
    except Exception:
        j = []
    j.append({"luc": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), **entry})
    ROOT.mkdir(parents=True, exist_ok=True)
    JOURNAL.write_text(json.dumps(j[-50:], ensure_ascii=False, indent=1), encoding="utf-8")


def apply(info, stage: Path) -> Path:
    """Sao lưu file cũ rồi thay bằng file mới. Trả về thư mục sao lưu (để quay lại)."""
    bdir = BACKUP / f"{info['current']}_{datetime.now():%Y%m%d_%H%M%S}"
    (bdir / "files").mkdir(parents=True, exist_ok=True)
    added = []
    for rel in [f["path"] for f in info["changed"]] + info["removed"]:
        p = _safe(rel)
        if p.exists():
            dst = bdir / "files" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
        else:
            added.append(rel)
    (bdir / "danh_sach.json").write_text(json.dumps({"tu": info["current"], "len": info["latest"], "them_moi": added},
                                                     ensure_ascii=False), encoding="utf-8")
    for f in info["changed"]:
        src, p = stage / f["path"], _safe(f["path"])
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".moi")
        shutil.copy2(src, tmp)
        os.replace(tmp, p)
    for rel in info["removed"]:
        _safe(rel).unlink(missing_ok=True)
    VERSION_FILE.write_text(info["latest"] + "\n", encoding="utf-8")
    CURRENT.write_text(json.dumps(info["manifest"], ensure_ascii=False), encoding="utf-8")
    shutil.rmtree(stage, ignore_errors=True)
    _journal({"viec": "cap_nhat", "tu": info["current"], "len": info["latest"], "so_file": len(info["changed"])})
    # chỉ giữ 3 bản sao lưu gần nhất
    for old in sorted(BACKUP.glob("*"), key=lambda x: x.stat().st_mtime)[:-3]:
        shutil.rmtree(old, ignore_errors=True)
    return bdir


def last_backup():
    b = sorted(BACKUP.glob("*/danh_sach.json"), key=lambda x: x.stat().st_mtime) if BACKUP.exists() else []
    return b[-1].parent if b else None


def rollback() -> str:
    """Quay lại bản trước lần cập nhật gần nhất."""
    bdir = last_backup()
    if not bdir:
        raise UpdateError("Chưa có bản sao lưu nào để quay lại.")
    info = json.loads((bdir / "danh_sach.json").read_text(encoding="utf-8"))
    for src in (bdir / "files").rglob("*"):
        if src.is_file():
            dst = BASE_DIR / src.relative_to(bdir / "files")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    for rel in info.get("them_moi", []):
        (BASE_DIR / rel).unlink(missing_ok=True)
    VERSION_FILE.write_text(info["tu"] + "\n", encoding="utf-8")
    CURRENT.unlink(missing_ok=True)
    shutil.rmtree(bdir, ignore_errors=True)
    _journal({"viec": "quay_lai", "tu": info["len"], "len": info["tu"]})
    return info["tu"]


# ------------------------------- khởi động lại -------------------------------
# CREATE_NO_WINDOW + nhóm tiến trình mới. KHÔNG dùng DETACHED_PROCESS: với python.exe của .venv (là chương trình
# trung gian gọi Python thật), tách hẳn console làm Python thật tự mở 1 cửa sổ đen mới.
_FLAGS = (0x08000000 | 0x00000200) if sys.platform == "win32" else 0


def _py():
    exe = Path(sys.executable)
    return str(exe.with_name("python.exe")) if sys.platform == "win32" and exe.name.lower() == "pythonw.exe" else str(exe)


def _pyw():
    """Python không cửa sổ (pythonw) cho tiến trình chạy ngầm; không có thì dùng python thường."""
    w = Path(_py()).with_name("pythonw.exe")
    return str(w) if sys.platform == "win32" and w.exists() else _py()


def restart_later(ui_pid: int, pip=False):
    """Nhờ 1 tiến trình riêng: chờ bộ đăng xong video đang đăng, tắt, (cài thư viện mới), bật lại tất cả."""
    args = [_pyw(), "-m", "core.updater", "--khoi-dong-lai", str(ui_pid)] + (["--pip"] if pip else [])
    subprocess.Popen(args, cwd=str(BASE_DIR), creationflags=_FLAGS, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True,
                     env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8"))


def _helper(ui_pid: int, pip: bool):
    log = ROOT / "khoi_dong_lai.log"
    ROOT.mkdir(parents=True, exist_ok=True)

    def say(m):
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%d/%m %H:%M:%S}  {m}\n")

    say("Bắt đầu khởi động lại sau cập nhật")
    (DATA_DIR / "stop_runner.flag").write_text("cap nhat", encoding="utf-8")
    end = time.time() + 30 * 60  # bộ đăng tự tắt khi xong video đang đăng
    while time.time() < end:
        try:
            alive = time.time() - float(HEARTBEAT_FILE.read_text()) < 60
        except Exception:
            alive = False
        if not alive:
            break
        time.sleep(3)
    say("Bộ đăng đã dừng")
    HEARTBEAT_FILE.unlink(missing_ok=True)  # để lúc bật lại không tưởng bộ đăng cũ còn sống (tool coi <90 giây là sống)
    if pip:
        r = subprocess.run([_py(), "-m", "pip", "install", "-q", "-r", str(BASE_DIR / "requirements.txt")],
                           capture_output=True, text=True, creationflags=0x08000000 if sys.platform == "win32" else 0)
        say(f"Cài thư viện: mã {r.returncode} {r.stderr[-300:]}")
    if sys.platform == "win32":
        # Không dùng /T: tiến trình này là con của giao diện, /T sẽ tắt luôn chính nó.
        subprocess.run(["taskkill", "/PID", str(ui_pid), "/F"], capture_output=True, creationflags=0x08000000)
    else:
        try:
            os.kill(ui_pid, 15)
        except Exception:
            pass
    say("Đã tắt giao diện cũ")
    time.sleep(3)
    (DATA_DIR / "stop_runner.flag").unlink(missing_ok=True)
    if sys.platform == "win32" and BASE_DIR.name.lower() == OLD_DIR_NAME.lower():
        try:
            doi_ten_thu_muc(say)
            return  # script đổi tên tự bật lại tool từ thư mục mới
        except Exception as e:
            say(f"Không đổi được tên thư mục ({e}), bật lại ở thư mục cũ")
    pyw = BASE_DIR / "SonixDangVideo.pyw"
    subprocess.Popen([_pyw(), str(pyw), "--nen"], cwd=str(BASE_DIR), creationflags=_FLAGS, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8"))
    say("Đã bật lại bộ đăng + giao diện")


# ------------------------------- đổi tên thư mục (bản 2.5: SonixDangVideo -> Sonix Auto) -------------------------------
OLD_DIR_NAME = "SonixDangVideo"
NEW_DIR_NAME = "Sonix Auto"
INNO_KEY = r"HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{6B1F3C2A-5D7E-4A8B-9C0D-50A1DA06E0F1}_is1"

_DOI_TEN_PS = r"""
$ErrorActionPreference = 'SilentlyContinue'
$old = '__OLD__'; $new = '__NEW__'; $log = '__LOG__'
function Say($m) { Add-Content -LiteralPath $log -Value ((Get-Date -Format 'dd/MM HH:mm:ss') + '  ' + $m) -Encoding UTF8 }
Start-Sleep 4
$ok = $false
for ($i = 0; $i -lt 40 -and -not $ok; $i++) {
  Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and ($_.ExecutablePath -like "$old\*" -or $_.CommandLine -like "*$old\*") } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
  Start-Sleep 2
  try { Rename-Item -LiteralPath $old -NewName (Split-Path $new -Leaf) -ErrorAction Stop; $ok = $true } catch { Say ('Chua doi ten duoc: ' + $_.Exception.Message) }
}
if ($ok) {
  Say 'Da doi ten thu muc'
  $k = '__KEY__'
  if (Test-Path $k) {
    $p = Get-ItemProperty $k
    foreach ($n in 'InstallLocation','Inno Setup: App Path','UninstallString','QuietUninstallString','DisplayIcon','ModifyPath') {
      $v = $p.$n; if ($v) { Set-ItemProperty $k -Name $n -Value ($v.Replace($old, $new)) }
    }
    Set-ItemProperty $k -Name 'DisplayName' -Value ('Sonix Auto ' + $p.DisplayVersion)
  }
  $dir = $new
} else { Say 'Khong doi ten duoc, bat lai o thu muc cu'; $dir = $old }
$py = Join-Path $dir 'python\pythonw.exe'
if (-not (Test-Path $py)) { $py = Join-Path $dir '.venv\Scripts\pythonw.exe' }
$env:PYTHONUTF8 = '1'; $env:PYTHONIOENCODING = 'utf-8'
Start-Process -FilePath $py -ArgumentList '-m','core.updater','--sau-doi-ten',('"' + $old + '"') -WorkingDirectory $dir -WindowStyle Hidden -Wait
Start-Process -FilePath $py -ArgumentList ('"' + (Join-Path $dir 'SonixDangVideo.pyw') + '"'),'--nen' -WorkingDirectory $dir -WindowStyle Hidden
Say 'Da bat lai tool'
"""


def doi_ten_thu_muc(say=print):
    """Nhờ PowerShell (nằm ngoài thư mục tool) chờ tool tắt hẳn rồi đổi tên thư mục và bật lại."""
    import tempfile
    new = BASE_DIR.parent / NEW_DIR_NAME
    if new.exists():
        raise UpdateError(f"Đã có thư mục {new}")
    log = Path(tempfile.gettempdir()) / "sonix_doi_ten.log"
    ps = (_DOI_TEN_PS.replace("__OLD__", str(BASE_DIR).replace("'", "''"))
          .replace("__NEW__", str(new).replace("'", "''")).replace("__LOG__", str(log)).replace("__KEY__", INNO_KEY))
    f = Path(tempfile.gettempdir()) / "sonix_doi_ten.ps1"
    f.write_text(ps, encoding="utf-8-sig")
    subprocess.Popen(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", str(f)],
                     creationflags=_FLAGS, close_fds=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, cwd=str(BASE_DIR.parent))
    say(f"Đổi tên thư mục -> {new} (nhật ký: {log})")


def sua_duong_dan_cu(old: str = "", log=print) -> int:
    """Đổi đường dẫn thư mục cũ (vd D:\\SonixDangVideo) sang thư mục đang dùng trong hàng chờ (sonix.db) và mọi file
    dữ liệu .json (âm thanh Yêu thích, Trưng bày, cài đặt, kịch bản). Trả về số chỗ đã sửa. Chạy lại nhiều lần không sao."""
    import sqlite3
    old = old or str(BASE_DIR.parent / OLD_DIR_NAME)
    if Path(old).resolve() == BASE_DIR.resolve() or Path(old).exists():
        return 0  # vẫn đang ở thư mục cũ / thư mục cũ còn đó -> không đụng
    pairs = [(old, str(BASE_DIR)), (old.replace("\\", "/"), str(BASE_DIR).replace("\\", "/")),
             (old.replace("\\", "\\\\"), str(BASE_DIR).replace("\\", "\\\\"))]

    def fix(t):
        for o, n in pairs:
            t = t.replace(o, n)
        return t
    n = 0
    db_file = DATA_DIR / "sonix.db"
    if db_file.exists():
        con = sqlite3.connect(db_file)
        try:
            cols = [r[1] for r in con.execute("PRAGMA table_info(jobs)") if r[2].upper().startswith("TEXT")]
            for (rid, *vals) in con.execute(f"SELECT id, {', '.join(cols)} FROM jobs").fetchall():
                upd = {c: fix(v) for c, v in zip(cols, vals) if isinstance(v, str) and old.split(":")[-1][1:] in v
                       and fix(v) != v}
                if upd:
                    con.execute(f"UPDATE jobs SET {', '.join(c + '=?' for c in upd)} WHERE id=?", [*upd.values(), rid])
                    n += len(upd)
            con.commit()
        finally:
            con.close()
    files = list(DATA_DIR.glob("*.json"))  # KHÔNG quét hồ sơ trình duyệt (data/profiles) của các kênh
    for sub in ("sounds", "showcase", "edit", "capnhat", "ref"):
        files += list((DATA_DIR / sub).rglob("*.json"))
    for f in files:
        try:
            t = f.read_text(encoding="utf-8")
            t2 = fix(t)
            if t2 != t:
                f.write_text(t2, encoding="utf-8")
                n += 1
        except Exception:
            pass
    if n:
        log(f"Đã sửa {n} chỗ còn ghi thư mục cũ {old} -> {BASE_DIR}")
    return n


def sau_doi_ten(old: str):
    """Chạy ở thư mục mới: làm lại biểu tượng, sửa đường dẫn cũ trong dữ liệu."""
    from . import desktop
    try:
        desktop.create_shortcuts()
        if desktop.is_autostart():
            desktop.set_autostart(True)
    except Exception:
        pass
    try:
        sua_duong_dan_cu(old)  # hàng chờ + dữ liệu .json (ảnh bìa, khung hình, âm thanh...)
    except Exception:
        pass
    olds = {old, old.replace("\\", "/")}
    news = {old: str(BASE_DIR), old.replace("\\", "/"): str(BASE_DIR).replace("\\", "/")}
    files = list((DATA_DIR / "edit" / "kich_ban").glob("*.json")) + [DATA_DIR / "settings.json"]
    try:
        from . import capcut_draft
        for d in ([] if capcut_draft.capcut_dang_mo() else capcut_draft.CAPCUT_DRAFTS.glob("*")):
            files += [d / "draft_content.json"] + list(d.glob("Timelines/*/draft_content.json"))
    except Exception:
        pass
    for f in files:
        try:
            t = f.read_text(encoding="utf-8")
            t2 = t
            for o in olds:
                t2 = t2.replace(o, news[o]).replace(o.replace("\\", "\\\\"), news[o].replace("\\", "\\\\"))
            if t2 != t:
                f.write_text(t2, encoding="utf-8")
        except Exception:
            pass


if __name__ == "__main__":
    if "--sau-doi-ten" in sys.argv:
        sau_doi_ten(sys.argv[sys.argv.index("--sau-doi-ten") + 1])
        sys.exit(0)
    if "--khoi-dong-lai" in sys.argv:
        _helper(int(sys.argv[sys.argv.index("--khoi-dong-lai") + 1]), "--pip" in sys.argv)
