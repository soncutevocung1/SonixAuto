"""Sửa đường dẫn cũ còn ghi trong hàng chờ (sonix.db) và file dữ liệu .json sau khi đổi tên thư mục.

Dùng cho: đổi thư mục video VIDEO_TIKTOK -> SONIX_UP_VIDEO (bản 2.5.2), đổi thư mục cài SonixDangVideo -> Sonix Auto.
Không đụng hồ sơ trình duyệt (data/profiles). Chạy lại nhiều lần không sao."""
import re
import sqlite3
from pathlib import Path

from .config import DATA_DIR


def _pairs(old: str, new: str):
    """Các dạng viết của 1 đường dẫn: dấu \\, dấu /, và \\\\ trong JSON."""
    return [(old, new), (old.replace("\\", "/"), new.replace("\\", "/")),
            (old.replace("\\", "\\\\"), new.replace("\\", "\\\\"))]


def _fix(t: str, pairs) -> str:
    for o, n in pairs:
        # chỉ thay khi sau tên thư mục là dấu phân cách hoặc hết chuỗi (tránh VIDEO_TIKTOK2...)
        for sep in ("\\", "/", '"'):
            t = t.replace(o + sep, n + sep)
        if t.endswith(o):
            t = t[: -len(o)] + n
    return t


def thay(old: str, new: str, log=None) -> int:
    """Đổi đường dẫn old -> new trong hàng chờ và file dữ liệu. Trả về số chỗ đã sửa."""
    if not old or not new or old == new:
        return 0
    pairs = _pairs(str(old), str(new))
    key = re.split(r"[\\/]", str(old).rstrip("\\/"))[-1]  # tên thư mục cuối (đúng cả dấu \ lẫn /)
    n = 0
    db_file = DATA_DIR / "sonix.db"
    if db_file.exists():
        con = sqlite3.connect(db_file, timeout=30)
        try:
            cols = [r[1] for r in con.execute("PRAGMA table_info(jobs)") if str(r[2]).upper().startswith("TEXT")]
            for rid, *vals in con.execute(f"SELECT id, {', '.join(cols)} FROM jobs").fetchall():
                upd = {}
                for c, v in zip(cols, vals):
                    if isinstance(v, str) and key in v:
                        v2 = _fix(v, pairs)
                        if v2 != v:
                            upd[c] = v2
                if upd:
                    con.execute(f"UPDATE jobs SET {', '.join(c + '=?' for c in upd)} WHERE id=?", [*upd.values(), rid])
                    n += len(upd)
            con.commit()
        finally:
            con.close()
    files = list(DATA_DIR.glob("*.json"))
    for sub in ("sounds", "showcase", "edit", "ref"):
        files += list((DATA_DIR / sub).rglob("*.json"))
    for f in files:
        try:
            t = f.read_text(encoding="utf-8")
            if key not in t:
                continue
            t2 = _fix(t, pairs)
            if t2 != t:
                f.write_text(t2, encoding="utf-8")
                n += 1
        except Exception:
            pass
    if n and log:
        log(f"Đã sửa {n} chỗ còn ghi {old} -> {new}")
    return n


def sua_thu_muc_video(settings, log=None) -> int:
    """Máy đã đổi VIDEO_TIKTOK -> SONIX_UP_VIDEO (Cài đặt đã trỏ tên mới) nhưng hàng chờ còn ghi tên cũ -> sửa."""
    root = Path(settings.get("root_folder") or "")
    if not root.name or not root.exists():
        return 0
    n = 0
    for old_name in ("VIDEO_TIKTOK",):
        old = root.parent / old_name
        if old != root and not old.exists():
            n += thay(str(old), str(root), log)
    return n
