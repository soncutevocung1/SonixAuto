"""Hàng chờ Facebook: cài đặt từng trang, thư mục video, xếp giờ đăng, chuyển file sau khi đăng.

Mỗi trang có 1 thư mục gốc (vd D:\\REUP) gồm CHƯA UP / ĐÃ UP / VIDEO LỖI giống TikTok.
Giờ đăng do bác tự đặt (vd 11:30, 19:30) → mỗi ngày đăng đúng số khung giờ đó.
"""
import re
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

from . import db
from .config import FOLDER_DONE, FOLDER_ERR, FOLDER_TODO, VIDEO_EXTS

FMT = db.TIME_FMT
DEFAULT_TARGETS = {"reels": 8, "posts": 10, "stories": 7, "replies": 1}
OPEN = ["analyzing", "draft", "pending", "running"]


def pages(settings) -> list:
    return [p for p in settings.get("facebook_pages", []) if p.get("name")]


def page(settings, name) -> dict:
    return next((p for p in pages(settings) if p["name"] == name), {}) or {}


WEEKDAYS = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]


def parse_times(text) -> list:
    out = []
    for x in re.split(r"[,;\s]+", str(text or "")):
        try:
            out.append(datetime.strptime(x.strip(), "%H:%M").strftime("%H:%M"))
        except ValueError:
            pass
    return sorted(set(out))


def times_of(pg) -> list:
    """Khung giờ chung mỗi ngày."""
    return parse_times(pg.get("times") or "11:30, 19:30") or ["11:30", "19:30"]


def times_for(pg, day) -> list:
    """Khung giờ của 1 ngày: theo từng thứ (nếu bật) hoặc khung chung. Ngày để trống = nghỉ."""
    if pg.get("by_day"):
        return parse_times((pg.get("times_by_day") or {}).get(str(day.weekday()), ""))
    return times_of(pg)


def plan_range(pg):
    """(từ ngày, đến ngày) đã lưu của trang; None = không giới hạn."""
    def d(x):
        try:
            return datetime.strptime(x, "%Y-%m-%d").date()
        except Exception:
            return None
    return d(pg.get("plan_from")), d(pg.get("plan_to"))


def folder(pg, sub=FOLDER_TODO) -> Path:
    if not (pg.get("folder") or "").strip():
        raise ValueError(f"Trang «{pg.get('name')}» chưa chọn thư mục video")
    return Path(pg["folder"].strip()) / sub


def _natural(p: Path):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.stem)]


def _known_paths() -> set:
    """Mọi video Facebook đang có trong hàng chờ (kể cả lỗi) -> không quét lại."""
    with db.conn() as c:
        return {r[0] for r in c.execute("SELECT video_path FROM jobs WHERE platform='facebook'")}


def new_videos(pg, min_age=0) -> list:
    """Video trong CHƯA UP chưa nằm trong hàng chờ, xếp theo số trong tên (1, 2, ..., 10).
    min_age: chỉ lấy file đã chép xong (không đổi trong `min_age` giây) để không đọc file đang chép dở."""
    if not (pg.get("folder") or "").strip():
        return []
    d = folder(pg)
    if not d.is_dir():
        return []
    busy, now = _known_paths(), time.time()
    out = []
    for p in d.iterdir():
        try:
            if (p.is_file() and p.suffix.lower() in VIDEO_EXTS and str(p) not in busy
                    and now - p.stat().st_mtime >= min_age):
                out.append(p)
        except OSError:
            pass
    return sorted(out, key=_natural)


def overview(pg) -> dict:
    """Số video theo từng chặng của trang."""
    out = {"chua_up": 0, "da_up": 0, "loi": 0}
    try:
        for key, sub in (("chua_up", FOLDER_TODO), ("da_up", FOLDER_DONE), ("loi", FOLDER_ERR)):
            d = folder(pg, sub)
            out[key] = sum(1 for p in d.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS) \
                if d.is_dir() else 0
    except Exception:
        pass
    js = db.list_jobs(None, "facebook", pg["name"])
    for st_ in ("analyzing", "draft", "pending", "scheduled_fb", "error"):
        out[st_] = sum(j["status"] == st_ for j in js)
    out["moi"] = len(new_videos(pg))
    out["het_lich"] = max([j["scheduled_at"] for j in js if j.get("scheduled_at")
                           and j["status"] in ("draft", "pending", "scheduled_fb")] or [""])
    return out


def auto_scan(settings) -> int:
    """Chế độ tự động: đưa video mới (đã chép xong) trong CHƯA UP vào phân tích. Trả về số video thêm."""
    n = 0
    for pg in pages(settings):
        if not pg.get("auto") or not pg.get("token") or not (pg.get("folder") or "").strip():
            continue
        for v in new_videos(pg, min_age=60):
            db.add_job(platform="facebook", channel=pg["name"], video_path=str(v), status="analyzing",
                       ai_model=pg.get("auto_model") or settings.get("ai_model") or "",
                       fb_story=1 if pg.get("story") else 0)
            n += 1
    return n


