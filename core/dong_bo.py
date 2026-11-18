"""Giữ sản phẩm - giỏ hàng - ảnh bìa - âm thanh của 1 video luôn khớp nhau.

Lỗi gặp (báo lỗi #1116095332): bác đổi giỏ hàng của video sang Kích rễ TC01 nhưng 'sản phẩm của video' vẫn là
Bọ trĩ, nên ảnh bìa theme và âm thanh Yêu thích (đi theo sản phẩm) vẫn là của Bọ trĩ.
"""
from pathlib import Path

from . import covers as cov
from . import db
from . import products as prod
from . import sounds as snd


def _music_item_ok(channel, settings, job) -> bool:
    """Âm thanh Yêu thích / mượn đang gắn có đúng sản phẩm của video không (nhạc khác thì coi như ổn)."""
    item = job.get("item_key") or ""
    if job.get("music_mode") == "tiktok":
        mid = snd.parse_ref(job.get("music_ref") or "")[0]
        f = next((x for x in snd.load_favs(channel) if x.get("id") == mid), None) if mid else None
        return not f or not f.get("items") or item in f["items"]
    if job.get("music_mode") == "local":
        f = next((x for x in snd.shared_pool(channel, settings) if x["file"] == job.get("music_ref")), None)
        return not f or item in (f.get("items") or [])
    return True


def khop(settings, channel, job, root, log=None) -> list:
    """Sửa 1 video cho khớp sản phẩm. Trả về các việc đã sửa (để ghi nhật ký)."""
    done = []
    k = prod.item_for(settings, channel, job.get("products"))
    if k and k != (job.get("item_key") or ""):
        db.update_job(job["id"], item_key=k)
        job["item_key"] = k
        done.append(f"sản phẩm theo giỏ hàng: {k}")
    try:
        c = cov.fix_conflict(settings, channel, job, root)
        if c:
            done.append(f"ảnh bìa sai sản phẩm → {c}")
    except Exception:
        pass
    if not int(job.get("music_by_user") or 0) and not _music_item_ok(channel, settings, job):
        upd, _ = snd.fav_for(channel, job.get("item_key") or "", settings)
        if not upd:
            mode, _, ref = (settings.get("default_music") or "auto::smart").partition("::")
            upd = {"music_mode": mode if ref else "none", "music_ref": ref}
        db.update_job(job["id"], **upd)
        job.update(upd)
        done.append("âm thanh sai sản phẩm → " + (Path(upd["music_ref"]).name if upd["music_mode"] == "local"
                                                   else str(upd.get("music_ref") or "nhạc mặc định")))
    if done and log:
        log(f"  · Sửa cho khớp sản phẩm: {'; '.join(done)}")
    return done


def khop_tat_ca(settings, channel, jobs, root) -> int:
    n = 0
    for j in jobs:
        try:
            n += bool(khop(settings, channel, j, root))
        except Exception:
            pass
    return n
