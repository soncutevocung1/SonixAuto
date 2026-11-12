"""BỘ ĐĂNG TỰ ĐỘNG của SonixDangVideo — để cửa sổ này chạy, đừng tắt.

  python runner.py                         chạy liên tục
  python runner.py --once                  xử lý 1 lượt rồi thoát
  python runner.py --login "Tên kênh"      mở trình duyệt kênh để đăng nhập TikTok
  python runner.py --sync-showcase "Kênh"  đọc danh sách Trưng bày sản phẩm
  python runner.py --sync-sounds "Kênh"    đọc âm thanh Yêu thích + tải đoạn nghe thử
  python runner.py --inspect "Kênh"        chụp lại giao diện TikTok Studio (gửi người hỗ trợ khi tool lỗi)
"""
import argparse
import logging
import os
import random
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("PYTHONUTF8", "1")

from core import channels as chs  # noqa: E402
from core import db, facebook, fbq, progress, sounds, stats, tiktok  # noqa: E402
from core.caption import build_text  # noqa: E402
from core.config import (DATA_DIR, FOLDER_DONE, FOLDER_ERR, FOLDER_TODO, HEARTBEAT_FILE, RUNNER_LOG, WORK_DIR,  # noqa: E402
                         ensure_dirs, get_channel, load_settings, save_settings, slug)
from core.video_utils import mix_music, strip_audio  # noqa: E402

ensure_dirs()
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%d/%m %H:%M:%S",
                    handlers=[logging.FileHandler(RUNNER_LOG, encoding="utf-8"), logging.StreamHandler(sys.stdout)])
_info = logging.getLogger("sonix").info


def log(msg):
    """Ghi nhật ký + cập nhật tiến độ cho tab Hàng chờ."""
    _info(msg)
    progress.on_log(str(msg))

BLOCK_DIR = DATA_DIR / "blocked"


# ---------- kênh bị chặn (chưa đăng nhập / trình duyệt đang mở) ----------
def block_channel(channel, msg):
    BLOCK_DIR.mkdir(parents=True, exist_ok=True)
    (BLOCK_DIR / f"{slug(channel)}.txt").write_text(f"{channel}\n{msg}", encoding="utf-8")


def blocked_channels() -> dict:
    out = {}
    if BLOCK_DIR.exists():
        for f in BLOCK_DIR.glob("*.txt"):
            lines = f.read_text(encoding="utf-8").split("\n", 1)
            out[lines[0]] = lines[1] if len(lines) > 1 else ""
    return out


def unblock_channel(channel):
    f = BLOCK_DIR / f"{slug(channel)}.txt"
    if f.exists():
        f.unlink()


def heartbeat():
    HEARTBEAT_FILE.write_text(str(time.time()), encoding="utf-8")


def runner_alive() -> bool:
    try:
        return time.time() - float(HEARTBEAT_FILE.read_text()) < 90
    except Exception:
        return False


# ---------- xử lý từng loại job ----------
def due_tiktok(job, now, settings) -> bool:
    if not job["scheduled_at"]:
        return True
    t = datetime.strptime(job["scheduled_at"], db.TIME_FMT)
    return t - now <= timedelta(days=int(settings.get("tt_max_ahead_days", 10)))


def due_facebook(job, now, settings=None) -> bool:
    """Đẩy lên Facebook trước giờ đăng tối đa N ngày (FB tự giữ lịch, máy tắt vẫn đăng).
    Để N nhỏ (mặc định 2) để bác còn sửa caption/giờ trong tool trước khi đẩy."""
    if not job.get("scheduled_at"):
        return False  # chưa có giờ thì không bao giờ tự đăng
    t = datetime.strptime(job["scheduled_at"], db.TIME_FMT)
    ahead = timedelta(days=float((settings or {}).get("fb_max_ahead_days", 2)))
    return t <= now or (t - now) <= ahead


