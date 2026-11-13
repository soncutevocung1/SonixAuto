"""Đồng bộ lịch đăng TikTok: không để ngày nào thiếu video so với số video/ngày đã đặt, xử lý video lỡ giờ.

- lap_ngay_thieu: ngày còn thiếu (vd đặt 10/ngày mà ngày cuối mới 5) -> kéo video xếp ở NGÀY SAU CÙNG (chưa đẩy lên
  TikTok) về lấp chỗ trống sớm nhất. Video mới bác thêm vào cũng được xếp vào ngày thiếu trước (schedule.plan).
- Lỡ giờ: video chưa kịp đăng mà đã quá giờ hẹn > LATE_MIN phút (máy tắt, bộ đăng dừng...) -> bộ đăng KHÔNG tự đăng,
  chuyển 'lo_gio' và hỏi bác: dời sang khung giờ trống tiếp theo, hoặc đăng bù dồn 2-4 video/lần.
"""
from datetime import datetime, timedelta

from . import db
from . import schedule as sch
from .config import channel_plan, post_now

FMT = db.TIME_FMT
LATE_MIN = 20
MOVABLE = ("draft", "pending")  # chưa đẩy lên TikTok nên đổi giờ thoải mái


def _dt(s):
    try:
        return datetime.strptime(s, FMT)
    except Exception:
        return None


def _jobs(channel, statuses):
    return [j for j in db.list_jobs(list(statuses), "tiktok", channel) if j.get("scheduled_at")]


def day_counts(channel, days=14) -> list:
    """[(ngày, số video đã xếp, số/ngày đặt)] từ hôm nay tới ngày xếp muộn nhất (tối đa `days` ngày)."""
    from .config import load_settings
    per = int(channel_plan(load_settings(), channel).get("per_day", 4))
    js = _jobs(channel, ("draft", "pending", "running", "scheduled", "done", "paused", "lo_gio"))
    cnt = {}
    for j in js:
        t = _dt(j["scheduled_at"])
        if t:
            cnt[t.date()] = cnt.get(t.date(), 0) + 1
    today = datetime.now().date()
    last = max([d for d in cnt if d >= today] or [today])
    out, d = [], today
    while d <= last and len(out) < days:
        out.append((d, cnt.get(d, 0), per))
        d += timedelta(days=1)
    return out


def _plan_one(settings, channel, exclude_id):
    p = channel_plan(settings, channel)
    taken = {j["scheduled_at"] for j in _jobs(channel, ("draft", "pending", "running", "scheduled", "done", "paused"))
             if j["id"] != exclude_id}
    t = sch.plan(1, datetime.now() + timedelta(minutes=30), settings["golden_hours"], p["per_day"], p["gap_min"],
                 p["start"], p["end"], p["golden_first"], p["golden_per_slot"], taken=taken)
    return t[0] if t else None


def lap_ngay_thieu(settings, channel, log=None) -> int:
    """Kéo video ở cuối lịch (chưa lên TikTok) về lấp ngày còn thiếu sớm hơn. Trả về số video đã dời."""
    if post_now(settings, channel):
        return 0
    moved = 0
    soon = datetime.now() + timedelta(minutes=30)
    for _ in range(300):
        movable = [j for j in _jobs(channel, MOVABLE) if (_dt(j["scheduled_at"]) or soon) > soon]
        if not movable:
            break
        last = max(movable, key=lambda j: j["scheduled_at"])
        t = _plan_one(settings, channel, last["id"])
        if not t or t.date() >= _dt(last["scheduled_at"]).date():
            break  # không còn ngày nào sớm hơn bị thiếu
        db.update_job(last["id"], scheduled_at=t.strftime(FMT))
        moved += 1
    if moved and log:
        log(f"  · Kênh «{channel}»: dời {moved} video ở cuối lịch về lấp ngày còn thiếu")
    return moved


def lap_tat_ca(settings, log=None) -> int:
    return sum(lap_ngay_thieu(settings, c["name"], log) for c in settings.get("channels", [])
               if c.get("enabled", True))


# ------------------------------- lỡ giờ -------------------------------
def is_late(job, now=None) -> bool:
    t = _dt(job.get("scheduled_at") or "")
    return bool(t) and not int(job.get("late_ok") or 0) and (now or datetime.now()) - t > timedelta(minutes=LATE_MIN)


def doi_khung_sau(settings, ids) -> int:
    """Dời các video lỡ giờ sang khung giờ trống tiếp theo (vẫn giữ đủ số video/ngày đã đặt)."""
    jobs = sorted([j for j in (db.get_job(i) for i in ids) if j], key=lambda j: j.get("scheduled_at") or "")
    by_ch = {}
    for j in jobs:
        by_ch.setdefault(j["channel"], []).append(j)
    n = 0
    for ch, js in by_ch.items():
        p = channel_plan(settings, ch)
        taken = {j["scheduled_at"] for j in _jobs(ch, ("draft", "pending", "running", "scheduled", "done", "paused"))}
        times = sch.plan(len(js), datetime.now() + timedelta(minutes=30), settings["golden_hours"], p["per_day"],
                         p["gap_min"], p["start"], p["end"], p["golden_first"], p["golden_per_slot"], taken=taken)
        for j, t in zip(js, times):
            db.update_job(j["id"], status="pending", scheduled_at=t.strftime(FMT), late_ok=0)
            n += 1
    return n


def dang_bu(ids, per_batch=3, gap_min=30) -> int:
    """Đăng bù: dồn `per_batch` video mỗi lần, các lần cách nhau `gap_min` phút. Đợt đầu đăng ngay."""
    jobs = sorted([j for j in (db.get_job(i) for i in ids) if j], key=lambda j: j.get("scheduled_at") or "")
    now = datetime.now().replace(second=0, microsecond=0)
    for i, j in enumerate(jobs):
        t = now + timedelta(minutes=gap_min * (i // max(1, per_batch)))
        if t > now:
            t = sch.round5(t)
        db.update_job(j["id"], status="pending", scheduled_at=t.strftime(FMT), late_ok=1)
    return len(jobs)
