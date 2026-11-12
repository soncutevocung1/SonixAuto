"""Tự cập nhật Sonix Đăng Video từ GitHub (kho riêng tư của bác).

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

DEFAULT_REPO = "soncutevocung1/SonixDangVideo"
CHANNELS = {"main": "Ổn định", "thu-nghiem": "Thử nghiệm"}
VERSION_FILE = BASE_DIR / "VERSION"
ROOT = DATA_DIR / "capnhat"
STAGE = ROOT / "tai_ve"
BACKUP = ROOT / "sao_luu"
CURRENT = ROOT / "manifest_dang_dung.json"
JOURNAL = ROOT / "nhat_ky.json"
SKIP_DIRS = {"data", ".venv", "python", "static", "patches", "__pycache__", ".git", ".github", "installer", "build", "dist"}
SKIP_FILES = {"manifest.json"}


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
    h = {"Accept": "application/vnd.github.raw", "User-Agent": "SonixDangVideo-capnhat",
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
    pyw = BASE_DIR / "SonixDangVideo.pyw"
    subprocess.Popen([_pyw(), str(pyw), "--nen"], cwd=str(BASE_DIR), creationflags=_FLAGS, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8"))
    say("Đã bật lại bộ đăng + giao diện")


if __name__ == "__main__":
    if "--khoi-dong-lai" in sys.argv:
        _helper(int(sys.argv[sys.argv.index("--khoi-dong-lai") + 1]), "--pip" in sys.argv)