def run_tiktok(job, settings):
    root = settings["root_folder"]
    tmp = None
    if job.get("music_mode") == "auto" and job.get("music_ref") == "favitem":  # chưa gán bài: thử mượn âm thanh
        b = sounds.borrow_for(job["channel"], job.get("item_key") or "", settings)
        if b:
            job.update(b)
            db.update_job(job["id"], **b)
            log(f"  - Mượn âm thanh kênh khác đúng sản phẩm: {Path(b['music_ref']).name}")
    keep = job.get("keep_audio") is None or int(job.get("keep_audio")) == 1
    src = Path(job["video_path"])
    if job.get("music_mode") == "local" and job.get("music_ref"):
        log(f"  - Ghép nhạc nền {Path(job['music_ref']).name}" + ("" if keep else " (tắt âm thanh gốc)") + "...")
        tmp = WORK_DIR / str(job["id"]) / ("nhac_" + src.stem + (".mp4" if keep else src.suffix))
        tmp.parent.mkdir(parents=True, exist_ok=True)
        if keep:
            mix_music(job["video_path"], job["music_ref"], str(tmp), float(settings.get("music_volume", 0.15)))
        else:
            strip_audio(job["video_path"], str(tmp), job["music_ref"])
        job["_upload_path"] = str(tmp)
    elif not keep:
        log("  - Tắt âm thanh gốc của video...")
        tmp = WORK_DIR / str(job["id"]) / ("tat_tieng_" + src.name)
        tmp.parent.mkdir(parents=True, exist_ok=True)
        strip_audio(job["video_path"], str(tmp))
        job["_upload_path"] = str(tmp)
    with tiktok.ProfileLock(job["channel"]) as lock:
        status, note = tiktok.post(job, settings, log=log, lock=lock)
    new_path = chs.move_to(job["video_path"], root, job["channel"], FOLDER_DONE)
    db.rename_video_path(job["video_path"], new_path)
    db.update_job(job["id"], status=status, result=note)
    stats.record("hen_gio", job)
    log(f"  ✔ {db.STATUS_LABELS.get(status)}: {note} → đã chuyển vào {FOLDER_DONE}")
    if tmp and tmp.exists():
        tmp.unlink()


def fail_tiktok(job, settings, err):
    msg = f"{type(err).__name__}: {str(err)[:500]}"
    new_path = chs.move_to(job["video_path"], settings["root_folder"], job["channel"], FOLDER_ERR)
    db.rename_video_path(job["video_path"], new_path)
    chs.write_error_note(new_path, msg)
    db.update_job(job["id"], status="error", result=msg)
    stats.record("loi", job)
    log(f"  ✖ Lỗi → chuyển vào {FOLDER_ERR}: {msg}")


def run_facebook(job, settings):
    page = fbq.page(settings, job["channel"])
    if not page:
        raise facebook.FacebookError(f"Không thấy trang FB '{job['channel']}' trong tool (tab Facebook)")
    t = datetime.strptime(job["scheduled_at"], db.TIME_FMT) if job.get("scheduled_at") else datetime.now()
    if t < datetime.now() - timedelta(minutes=15):  # đã qua giờ (duyệt trễ / máy tắt) -> dời sang khung trống kế tiếp
        slots = fbq.next_slots(page, 1, exclude_ids=[job["id"]])
        t = slots[0] if slots else datetime.now()  # hết khung trong lịch -> đăng ngay
        db.update_job(job["id"], scheduled_at=t.strftime(db.TIME_FMT))
        log(f"  - Lỡ giờ cũ, dời sang {t:%d/%m %H:%M}")
    text = build_text(job["caption"], job["hashtags"], job.get("product_link", ""), "facebook")
    cover = job.get("cover_path") if int(job.get("cover_by_user") or 0) else ""
    status, note = facebook.post(job["video_path"], text, page, t, job.get("product_link", ""),
                                 settings.get("fb_graph_version", "v23.0"), cover=cover)
    if page.get("folder"):
        new_path = fbq.move(job["video_path"], page, FOLDER_DONE)
        db.rename_video_path(job["video_path"], new_path)
    db.update_job(job["id"], status=status, result=note)
    stats.record("hen_gio", job)
    log(f"  ✔ FB {db.STATUS_LABELS.get(status)}: {note}")


