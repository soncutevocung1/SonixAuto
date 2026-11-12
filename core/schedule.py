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


ORDERS = {"folder": "Theo thứ tự trong thư mục (tên file)",
          "mix": "Xen kẽ sản phẩm (lần lượt từng sản phẩm)",
          "random": "Ngẫu nhiên (không để 2 video cùng sản phẩm liền nhau)"}


def order_jobs(jobs, mode="folder", seed=None) -> list:
    """Sắp thứ tự đăng các video: theo thư mục (tên file), xen kẽ sản phẩm, hoặc ngẫu nhiên tránh trùng liền nhau."""
    import random
    import re as _re
    from pathlib import Path

    def nat(j):
        return [int(t) if t.isdigit() else t.lower() for t in _re.split(r"(\d+)", Path(j["video_path"]).name)]

    base = sorted(jobs, key=nat)
    if mode not in ("mix", "random") or len(base) < 3:
        return base
    groups = {}
    for j in base:
        groups.setdefault(j.get("item_key") or "", []).append(j)
    rnd = random.Random(seed)
    if mode == "random":
        for g in groups.values():
            rnd.shuffle(g)
    out, last = [], None
    while any(groups.values()):
        # lấy nhóm còn nhiều video nhất (khác sản phẩm vừa đăng) -> trải đều; ngẫu nhiên thì chọn bừa trong các nhóm hợp lệ
        ok = [k for k, g in groups.items() if g and k != last] or [k for k, g in groups.items() if g]
        if mode == "random":
            weights = [len(groups[k]) for k in ok]
            k = rnd.choices(ok, weights=weights)[0]
        else:
            k = max(ok, key=lambda x: (len(groups[x]), -list(groups).index(x)))
        out.append(groups[k].pop(0))
        last = k
    return out
