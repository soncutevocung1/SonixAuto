"""Tổng hợp theo ngày: ghi lại mỗi việc tool làm (phân tích, xác nhận, hẹn giờ/đăng, lỗi)
theo ngày, kênh, sản phẩm. Mỗi ngày tự tính lại từ 0; ngày cũ giữ nguyên để xem lại."""
from datetime import date, datetime, timedelta

from . import db

KINDS = {
    "phan_tich": "Đã phân tích",
    "xac_nhan": "Đã xác nhận",
    "hen_gio": "Đã hẹn giờ / đăng",
    "loi": "Lỗi",
}


def init():
    """Tạo bảng (1 lần). Lần đầu: dựng lại lịch sử gần đúng từ hàng chờ có sẵn."""
    with db.conn() as c:
        c.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, day TEXT, "
                  "kind TEXT, channel TEXT, item_key TEXT, job_id INTEGER)")
        c.execute("CREATE INDEX IF NOT EXISTS ev_day ON events(day)")
        c.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
        done = c.execute("SELECT v FROM meta WHERE k='events_backfill'").fetchone()
        if done:
            return
        rows = c.execute("SELECT id, channel, item_key, status, created_at, updated_at FROM jobs "
                         "WHERE platform='tiktok'").fetchall()
        ev = []
        for r in rows:
            made, upd = (r["created_at"] or "")[:16], (r["updated_at"] or "")[:16]
            if made and r["status"] != "analyzing":
                ev.append((made, "phan_tich", r))
            if upd and r["status"] in ("scheduled", "done"):
                ev.append((upd, "hen_gio", r))
            if upd and r["status"] in ("error", "check"):
                ev.append((upd, "loi", r))
        c.executemany("INSERT INTO events(ts, day, kind, channel, item_key, job_id) VALUES (?,?,?,?,?,?)",
                      [(ts, ts[:10], k, r["channel"] or "", r["item_key"] or "", r["id"]) for ts, k, r in ev])
        c.execute("INSERT OR REPLACE INTO meta(k, v) VALUES ('events_backfill', ?)", (db.now_str(),))


def record(kind, job, when=None):
    """Ghi 1 việc vừa làm. Lỗi ghi thống kê không bao giờ làm hỏng việc chính."""
    try:
        t = when or datetime.now()
        job = job or {}
        with db.conn() as c:
            c.execute("INSERT INTO events(ts, day, kind, channel, item_key, job_id) VALUES (?,?,?,?,?,?)",
                      (t.strftime(db.TIME_FMT), t.strftime("%Y-%m-%d"), kind, job.get("channel") or "",
                       job.get("item_key") or "", job.get("id")))
    except Exception:
        pass


def day_detail(day: str) -> dict:
    """{kind: {"total": n, "channels": {kênh: n}, "items": {sản phẩm: n}}} của 1 ngày (YYYY-MM-DD)."""
    out = {k: {"total": 0, "channels": {}, "items": {}} for k in KINDS}
    try:
        with db.conn() as c:
            for r in c.execute("SELECT kind, channel, item_key, COUNT(*) n FROM events WHERE day=? "
                               "GROUP BY kind, channel, item_key", (day,)):
                d = out.setdefault(r["kind"], {"total": 0, "channels": {}, "items": {}})
                d["total"] += r["n"]
                d["channels"][r["channel"]] = d["channels"].get(r["channel"], 0) + r["n"]
                d["items"][r["item_key"]] = d["items"].get(r["item_key"], 0) + r["n"]
    except Exception:
        pass
    return out


def series(kind: str, end: date, days: int = 7) -> list:
    """[(ngày, số)] của `days` ngày tới `end`."""
    start = end - timedelta(days=days - 1)
    got = {}
    try:
        with db.conn() as c:
            for r in c.execute("SELECT day, COUNT(*) n FROM events WHERE kind=? AND day BETWEEN ? AND ? GROUP BY day",
                               (kind, start.isoformat(), end.isoformat())):
                got[r["day"]] = r["n"]
    except Exception:
        pass
    return [((start + timedelta(days=i)).isoformat(), got.get((start + timedelta(days=i)).isoformat(), 0))
            for i in range(days)]


def first_day():
    try:
        with db.conn() as c:
            v = c.execute("SELECT MIN(day) FROM events").fetchone()[0]
        return date.fromisoformat(v) if v else None
    except Exception:
        return None