def fail_facebook(job, settings, err):
    msg = f"{type(err).__name__}: {facebook.safe(err)[:400]}"
    page = fbq.page(settings, job["channel"])
    if page.get("folder") and "Token" not in msg and "token" not in msg:  # lỗi mã thì giữ video để đăng lại
        new_path = fbq.move(job["video_path"], page, FOLDER_ERR)
        db.rename_video_path(job["video_path"], new_path)
        chs.write_error_note(new_path, msg)
    db.update_job(job["id"], status="error", result=msg)
    stats.record("loi", job)
    log(f"  ✖ FB lỗi: {msg}")


_LAST_COVER_CHECK = {}
_RETRY_AFTER = {}  # job id -> lúc được thử lại (ảnh bìa chưa lên)


def check_covers(settings):
    """Lúc rảnh: vào TikTok Studio kiểm tra ảnh bìa các video đã hẹn giờ.
    - Thiếu bìa: đưa video về CHƯA UP, báo bác xoá bài trong app TikTok (web không cho xoá bài có giỏ hàng).
    - Bác đã xoá bài (thiếu bìa, hoặc chưa kiểm): tự đăng lại kèm ảnh bìa."""
    from core import schedule as sch
    from core.config import channel_plan
    now = datetime.now()
    soon, old = (now + timedelta(minutes=5)).strftime(db.TIME_FMT), (now - timedelta(minutes=3)).strftime(db.TIME_FMT)
    todo = {}
    for j in db.list_jobs(["scheduled", "check"], "tiktok"):
        if (int(j.get("cover_checked") or 0) in (0, 2) and j.get("cover_path") and j.get("scheduled_at", "") > soon
                and (j.get("updated_at") or "") <= old and (j["status"] == "scheduled" or int(j.get("cover_checked") or 0) == 2)):
            todo.setdefault(j["channel"], []).append(j)
    blocked = blocked_channels()
    for ch, jobs in todo.items():
        if ch in blocked or time.time() - _LAST_COVER_CHECK.get(ch, 0) < 15 * 60:
            continue
        _LAST_COVER_CHECK[ch] = time.time()
        log(f"Kiểm tra ảnh bìa {len(jobs)} video đã hẹn giờ của kênh «{ch}» trên TikTok Studio...")
        heartbeat()
        try:
            res = tiktok.verify_covers(settings, ch, jobs, log)
        except Exception as e:
            log(f"  ! Chưa kiểm tra được: {str(e)[:150]}")
            continue
        from collections import Counter
        cnt = Counter(v[0] for v in res.values())
        log(f"  Kết quả: {cnt.get('ok', 0)} đúng bìa · {cnt.get('thieu_bia', 0)} thiếu bìa · "
            f"{cnt.get('da_xoa', 0)} đã xoá trên TikTok · {cnt.get('chua_ro', 0)} chưa rõ (kiểm lại sau)")
        root = settings.get("root_folder")
        for j in jobs:
            r_ = res.get(j["id"], ("chua_ro", -1))
            kind, sc = r_[0], r_[1]
            name = Path(j["video_path"]).name
            if len(r_) > 2 and r_[2] is not None:  # bài còn trên TikTok nhưng giờ hẹn khác giờ tool ghi -> sửa lại giờ
                log(f"  · {name}: giờ hẹn thật trên TikTok là {r_[2] or 'đã đăng'} (tool ghi {j['scheduled_at']})")
                if r_[2]:
                    db.update_job(j["id"], scheduled_at=r_[2])
                    j["scheduled_at"] = r_[2]
            if kind == "ok":
                db.update_job(j["id"], cover_checked=1)
            elif kind == "thieu_bia" and int(j.get("cover_checked") or 0) == 0:
                new_path = chs.move_to(j["video_path"], root, ch, FOLDER_TODO) if root else j["video_path"]
                db.rename_video_path(j["video_path"], new_path)
                t = datetime.strptime(j["scheduled_at"], db.TIME_FMT)
                db.update_job(j["id"], status="check", cover_checked=2,
                              result=f"THIẾU ẢNH BÌA trên TikTok (bài hẹn {t:%H:%M %d/%m}). Bác vào app TikTok xoá bài "
                                     f"đó, tool tự đăng lại kèm ảnh bìa.")
                log(f"  ✖ {name}: thiếu ảnh bìa (điểm {sc:.0f}) → về CHƯA UP, nhờ bác xoá bài {t:%H:%M %d/%m} trong app")
            elif kind == "da_xoa":
                if root:
                    new_path = chs.move_to(j["video_path"], root, ch, FOLDER_TODO)
                    db.rename_video_path(j["video_path"], new_path)
                t = datetime.strptime(j["scheduled_at"], db.TIME_FMT)
                if t < now + timedelta(minutes=40):  # giờ cũ sắp tới / đã qua -> khung trống kế tiếp
                    p = channel_plan(settings, ch)
                    slots = sch.plan(1, now + timedelta(minutes=30), settings["golden_hours"], p["per_day"],
                                     p["gap_min"], p["start"], p["end"], p["golden_first"], p["golden_per_slot"],
                                     taken=db.taken_times(ch))
                    t = slots[0] if slots else now + timedelta(minutes=30)
                db.update_job(j["id"], status="pending", cover_checked=0, scheduled_at=t.strftime(db.TIME_FMT),
                              result="Bài cũ đã bị xoá trên TikTok → đăng lại kèm ảnh bìa")
                log(f"  ↻ {name}: bài đã xoá trên TikTok → đăng lại lúc {t:%H:%M %d/%m}")


