"""Phân tích video CHẠY NGẦM (không phụ thuộc cửa sổ giao diện).

Nút "Phân tích" chỉ đưa video vào hàng (trạng thái 'analyzing'). Luồng nền này lấy ra phân tích từng đợt 4 video,
ghi kết quả vào hàng chờ, rồi xếp lịch giờ vàng cho các video vừa xong. Bấm 2 lần, bấm sang tab khác,
tắt cửa sổ hay tắt máy giữa chừng đều không bị kẹt: lần sau mở tool, video còn dở được phân tích tiếp.
"""
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

from . import analyze as ana
from . import db
from . import fbq
from . import schedule as sch
from . import sounds as snd
from . import stats
from .config import LOG_DIR, MODELS, NO_AI, ai_key, channel_plan, load_settings

NAME = "sonix-phan-tich"
FMT = db.TIME_FMT
_lock = threading.Lock()
_USED = {}  # âm thanh Yêu thích đã gán (xoay vòng để các video không trùng nhau)


def default_model(settings) -> str:
    m = settings.get("ai_model")
    return m if m in MODELS and ai_key(settings, m) else NO_AI


def _log(msg):
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_DIR / "phan_tich.log", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%d/%m %H:%M:%S}  {msg}\n")
    except Exception:
        pass


def analyze_fb_job(jid, video, page, model, settings, redo=False) -> str:
    try:
        r = ana.analyze_fb(jid, video, page, settings, model)
        if redo and int((db.get_job(jid) or {}).get("cover_by_user") or 0):
            r.pop("cover_path", None)  # viết lại caption: giữ ảnh bìa bác đã chọn
        db.update_job(jid, status="draft", redo_caption=0, **r)
        if not redo:  # viết lại caption thì không đếm thêm lượt phân tích
            stats.record("phan_tich", db.get_job(jid))
        return ""
    except Exception as e:
        db.update_job(jid, status="draft", frames=[], cover_path="",
                      ai_note=f"Phân tích lỗi: {str(e)[:150]} → bấm Phân tích lại hoặc Bỏ video")
        return f"{Path(video).name}: {e}"


def analyze_job(jid, video, channel, model, settings, caption_only=False, item_key="", platform="tiktok") -> str:
    """Phân tích 1 video, ghi ngay kết quả vào hàng chờ. Trả về '' nếu ổn, hoặc nội dung lỗi."""
    if platform == "facebook":
        return analyze_fb_job(jid, video, channel, model, settings, redo=caption_only)
    try:
        r = ana.analyze(jid, video, channel, settings, model, caption_only=caption_only, known_item=item_key)
        db.update_job(jid, status="draft", redo_caption=0, **r)
        if not caption_only:
            j = db.get_job(jid) or {}
            stats.record("phan_tich", j)
            if j.get("music_mode") == "auto" and j.get("music_ref") == "favitem":  # gán âm thanh để nghe thử trước
                f = snd.pick_for(channel, j.get("item_key") or "", _USED.setdefault(channel, {}))
                if f:
                    db.update_job(jid, music_mode="tiktok", music_ref=snd.ref_of(f))
                else:  # kênh không có Yêu thích riêng -> mượn âm thanh đúng sản phẩm của kênh khác
                    b = snd.borrow_for(channel, j.get("item_key") or "", settings, _USED.setdefault("_muon", {}))
                    if b:
                        db.update_job(jid, **b)
        return ""
    except Exception as e:
        if caption_only:  # chỉ viết lại caption hỏng -> giữ nguyên mọi thứ khác
            db.update_job(jid, status="draft", redo_caption=0, ai_note=f"⚠️ Viết lại caption lỗi: {str(e)[:150]}")
            return f"{Path(video).name}: {e}"
        db.update_job(jid, status="draft", confidence=0, frames=[], cover_path="",
                      ai_note=f"⚠️ Phân tích lỗi: {str(e)[:150]} → bấm 🔄 Phân tích lại hoặc 🗑 Bỏ video")
        return f"{Path(video).name}: {e}"


def plan_new(channel, ids, settings):
    """Xếp lịch giờ vàng cho các video vừa phân tích xong (không đụng lịch bác đã chỉnh ở video khác)."""
    from .config import post_now
    if post_now(settings, channel):  # kênh đăng ngay khi xác nhận -> không xếp giờ
        return 0
    drafts = db.list_jobs(["draft"], "tiktok", channel)
    jobs = [j for j in drafts if j["id"] in ids and not j.get("scheduled_at")]
    if not jobs:
        return 0
    others = {j["scheduled_at"] for j in drafts if j["id"] not in ids and j.get("scheduled_at")}
    p = channel_plan(settings, channel)
    times = sch.plan(len(jobs), datetime.now() + timedelta(minutes=30), settings["golden_hours"], p["per_day"],
                     p["gap_min"], p["start"], p["end"], p["golden_first"], p["golden_per_slot"],
                     taken=db.taken_times(channel) | others)
    for j, t in zip(jobs, times):
        db.update_job(j["id"], scheduled_at=t.strftime(FMT))
    return len(times)


def _loop():
    _log("Bắt đầu luồng phân tích ngầm")
    last_scan = 0
    while True:
        try:
            if time.time() - last_scan > 60:  # Facebook tự động: 1 phút quét CHƯA UP 1 lần
                last_scan = time.time()
                added = fbq.auto_scan(load_settings())
                if added:
                    _log(f"Facebook tự động: thêm {added} video mới vào phân tích")
            todo = db.list_jobs(["analyzing"])
            if not todo:
                time.sleep(2)
                continue
            settings = load_settings()
            batch = todo[:8]
            touched = {}
            gem = any(str(j.get("ai_model") or default_model(settings)).startswith("gemini") for j in batch)
            with ThreadPoolExecutor(max_workers=2) as ex:  # 2 video/lần: đỡ nghẽn ổ cứng, Gemini miễn phí đỡ vượt lượt/phút
                futs = {ex.submit(analyze_job, j["id"], j["video_path"], j["channel"],
                                  j.get("ai_model") or default_model(settings), settings,
                                  bool(j.get("redo_caption")), j.get("item_key") or "",
                                  j.get("platform") or "tiktok"): j for j in batch}
                for fu in as_completed(futs):
                    j = futs[fu]
                    err = fu.result()
                    touched.setdefault((j.get("platform") or "tiktok", j["channel"]), set()).add(j["id"])
                    _log(f"{'✖ ' + err if err else '✔ ' + Path(j['video_path']).name} ({j['channel']})")
            for (pf, ch), ids in touched.items():
                (fbq.plan_new if pf == "facebook" else plan_new)(ch, ids, settings)
        except Exception:
            _log("Lỗi luồng phân tích: " + traceback.format_exc()[-600:])
            time.sleep(5)


def start():
    """Bật luồng phân tích ngầm (nếu chưa chạy). Gọi nhiều lần cũng chỉ có 1 luồng."""
    from . import desktop
    desktop.low_priority()
    with _lock:
        if any(t.name == NAME and t.is_alive() for t in threading.enumerate()):
            return False
        threading.Thread(target=_loop, name=NAME, daemon=True).start()
        return True


def pending_counts() -> dict:
    """Số video đang chờ/đang phân tích theo từng kênh."""
    out = {}
    for j in db.list_jobs(["analyzing"], "tiktok"):
        out[j["channel"]] = out.get(j["channel"], 0) + 1
    return out
