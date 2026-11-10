"""Xếp lịch đăng: ưu tiên khung giờ vàng, giới hạn số video/ngày, cách nhau tối thiểu."""
from datetime import datetime, timedelta

FMT = "%Y-%m-%d %H:%M"


def _hm(s):
    h, m = map(int, s.strip().split(":"))
    return h, m


def round5(dt: datetime) -> datetime:
    """TikTok chỉ cho chọn phút chia hết cho 5."""
    dt = dt.replace(second=0, microsecond=0)
    extra = (5 - dt.minute % 5) % 5
    return dt + timedelta(minutes=extra)


def is_golden(dt: datetime, golden, window_min=30) -> bool:
    for g in golden:
        h, m = _hm(g)
        gd = dt.replace(hour=h, minute=m)
        if abs((dt - gd).total_seconds()) <= window_min * 60:
            return True
    return False


def plan(n, start: datetime, golden, per_day=4, gap_min=90, day_start="05:00", day_end="22:30",
         golden_first=True, golden_per_slot=1, taken=()) -> list:
    """Trả về n mốc giờ (datetime) theo thứ tự."""
    gap = timedelta(minutes=max(5, int(gap_min)))
    taken_dt = [datetime.strptime(t, FMT) for t in taken if t]
    earliest = round5(start)
    out = []
    day = earliest.date()
    for _ in range(400):
        if len(out) >= n:
            break
        base = datetime.combine(day, datetime.min.time())
        sh, sm = _hm(day_start)
        eh, em = _hm(day_end)
        w0, w1 = base.replace(hour=sh, minute=sm), base.replace(hour=eh, minute=em)
        cands = []
        if golden_first:
            for g in sorted(golden):
                h, m = _hm(g)
                for i in range(max(1, int(golden_per_slot))):
                    cands.append(base.replace(hour=h, minute=m) + gap * i)
        t = w0
        while t <= w1:
            cands.append(t)
            t += gap
        used_today = [x for x in taken_dt + out if x.date() == day]
        quota = max(0, int(per_day) - len(used_today))
        chosen = []
        for c in cands:
            if len(chosen) >= quota or len(out) + len(chosen) >= n:
                break
            c = round5(c)
            if c < earliest or c.date() != day or c < w0 or c > w1:  # giờ vàng ngoài khung đăng thì bỏ
                continue
            if any(abs((c - x).total_seconds()) < gap.total_seconds() for x in used_today + chosen):
                continue
            chosen.append(c)
        out.extend(sorted(chosen))
        day += timedelta(days=1)
    return sorted(out)[:n]
