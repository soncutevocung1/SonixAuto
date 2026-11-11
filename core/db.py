"""Hàng chờ (SQLite): mỗi dòng = 1 video sẽ đăng lên 1 kênh."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from .config import DB_FILE, ensure_dirs

TIME_FMT = "%Y-%m-%d %H:%M"

STATUS_LABELS = {
    "analyzing": "Đang phân tích",
    "draft": "Chờ duyệt",
    "pending": "Chờ đăng",
    "running": "Đang đăng",
    "scheduled": "Đã hẹn giờ trên TikTok",
    "done": "Đã đăng",
    "scheduled_fb": "Đã hẹn giờ trên FB",
    "check": "Cần kiểm tra",
    "error": "Lỗi",
    "paused": "Tạm dừng",
}

COLUMNS = {
    "platform": "TEXT DEFAULT 'tiktok'",     # tiktok | facebook
    "channel": "TEXT NOT NULL",              # tên kênh TikTok / tên trang FB
    "video_path": "TEXT NOT NULL",
    "status": "TEXT DEFAULT 'draft'",
    "caption": "TEXT DEFAULT ''",
    "hashtags": "TEXT DEFAULT ''",
    "item_key": "TEXT DEFAULT ''",           # sản phẩm nhận diện được ('' = không gắn giỏ)
    "products_json": "TEXT DEFAULT '[]'",    # [{"id": "...", "name": "..."}]
    "cart_name": "TEXT DEFAULT ''",          # tên giỏ hàng hiện trên video (<=30 ký tự)
    "confidence": "INTEGER DEFAULT 0",
    "ai_note": "TEXT DEFAULT ''",
    "frames_json": "TEXT DEFAULT '[]'",      # [{"t": giây, "thumb": đường dẫn}]
    "cover_path": "TEXT DEFAULT ''",
    "cover_by_user": "INTEGER DEFAULT 0",    # 1 = bác tự chọn bìa cho video này (không tự dùng bìa mặc định)
    "reviewed": "INTEGER DEFAULT 0",
    "music_mode": "TEXT DEFAULT 'none'",     # none | tiktok | local
    "music_ref": "TEXT DEFAULT ''",          # tên âm thanh TikTok hoặc đường dẫn file nhạc
    "visibility": "TEXT DEFAULT 'public'",   # public | friends | private
    "ai_content": "INTEGER DEFAULT 0",
    "disclosure": "TEXT DEFAULT 'none'",
    "product_link": "TEXT DEFAULT ''",       # dùng cho Facebook
    "scheduled_at": "TEXT DEFAULT ''",
    "result": "TEXT DEFAULT ''",
    "attempts": "INTEGER DEFAULT 0",
    "ai_model": "TEXT DEFAULT ''",
    "keep_audio": "INTEGER DEFAULT 1",
    "music_by_user": "INTEGER DEFAULT 0",    # 1 = bác tự chọn nhạc cho video này (tool không tự đổi nữa)
    "redo_caption": "INTEGER DEFAULT 0",     # 1 = chỉ viết lại caption (giữ sản phẩm, ảnh bìa)       # 1 = giữ âm thanh gốc, 0 = tắt tiếng gốc trước khi đăng           # mức AI chọn lúc bấm Phân tích (luồng ngầm dùng)
    "fb_story": "INTEGER DEFAULT 0",         # Facebook: 1 = đăng kèm vào Tin lúc tới giờ
    "fb_story_state": "TEXT DEFAULT ''",     # '' | done | skip | lỗi...
    "created_at": "TEXT",
    "updated_at": "TEXT",
}


@contextmanager
def conn():
    ensure_dirs()
    c = sqlite3.connect(DB_FILE, timeout=30)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db():
    with conn() as c:
        cols = ", ".join(f"{k} {v}" for k, v in COLUMNS.items())
        c.execute(f"CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols})")
        have = {r[1] for r in c.execute("PRAGMA table_info(jobs)")}
        for k, v in COLUMNS.items():  # nâng cấp bảng cũ
            if k not in have:
                c.execute(f"ALTER TABLE jobs ADD COLUMN {k} {v.replace('NOT NULL', '')}")


def now_str():
    return datetime.now().strftime(TIME_FMT)


def _row(r):
    d = dict(r)
    d["products"] = json.loads(d.get("products_json") or "[]")
    d["frames"] = json.loads(d.get("frames_json") or "[]")
    return d


def add_job(**f) -> int:
    f["created_at"] = f["updated_at"] = now_str()
    for k in ("products", "frames"):
        if k in f:
            f[k + "_json"] = json.dumps(f.pop(k), ensure_ascii=False)
    keys = [k for k in f if k in COLUMNS]
    with conn() as c:
        cur = c.execute(f"INSERT INTO jobs ({','.join(keys)}) VALUES ({','.join('?' * len(keys))})",
                        [f[k] for k in keys])
        return cur.lastrowid


def list_jobs(statuses=None, platform=None, channel=None):
    q, args, where = "SELECT * FROM jobs", [], []
    if statuses:
        where.append(f"status IN ({','.join('?' * len(statuses))})")
        args += list(statuses)
    if platform:
        where.append("platform=?")
        args.append(platform)
    if channel:
        where.append("channel=?")
        args.append(channel)
    if where:
        q += " WHERE " + " AND ".join(where)
    q += " ORDER BY CASE WHEN scheduled_at='' THEN 1 ELSE 0 END, scheduled_at, id"
    with conn() as c:
        return [_row(r) for r in c.execute(q, args)]


def get_job(job_id):
    with conn() as c:
        r = c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return _row(r) if r else None


def update_job(job_id, **f):
    f["updated_at"] = now_str()
    for k in ("products", "frames"):
        if k in f:
            f[k + "_json"] = json.dumps(f.pop(k), ensure_ascii=False)
    keys = [k for k in f if k in COLUMNS]
    with conn() as c:
        c.execute(f"UPDATE jobs SET {', '.join(k + '=?' for k in keys)} WHERE id=?",
                  [f[k] for k in keys] + [job_id])


def delete_jobs(ids):
    if ids:
        with conn() as c:
            c.execute(f"DELETE FROM jobs WHERE id IN ({','.join('?' * len(ids))})", list(ids))


def claim_job(job_id) -> bool:
    with conn() as c:
        cur = c.execute("UPDATE jobs SET status='running', attempts=attempts+1, updated_at=? "
                        "WHERE id=? AND status='pending'", (now_str(), job_id))
        return cur.rowcount == 1


def reset_stuck():
    with conn() as c:
        c.execute("UPDATE jobs SET status='check', result='Tool bị tắt giữa chừng. Bác mở kênh xem video đã lên "
                  "chưa: chưa lên thì bấm Cho chạy lại.' WHERE status='running'")


def active_paths(platform="tiktok") -> set:
    """Video đang nằm trong quy trình (chưa đăng xong) -> không quét lại."""
    with conn() as c:
        return {r[0] for r in c.execute(
            "SELECT video_path FROM jobs WHERE status IN ('analyzing','draft','pending','running','paused') "
            "AND platform=?", (platform,))}


def taken_times(channel) -> set:
    with conn() as c:
        return {r[0] for r in c.execute(
            "SELECT scheduled_at FROM jobs WHERE channel=? AND scheduled_at!='' AND "
            "status IN ('pending','running','scheduled','done','paused')", (channel,))}


def rename_video_path(old, new):
    with conn() as c:
        c.execute("UPDATE jobs SET video_path=? WHERE video_path=?", (new, old))


def other_open_jobs_for_video(video_path, exclude_id) -> int:
    with conn() as c:
        return c.execute("SELECT COUNT(*) FROM jobs WHERE video_path=? AND id!=? AND "
                         "status IN ('draft','pending','running','paused')", (video_path, exclude_id)).fetchone()[0]
