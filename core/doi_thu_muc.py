"""Bản 2.5.2: đổi tên thư mục video cho dễ nhận biết (chạy lúc mở app, TRƯỚC khi bộ đăng bật):
  VIDEO_TIKTOK -> SONIX_UP_VIDEO     (thư mục gốc của Sonix Up Video, lấy theo Cài đặt)
  VIDEO_INPUT  -> SONIX_EDIT_VIDEO   (thư mục nguồn của Sonix Edit Video)
Chỉ đổi khi thư mục đang đúng tên cũ và chưa có thư mục tên mới. Đổi không được (đang mở trong
File Explorer, file đang dùng...) thì để nguyên, lần mở app sau thử lại. Sửa luôn đường dẫn cũ trong
Cài đặt, chỉ mục cảnh quay và các dự án CapCut do tool tạo."""
import json
from pathlib import Path

from .config import DATA_DIR, load_settings, save_settings

UP_OLD, UP_NEW = "VIDEO_TIKTOK", "SONIX_UP_VIDEO"
EDIT_OLD, EDIT_NEW = "VIDEO_INPUT", "SONIX_EDIT_VIDEO"
LOG = DATA_DIR / "logs" / "doi_thu_muc.log"


def _log(m):
    try:
        from datetime import datetime
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%d/%m %H:%M:%S}  {m}\n")
    except Exception:
        pass


def _doi(old: Path, new_name: str):
    """Đổi tên, trả về đường dẫn mới hoặc None."""
    new = old.parent / new_name
    if not old.is_dir() or new.exists():
        return None
    try:
        old.rename(new)
        _log(f"Đã đổi {old} -> {new}")
        return new
    except OSError as e:
        _log(f"Chưa đổi được {old}: {e}")
        return None


def _thay_trong_file(f: Path, old: str, new: str):
    """Thay đường dẫn cũ trong file chữ (cả dạng \\, \\\\ của JSON và /)."""
    pairs = {old: new, old.replace("\\", "/"): new.replace("\\", "/"),
             old.replace("\\", "\\\\"): new.replace("\\", "\\\\")}
    try:
        t = f.read_text(encoding="utf-8")
    except Exception:
        return
    t2 = t
    for o, n in pairs.items():
        t2 = t2.replace(o + "\\", n + "\\").replace(o + "/", n + "/").replace(o + '"', n + '"')
    if t2 != t:
        f.write_text(t2, encoding="utf-8")


def _sua_du_lieu_edit(old: str, new: str):
    files = list((DATA_DIR / "edit").rglob("*.json"))
    try:
        from . import capcut_draft
        if not capcut_draft.capcut_dang_mo():
            for d in capcut_draft.CAPCUT_DRAFTS.glob("*"):
                files += [d / "draft_content.json"] + list(d.glob("Timelines/*/draft_content.json"))
    except Exception:
        pass
    for f in files:
        if f.exists():
            _thay_trong_file(f, old, new)


def chay():
    S = load_settings()
    doi = False
    # Sonix Up Video
    root = S.get("root_folder") or ""
    if root and Path(root).name.upper() == UP_OLD:
        new = _doi(Path(root), UP_NEW)
        if new:
            S["root_folder"] = str(new)
            doi = True
    # Sonix Edit Video
    from . import edit_video
    src = Path(S.get("edit_input_root") or edit_video.INPUT_OLD)
    if src.name.upper() == EDIT_OLD:
        new = _doi(src, EDIT_NEW)
        if new:
            S["edit_input_root"] = str(new)
            _sua_du_lieu_edit(str(src), str(new))
            doi = True
    if doi:
        save_settings(S)
    return doi