def run_fb_stories(settings, now):
    """Video đã tới giờ đăng mà bác chọn 'đăng kèm vào Tin' -> đăng vào Tin (Tin không hẹn giờ trước được)."""
    for job in db.list_jobs(["scheduled_fb", "done"], "facebook"):
        if not int(job.get("fb_story") or 0) or job.get("fb_story_state"):
            continue
        try:
            t = datetime.strptime(job["scheduled_at"], db.TIME_FMT)
        except Exception:
            continue
        if now < t + timedelta(minutes=2):
            continue
        if now > t + timedelta(hours=12):  # máy tắt quá lâu: bỏ, tránh đăng Tin cũ dồn cục
            db.update_job(job["id"], fb_story_state="bỏ (quá giờ)")
            continue
        page = fbq.page(settings, job["channel"])
        heartbeat()
        try:
            from core.video_utils import probe
            if probe(job["video_path"])["duration"] > 60:
                db.update_job(job["id"], fb_story_state="bỏ (video dài hơn 60 giây)")
                continue
            facebook.post_story(page["page_id"], page["token"], job["video_path"],
                                settings.get("fb_graph_version", "v23.0"))
            db.update_job(job["id"], fb_story_state="done")
            log(f"  ✔ FB Tin: {Path(job['video_path']).name} ({job['channel']})")
        except Exception as e:
            db.update_job(job["id"], fb_story_state=f"lỗi: {facebook.safe(e)[:150]}")
            log(f"  ✖ FB Tin lỗi: {facebook.safe(e)}")


