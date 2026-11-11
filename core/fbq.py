"""Hàng chờ Facebook: cài đặt từng trang, thư mục video, xếp giờ đăng, chuyển file sau khi đăng.

Mỗi trang có 1 thư mục gốc (vd D:\\REUP) gồm CHƯA UP / ĐÃ UP / VIDEO LỖI giống TikTok.
Giờ đăng do bác tự đặt (vd 11:30, 19:30) → mỗi ngày đăng đúng số khung giờ đó.
"""
import re
import shutil
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


def times_of(pg) -> list:
    out = []
    for x in re.split(r"[,;\s]+", str(pg.get("times") or "11:30, 19:30")):
        try:
            out.append(datetime.strptime(x.strip(), "%H:%M").strftime("%H:%M"))
        except ValueError:
            pass
    return sorted(set(out)) or ["11:30", "19:30"]


def folder(pg, sub=FOLDER_TODO) -> Path:
    return Path(pg.get("folder") or r"D:\REUP") / sub


def _natural(p: Path):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.stem)]


def new_videos(pg) -> list:
    """Video trong CHƯA UP chưa nằm trong hàng chờ, xếp theo số trong tên (1, 2, ..., 10)."""
    d = folder(pg)
    if not d.is_dir():
        return []
    busy = db.active_paths("facebook")
    return sorted([p for p in d.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS and str(p) not in busy],
                  key=_natural)


def taken(name) -> set:
    with db.conn() as c:
        rows = c.execute("SELECT scheduled_at FROM jobs WHERE platform='facebook' AND channel=? AND scheduled_at!='' "
                         "AND status NOT IN ('error')", (name,)).fetchall()
    return {r[0] for r in rows}


def next_slots(pg, n, start=None) -> list:
    """n khung giờ trống tiếp theo của trang (cách bây giờ ít nhất 30 phút)."""
    start = start or datetime.now() + timedelta(minutes=30)
    used, out, day = taken(pg["name"]), [], start.date()
    while len(out) < n and day < start.date() + timedelta(days=400):
        for hm in times_of(pg):
            t = datetime.combine(day, datetime.strptime(hm, "%H:%M").time())
            s = t.strftime(FMT)
            if t >= start and s not in used:
                out.append(t)
                used.add(s)
                if len(out) >= n:
                    break
        day += timedelta(days=1)
    return out


def plan_new(name, ids, settings) -> int:
    """Xếp giờ cho các video Facebook vừa phân tích xong."""
    pg = page(settings, name)
    if not pg:
        return 0
    jobs = [j for j in db.list_jobs(["draft"], "facebook", name) if j["id"] in ids and not j.get("scheduled_at")]
    for j, t in zip(jobs, next_slots(pg, len(jobs))):
        db.update_job(j["id"], scheduled_at=t.strftime(FMT))
    return len(jobs)


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