def taken(name, exclude_ids=()) -> set:
    with db.conn() as c:
        rows = c.execute("SELECT id, scheduled_at FROM jobs WHERE platform='facebook' AND channel=? "
                         "AND scheduled_at!='' AND status NOT IN ('error')", (name,)).fetchall()
    return {r[1] for r in rows if r[0] not in set(exclude_ids)}


def next_slots(pg, n, start=None, end_day=None, exclude_ids=()) -> list:
    """n khung giờ trống tiếp theo của trang, trong khoảng [start, end_day]. Thiếu chỗ thì trả về ít hơn n."""
    p_from, p_to = plan_range(pg)
    if pg.get("auto"):  # tự động: lên lịch toàn bộ video, bỏ qua 'Đến ngày'
        p_to = None
    soon = datetime.now() + timedelta(minutes=30)
    if start is None:
        start = max(soon, datetime.combine(p_from, datetime.min.time())) if p_from else soon
    start = max(start, soon)
    end_day = end_day or p_to or start.date() + timedelta(days=400)
    used, out, day = taken(pg["name"], exclude_ids), [], start.date()
    while len(out) < n and day <= end_day:
        for hm in times_for(pg, day):
            t = datetime.combine(day, datetime.strptime(hm, "%H:%M").time())
            s_ = t.strftime(FMT)
            if t >= start and s_ not in used:
                out.append(t)
                used.add(s_)
                if len(out) >= n:
                    break
        day += timedelta(days=1)
    return out


def plan_new(name, ids, settings) -> int:
    """Xếp giờ cho các video Facebook vừa phân tích xong."""
    pg = page(settings, name)
    if not pg:
        return 0
    drafts = db.list_jobs(["draft"], "facebook", name)
    if pg.get("auto"):  # tự động: xếp mọi video chưa có giờ, nối tiếp SAU video có lịch muộn nhất
        jobs = [j for j in drafts if not j.get("scheduled_at")]
        last = max(taken(name) or [""])
        start = datetime.strptime(last, FMT) + timedelta(minutes=1) if last else None
    else:
        jobs = [j for j in drafts if j["id"] in ids and not j.get("scheduled_at")]
        start = None
    jobs.sort(key=lambda j: _natural(Path(j["video_path"])))
    slots = next_slots(pg, len(jobs), start)
    for j, t in zip(jobs, slots):
        db.update_job(j["id"], scheduled_at=t.strftime(FMT))
    return len(slots)


def replan(pg, jobs, start, end_day=None) -> tuple:
    """Xếp lại giờ cho các video (chưa đẩy lên Facebook). Trả về (số đã xếp, số thiếu chỗ)."""
    jobs = sorted(jobs, key=lambda j: (j.get("scheduled_at") or "9999", _natural(Path(j["video_path"]))))
    slots = next_slots(pg, len(jobs), start, end_day, exclude_ids=[j["id"] for j in jobs])
    for i, j in enumerate(jobs):
        db.update_job(j["id"], scheduled_at=slots[i].strftime(FMT) if i < len(slots) else "")
    return len(slots), len(jobs) - len(slots)


def move(video_path, pg, sub) -> str:
    """Chuyển video sang ĐÃ UP / VIDEO LỖI của trang (trùng tên thì thêm số)."""
    src = Path(video_path)
    if not src.exists():
        return video_path
    dst_dir = folder(pg, sub)
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst, i = dst_dir / src.name, 1
    while dst.exists():
        dst, i = dst_dir / f"{src.stem}_{i}{src.suffix}", i + 1
    shutil.move(str(src), str(dst))
    return str(dst)


def ensure_folders(pg):
    for sub in (FOLDER_TODO, FOLDER_DONE, FOLDER_ERR):
        folder(pg, sub).mkdir(parents=True, exist_ok=True)


def tool_week(name, since) -> dict:
    """Việc tool đã làm/đã hẹn cho trang trong tuần này (đếm cả bài hẹn giờ chưa tới giờ)."""
    end = since + timedelta(days=7)
    out = {"reels_done": 0, "reels_planned": 0, "stories_done": 0, "stories_planned": 0}
    for j in db.list_jobs(["pending", "running", "scheduled_fb", "done"], "facebook", name):
        try:
            t = datetime.strptime(j["scheduled_at"], FMT)
        except Exception:
            continue
        if not (since <= t < end):
            continue
        past = t <= datetime.now()
        out["reels_done" if past and j["status"] in ("scheduled_fb", "done") else "reels_planned"] += 1
        if int(j.get("fb_story") or 0):
            out["stories_done" if j.get("fb_story_state") == "done" else "stories_planned"] += 1
    return out
