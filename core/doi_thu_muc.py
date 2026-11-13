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
    # Máy chưa từng có thư mục nguồn Edit Video: tạo sẵn cạnh thư mục Up Video (cùng ổ)
    if not edit_video.input_root(S).exists():
        goc = Path(S.get("root_folder") or "")
        o = goc.anchor if goc.anchor and Path(goc.anchor).exists() else edit_video.INPUT_ROOT.anchor
        if not Path(o).exists():
            from .channels import default_root
            o = Path(default_root()).anchor
        moi = Path(o) / EDIT_NEW
        try:
            for sub in ("", "TÀI NGUYÊN", "CHƯA LỌC", "MẪU"):
                (moi / sub).mkdir(parents=True, exist_ok=True)
            (moi / "DOC_TRUOC.txt").write_text(
                "Thư mục nguồn của Sonix Edit Video.\n"
                "- CHƯA LỌC: bỏ video lẫn lộn vào đây, rồi vào app > Sonix Edit Video > Tự lọc video theo sản phẩm.\n"
                "  Tool tạo thư mục theo từng sản phẩm (ĐẠM CÁ ..., KÍCH RỄ ...).\n"
                "- TÀI NGUYÊN: nhạc nền kịch tính (.mp4/.mp3), ảnh khung, video người dẫn.\n"
                "- MẪU: mỗi thư mục con là 1 phong cách edit (tự đặt tên, vd 'Reup Aff'), bỏ vài video mẫu vào,\n"
                "  rồi vào app > Sonix Edit Video > Làm theo phong cách mẫu > Học phong cách này.\n"
                "Dự án CapCut mẫu tên 'mẫu' phải có sẵn trong CapCut.\n", encoding="utf-8")
            S["edit_input_root"] = str(moi)
            doi = True
            _log(f"Đã tạo {moi}")
        except OSError as e:
            _log(f"Không tạo được {moi}: {e}")
    # Máy đã có thư mục nguồn (bản trước) nhưng thiếu MẪU / CHƯA LỌC: tạo thêm
    try:
        r = edit_video.input_root(S)
        if r.exists():
            for sub in ("MẪU", "CHƯA LỌC"):
                if not (r / sub).exists():
                    (r / sub).mkdir()
                    _log(f"Đã tạo {r / sub}")
    except OSError:
        pass
    if doi:
        save_settings(S)
    return doi