def run_once():
    settings = load_settings()
    now = datetime.now()
    blocked = blocked_channels()
    did_tt = False
    try:
        run_fb_stories(settings, now)
    except Exception as e:
        log(f"  ✖ FB Tin: {facebook.safe(e)}")
    for job in db.list_jobs(["pending"]):
        heartbeat()
        if (DATA_DIR / "stop_runner.flag").exists():  # có lệnh dừng (tắt tool / cập nhật): dừng sau video đang đăng
            log("  · Có lệnh dừng → không đăng thêm video, dừng bộ đăng")
            return
        if job["platform"] == "facebook":
            if not due_facebook(job, now, settings) or not db.claim_job(job["id"]):
                continue
            log(f"▶ #{job['id']} FACEBOOK · {job['channel']} · {Path(job['video_path']).name}")
            try:
                run_facebook(db.get_job(job["id"]), settings)
            except Exception as e:
                fail_facebook(db.get_job(job["id"]), settings, e)
            continue

        if job["channel"] in blocked or not due_tiktok(job, now, settings) \
                or _RETRY_AFTER.get(job["id"], 0) > time.time():
            continue
        if not settings.get("root_folder"):
            log("! Chưa chọn thư mục gốc trong tool")
            return
        if did_tt:
            a, b = settings.get("tt_gap_seconds", [10, 25])
            wait = random.uniform(a, b)
            log(f"  … nghỉ {wait:.0f} giây trước video kế tiếp")
            end = time.time() + wait
            while time.time() < end:
                heartbeat()
                time.sleep(5)
        if not db.claim_job(job["id"]):
            continue
        job = db.get_job(job["id"])
        log(f"▶ #{job['id']} TIKTOK · {job['channel']} · {Path(job['video_path']).name}")
        try:
            run_tiktok(job, settings)
        except (tiktok.NeedLogin, tiktok.BrowserBusy) as e:
            # lỗi của cả kênh: giữ video ở CHƯA UP, dừng kênh đến khi người dùng xử lý
            db.update_job(job["id"], status="pending", result=str(e))
            block_channel(job["channel"], str(e))
            blocked[job["channel"]] = str(e)
            log(f"  ⛔ DỪNG KÊNH «{job['channel']}»: {e}")
        except tiktok.TikTokError as e:
            if str(e).startswith("Ảnh bìa"):  # bìa không lên -> KHÔNG đăng, giữ ở CHƯA UP, 10 phút sau thử lại
                n = int(job.get("attempts") or 0) + 1
                if n >= 3:
                    db.update_job(job["id"], status="check", attempts=n,
                                  result=f"Không gắn được ảnh bìa sau {n} lần → chưa đăng, video vẫn ở CHƯA UP. {e}")
                    log(f"  ✖ Không gắn được ảnh bìa sau {n} lần → chuyển 'Cần kiểm tra', video vẫn ở CHƯA UP")
                else:
                    t = max(datetime.strptime(job["scheduled_at"], db.TIME_FMT) if job.get("scheduled_at") else now,
                            datetime.now() + timedelta(minutes=10))
                    db.update_job(job["id"], status="pending", attempts=n, result=f"Ảnh bìa chưa lên, thử lại ({n}/3)",
                                  scheduled_at=job.get("scheduled_at") or t.strftime(db.TIME_FMT))
                    _RETRY_AFTER[job["id"]] = time.time() + 600
                    log(f"  ! Ảnh bìa chưa lên → chưa đăng, 10 phút sau thử lại ({n}/3)")
            else:
                fail_tiktok(job, settings, e)
        except Exception as e:
            fail_tiktok(job, settings, e)
        did_tt = True
    if not did_tt:  # rảnh: kiểm tra ảnh bìa các bài đã hẹn giờ trên TikTok
        try:
            check_covers(settings)
        except Exception as e:
            log(f"  ! Kiểm tra ảnh bìa lỗi: {str(e)[:150]}")


def label_sounds(ch, settings, force=False):
    """Nghe lời nói trong từng âm thanh Yêu thích và tự gắn sản phẩm (Whisper, chạy trên máy)."""
    if not sounds.whisper_ok():
        log("(Chưa có bộ nghe giọng nói faster-whisper → bác tự gắn sản phẩm cho âm thanh ở tab 🎵 Nhạc nền)")
        return
    log(f"Nghe từng âm thanh của kênh «{ch}» để gắn sản phẩm...")
    n = sounds.label_all(ch, settings, log, force=force)
    log(f"✔ Đã nghe {n} âm thanh. Bác vào tab 🎵 Nhạc nền nghe thử và sửa nếu tool gắn sai.")


def run_task(args):
    settings = load_settings()
    ch = args.login or args.sync_showcase or args.sync_sounds or args.label_sounds or args.inspect
    if not get_channel(settings, ch):
        print(f"Không có kênh «{ch}» trong tool")
        return
    try:
        if args.login:
            ok, handle = tiktok.login(settings, ch)
            if ok:
                unblock_channel(ch)
                c = get_channel(settings, ch)
                if handle and not c.get("handle"):
                    c["handle"] = handle
                    save_settings(settings)
                log(f"Đăng nhập kênh «{ch}» OK {('@' + handle) if handle else ''}")
            else:
                log(f"Kênh «{ch}»: chưa đăng nhập được")
        elif args.sync_showcase:
            log(f"Đồng bộ Trưng bày sản phẩm kênh «{ch}»...")
            items = tiktok.sync_showcase(settings, ch, log)
            log(f"✔ Đã lưu {len(items)} sản phẩm của kênh «{ch}»")
        elif args.sync_sounds:
            log(f"Đồng bộ âm thanh Yêu thích kênh «{ch}»...")
            items = tiktok.sync_sounds(settings, ch, log)
            log(f"✔ Đã lưu {len(items)} âm thanh của kênh «{ch}»")
            label_sounds(ch, settings)
        elif args.label_sounds:
            label_sounds(ch, settings, force=True)
        elif args.inspect:
            shots = tiktok.inspect_ui(settings, ch, log)
            log(f"✔ Đã chụp {len(shots)} màn hình vào data/logs/debug")
    except Exception as e:
        log(f"✖ Lỗi: {type(e).__name__}: {e}")
        time.sleep(8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--login")
    ap.add_argument("--sync-showcase")
    ap.add_argument("--sync-sounds")
    ap.add_argument("--label-sounds")
    ap.add_argument("--inspect")
    args = ap.parse_args()
    db.init_db()
    stats.init()
    if args.login or args.sync_showcase or args.sync_sounds or args.label_sounds or args.inspect:
        run_task(args)
        return
    if args.once:
        run_once()
        return
    if not _single_instance():
        print("Bộ đăng tự động ĐANG CHẠY ở cửa sổ khác. Cửa sổ này tự đóng sau 10 giây.")
        time.sleep(10)
        return
    _ALIVE.set()
    from core import desktop as _dk
    _dk.low_priority()  # nhường CPU cho việc khác của bác (Chrome, ffmpeg tool mở cũng nhường theo)
    threading.Thread(target=_beat_forever, name="nhip-tim", daemon=True).start()
    db.reset_stuck()
    stop_flag = DATA_DIR / "stop_runner.flag"
    stop_flag.unlink(missing_ok=True)
    log("=== SonixDangVideo: BỘ ĐĂNG TỰ ĐỘNG ĐÃ BẬT ===")
    while True:
        heartbeat()
        try:
            run_once()
        except Exception as e:
            log(f"! Lỗi vòng lặp: {e}")
        for _ in range(4):
            if stop_flag.exists():  # người dùng bấm "Tắt hẳn tool" trong giao diện
                stop_flag.unlink(missing_ok=True)
                _ALIVE.clear()
                HEARTBEAT_FILE.unlink(missing_ok=True)
                log("=== Đã tắt bộ đăng tự động ===")
                return
            heartbeat()
            time.sleep(5)


_MUTEX = None
_ALIVE = threading.Event()


def _single_instance() -> bool:
    """Chỉ cho 1 bộ đăng chạy. Bật trùng 2 bộ thì 2 bộ tranh 1 trình duyệt kênh -> kênh bị dừng."""
    global _MUTEX
    try:
        if sys.platform == "win32":
            import ctypes
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            _MUTEX = k32.CreateMutexW(None, False, "SonixDangVideo_BoDangTuDong")
            return ctypes.get_last_error() != 183  # 183 = đã có bộ đăng khác giữ
        import fcntl
        _MUTEX = open(DATA_DIR / "runner.lock", "w")
        fcntl.flock(_MUTEX, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False
    except Exception:
        return True


def _beat_forever():
    """Báo 'còn sống' 15 giây/lần kể cả khi đang đăng 1 video lâu (trước đây đăng lâu > 90 giây thì giao diện
    tưởng bộ đăng đã tắt, bật thêm bộ thứ 2)."""
    while _ALIVE.is_set():
        try:
            heartbeat()
        except Exception:
            pass
        time.sleep(15)


if __name__ == "__main__":
    main()
