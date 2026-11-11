"""GIAO DIỆN SonixDangVideo — chạy bằng 2_MO_SonixDangVideo.bat"""
import io
import json
import os
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import analyze as ana  # noqa: E402
from core import caption as cap  # noqa: E402
from core import channels as chs  # noqa: E402
from core import db, facebook  # noqa: E402
from core import products as prod  # noqa: E402
from core import schedule as sch  # noqa: E402
from core.config import (ai_key, channel_plan, APP_NAME, BASE_DIR, DATA_DIR, DEBUG_DIR, FOLDER_ERR, FOLDER_MUSIC,  # noqa: E402
                         FOLDER_TODO, HEARTBEAT_FILE, MODELS, NO_AI, REF_DIR, RUNNER_LOG, SOUNDS_DIR,
                         VIDEO_EXTS, load_settings, profile_dir, save_settings, slug)
from core import desktop  # noqa: E402
from core.video_utils import make_preview  # noqa: E402
from core.tiktok import chrome_exe, is_busy  # noqa: E402
import threading  # noqa: E402
from core import worker  # noqa: E402
from core import sounds as snd  # noqa: E402
from core import covers as cov  # noqa: E402
from core import stats, ui  # noqa: E402
from core import updater as upd  # noqa: E402
from collections import Counter  # noqa: E402
from datetime import date  # noqa: E402

st.set_page_config(page_title=ui.APP_TITLE, layout="wide",
                   page_icon=str(desktop.CUSTOM_PNG) if desktop.CUSTOM_PNG.exists() else None)
db.init_db()
stats.init()
worker.start()  # luồng phân tích ngầm
S = load_settings()
st.markdown(ui.css(S, getattr(getattr(st.context, "theme", None), "type", None)), unsafe_allow_html=True)
FMT = db.TIME_FMT
VIS = {"public": "Mọi người", "friends": "Bạn bè", "private": "Chỉ mình tôi (đăng thử)"}
DISC = {"own_brand": "Thương hiệu của bạn", "branded": "Nội dung định hướng thương hiệu",
        "none": "Không khai báo"}
ITEMS = {it["key"]: it for it in S.get("items", [])}

# ---------- mở từ điện thoại / máy khác: phải bật cho phép + nhập mã PIN ----------
_ip = getattr(st.context, "ip_address", None)
if _ip not in (None, "", "127.0.0.1", "::1", "localhost"):
    if not S.get("lan_access"):
        st.error("Tool đang tắt chế độ mở từ máy khác. Bật ở Cài đặt trên máy tính chạy tool.")
        st.stop()
    if S.get("app_pin") and not st.session_state.get("pin_ok"):
        st.title(f"{APP_NAME}")
        _pin = st.text_input("Nhập mã PIN để mở tool", type="password")
        if _pin and _pin == S["app_pin"]:
            st.session_state["pin_ok"] = True
            st.rerun()
        elif _pin:
            st.error("Sai mã PIN")
        st.stop()



# =============================== tiện ích ===============================
def spawn(args=()):
    """Chạy bộ đăng / việc phụ ở chế độ ẩn (không bật cửa sổ đen)."""
    subprocess.Popen([sys.executable, str(BASE_DIR / "runner.py"), *args], cwd=str(BASE_DIR), env=desktop.env(),
                     creationflags=desktop.no_window_flags(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def shutdown_all():
    desktop.stop_all()
    threading.Timer(2.0, lambda: os._exit(0)).start()


def runner_alive():
    try:
        return time.time() - float(HEARTBEAT_FILE.read_text()) < 90
    except Exception:
        return False


def pick_folder(title="Chọn thư mục"):
    code = ("import tkinter as tk\nfrom tkinter import filedialog\nr=tk.Tk();r.withdraw();r.attributes('-topmost',True)\n"
            f"print(filedialog.askdirectory(title={title!r}))")
    try:
        return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=600,
                              encoding="utf-8").stdout.strip()
    except Exception:
        return ""


def open_folder(path):
    try:
        if sys.platform == "win32":
            os.startfile(path)  # noqa
        else:
            subprocess.Popen(["xdg-open" if sys.platform.startswith("linux") else "open", path])
    except Exception as e:
        st.error(f"Không mở được thư mục: {e}")


def blocked():
    d = DATA_DIR / "blocked"
    out = {}
    if d.exists():
        for f in d.glob("*.txt"):
            a = f.read_text(encoding="utf-8").split("\n", 1)
            out[a[0]] = (a[1] if len(a) > 1 else "", f)
    return out


def favorites(channel):
    f = SOUNDS_DIR / slug(channel) / "favorites.json"
    try:
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
    except Exception:
        return []


def conf_badge(c, item_key, reviewed=0):
    what0 = ITEMS.get(item_key, {}).get("name", "Không có sản phẩm (video kiến thức)") if item_key else \
        "Không có sản phẩm (video kiến thức)"
    if reviewed:
        return f"<span class='sx-cdot g'></span><span class='conf-g'>Bác đã kiểm tra</span> · <b>{what0}</b>"
    if c >= 80:
        cls, ic = "conf-g", "<span class='sx-cdot g'></span>"
    elif c >= 60:
        cls, ic = "conf-y", "<span class='sx-cdot y'></span>"
    else:
        cls, ic = "conf-r", "<span class='sx-cdot r'></span>"
    what = ITEMS.get(item_key, {}).get("name", "Không có sản phẩm (video kiến thức)") if item_key else \
        "Không có sản phẩm (video kiến thức)"
    return f"{ic}<span class='{cls}'>{c}%</span> · <b>{what}</b>"


def needs_check(j):
    return int(j.get("confidence") or 0) < 60 and not int(j.get("reviewed") or 0)


def discard_cb(jid, reason="Bỏ khi duyệt (không nhận diện được / bác chọn bỏ)"):
    """Chuyển video vào VIDEO LỖI (kèm ghi chú) và bỏ khỏi danh sách duyệt."""
    j = db.get_job(jid)
    if j:
        new = chs.move_to(j["video_path"], ROOT, j["channel"], FOLDER_ERR)
        chs.write_error_note(new, reason)
        db.delete_jobs([jid])
    forget(jid)
    st.session_state.pop(k("sel", jid), None)


def default_model():
    return S.get("ai_model") if S.get("ai_model") in MODELS and ai_key(S, S.get("ai_model")) else NO_AI


def reanalyze_cb(jid):
    db.update_job(jid, status="analyzing", ai_model=default_model(), ai_note="", cover_by_user=0)
    worker.start()
    forget(jid)


def golden_tag(ts):
    try:
        return " <span class='gold'>GIỜ VÀNG</span>" if sch.is_golden(datetime.strptime(ts, FMT),
                                                                         S["golden_hours"]) else ""
    except Exception:
        return ""


def make_shortcut(channel):
    return desktop.channel_shortcut(channel, profile_dir(S, channel), chrome_exe())


# ---------- trạng thái ô nhập của từng video ----------
FIELDS = ("it", "pr", "cart", "cap", "tag", "d", "t", "mu", "vis", "rev", "ka")


def k(f, jid):
    return f"{f}_{jid}"


def forget(jid, fields=FIELDS):
    for f in fields:
        st.session_state.pop(k(f, jid), None)


def auto_music_opts():
    """Các lựa chọn nhạc tự động (TikTok tự chọn bài lúc đăng)."""
    from core.tiktok import AUTO_MUSIC
    opts = {f"auto::{kk}": v for kk, v in AUTO_MUSIC.items()}
    for kw in S.get("music_keywords", []):
        if kw.strip():
            opts[f"auto::search:{kw.strip()}"] = f"Tự động: tìm nhạc «{kw.strip()}»"
    return opts


def music_value(j):
    if j.get("music_mode") == "auto" and j.get("music_ref"):
        return "auto::" + j["music_ref"]
    if j.get("music_mode") == "tiktok" and j.get("music_ref"):
        return "tiktok::" + j["music_ref"]
    if j.get("music_mode") == "local" and j.get("music_ref"):
        return "local::" + j["music_ref"]
    return "none"


def init_state(j):
    jid = j["id"]
    ss = st.session_state
    when = datetime.strptime(j["scheduled_at"], FMT) if j.get("scheduled_at") else \
        sch.round5(datetime.now() + timedelta(minutes=30))
    vals = {"it": j.get("item_key") or "", "pr": [p["id"] for p in j["products"]], "cart": j.get("cart_name") or "",
            "cap": j.get("caption") or "", "tag": j.get("hashtags") or "", "d": when.date(), "t": when.time(),
            "mu": music_value(j), "vis": j.get("visibility") or "public", "rev": bool(j.get("reviewed")),
            "ka": j.get("keep_audio") is None or int(j.get("keep_audio")) == 1}
    for f, v in vals.items():
        if k(f, jid) not in ss:
            ss[k(f, jid)] = v


def save(jid, field, f, conv=lambda v: v):
    db.update_job(jid, **{field: conv(st.session_state[k(f, jid)])})


def save_products(jid, channel):
    names = {p["id"]: p.get("name", "") for p in prod.load_showcase(channel)["products"]}
    db.update_job(jid, products=[{"id": i, "name": names.get(i, "")} for i in st.session_state[k("pr", jid)]])


def save_item(jid, channel):
    key = st.session_state[k("it", jid)]
    products, cart = prod.resolve(S, channel, key)
    db.update_job(jid, item_key=key, products=products, cart_name=cart, reviewed=1)
    forget(jid, ("pr", "cart", "rev"))


def save_time(jid):
    dt = datetime.combine(st.session_state[k("d", jid)], st.session_state[k("t", jid)])
    db.update_job(jid, scheduled_at=sch.round5(dt).strftime(FMT))


def save_music(jid):
    v = st.session_state[k("mu", jid)]
    mode, _, ref = v.partition("::")
    db.update_job(jid, music_mode=mode if ref else "none", music_ref=ref, music_by_user=1)


def next_fav(jid, channel):
    """Đổi sang âm thanh Yêu thích khác cùng sản phẩm (xoay vòng)."""
    j = db.get_job(jid) or {}
    item = j.get("item_key") or ""
    refs = [snd.ref_of(f) for f in snd.load_favs(channel)
            if item and item in (f.get("items") or []) and f.get("file") and not f.get("skip")]
    if not refs:
        return
    cur = j.get("music_ref") or ""
    nxt = refs[(refs.index(cur) + 1) % len(refs)] if cur in refs else refs[0]
    db.update_job(jid, music_mode="tiktok", music_ref=nxt, keep_audio=0, music_by_user=0)
    forget(jid, ("mu", "ka"))


def use_theme_cb(ids, theme, msg_key=""):
    """Dùng ảnh theme làm ảnh bìa cho các video (tool chỉnh ảnh về đúng khung từng video)."""
    ok, err = 0, ""
    for i in ids:
        j = db.get_job(i)
        if not j:
            continue
        try:
            db.update_job(i, cover_path=cov.make_cover(j, theme), cover_by_user=1)
            ok += 1
        except Exception as e:
            err = str(e)[:150]
    if msg_key:
        st.session_state[msg_key] = ((f"Đã đặt ảnh bìa «{Path(theme).name}» cho {ok} video." if ok else "")
                                     + (f" Lỗi: {err}" if err else ""))


def auto_theme_cb(ids, channel, msg_key=""):
    """Mỗi video lấy ảnh bìa trùng tên sản phẩm của nó (đi theo sản phẩm: đổi sản phẩm thì bìa đổi theo)."""
    ok, miss, err = 0, [], ""
    for i in ids:
        j = db.get_job(i)
        if not j:
            continue
        t = cov.theme_for_job(S, channel, j, ROOT)
        if not t:
            miss.append(Path(j["video_path"]).name)
            continue
        try:
            follow = bool(cov.default_for(S, channel, j.get("item_key")))  # có bìa mặc định -> bìa đi theo sản phẩm
            db.update_job(i, cover_path=cov.make_cover(j, t), cover_by_user=0 if follow else 1)
            ok += 1
        except Exception as e:
            err = str(e)[:150]
    if msg_key:
        st.session_state[msg_key] = (f"Đã gắn ảnh bìa theo sản phẩm cho {ok} video."
                                     + (f" {len(miss)} video chưa có ảnh trùng sản phẩm (hoặc chưa nhận ra sản phẩm): "
                                        + ", ".join(miss[:5]) + ("…" if len(miss) > 5 else "") if miss else "")
                                     + (f" Lỗi: {err}" if err else ""))


def upload_theme_cb(wkey, nkey, ids, msg_key):
    """Lưu ảnh bác tải lên vào thư mục ẢNH BÌA; tải cho 1 video thì dùng luôn ảnh đó làm bìa."""
    files = st.session_state.get(wkey) or []
    files = files if isinstance(files, list) else [files]
    st.session_state[nkey] = st.session_state.get(nkey, 0) + 1  # ô tải lên trống lại cho lần sau
    if not ROOT:
        st.session_state[msg_key] = "Chưa chọn thư mục gốc (tab Đăng video) nên chưa lưu được ảnh."
        return
    saved, err = [], ""
    for f in files:
        try:
            saved.append(cov.save_upload(ROOT, f.name, f.getvalue()))
        except Exception as e:
            err = f"{f.name}: không đọc được ảnh ({str(e)[:80]})"
    if ids and saved:
        use_theme_cb(ids, saved[-1], msg_key)
        if err:
            st.session_state[msg_key] += f" {err}"
    else:
        st.session_state[msg_key] = ((f"Đã thêm {len(saved)} ảnh vào thư viện ảnh bìa." if saved else "")
                                     + (f" {err}" if err else ""))


def set_cover_cb(jid, idx):
    j = db.get_job(jid)
    db.update_job(jid, cover_path=ana.set_cover(j, idx), reviewed=1, cover_by_user=1)


def save_cover_default(channel, item_key, wkey):
    """Lưu ảnh bìa mặc định cho 1 sản phẩm của kênh."""
    m = S.setdefault("cover_by_product", {}).setdefault(channel, {})
    if st.session_state.get(wkey):
        m[item_key] = st.session_state[wkey]
    else:
        m.pop(item_key, None)
    save_settings(S)


def reset_cover_cb(jid):
    """Video này quay lại dùng bìa mặc định của sản phẩm."""
    db.update_job(jid, cover_by_user=0)


def save_cart_template(channel, jid):
    item_key, cart = st.session_state[k("it", jid)], st.session_state[k("cart", jid)]
    if not item_key:
        return
    cp = S.setdefault("channel_products", {}).setdefault(channel, {})
    m = cp.setdefault(item_key, {})
    m["cart"] = cart[:30]
    if "ids" not in m:
        m["ids"] = prod.mapping(S, channel)[item_key]["ids"]
    save_settings(S)


def plan_channel(channel, jobs, p):
    others = {j["scheduled_at"] for j in db.list_jobs(["draft"], "tiktok", channel)
              if j["id"] not in {x["id"] for x in jobs}}
    times = sch.plan(len(jobs), p["start_dt"], S["golden_hours"], p["per_day"], p["gap_min"], p["start"], p["end"],
                     p["golden_first"], p["golden_per_slot"], taken=db.taken_times(channel) | others)
    for j, t in zip(jobs, times):
        db.update_job(j["id"], scheduled_at=t.strftime(FMT))
        forget(j["id"], ("d", "t"))
    return len(times)


# =============================== THANH BÊN ===============================
@st.cache_data(ttl=6 * 3600, show_spinner=False)
def new_version_cached(repo, channel, token):
    """Hỏi GitHub có bản mới không (6 giờ hỏi 1 lần). Lỗi mạng / chưa có mã đọc thì im lặng."""
    if not token:
        return ""
    try:
        man = json.loads(upd.fetch("manifest.json", {"update_repo": repo, "update_channel": channel,
                                                     "github_token": token}).decode("utf-8"))
        return man.get("version", "") if upd.vtuple(man.get("version", "0")) > upd.vtuple(upd.local_version()) else ""
    except Exception:
        return ""


def item_name(key):
    return ITEMS.get(key, {}).get("name", key) if key else "Không gắn sản phẩm (video kiến thức)"


def save_ui(field, wkey):
    S[field] = st.session_state[wkey]
    save_settings(S)


with st.sidebar:
    st.markdown(ui.brand_html(ui.avatar_uri()), unsafe_allow_html=True)
    st.caption(f"Phiên bản {upd.local_version()}")
    _alive = runner_alive()
    st.markdown(ui.pill_html(_alive), unsafe_allow_html=True)
    if not _alive:
        if st.button("Bật bộ đăng tự động", icon=":material/play_arrow:", width="stretch", type="primary"):
            spawn()
            time.sleep(3)
            st.rerun()
    _dark = ui.mode(S) == "dark"
    if st.button("Chuyển giao diện sáng" if _dark else "Chuyển giao diện tối", width="stretch", key="ui_toggle",
                 icon=":material/light_mode:" if _dark else ":material/dark_mode:"):
        S["ui_theme"] = "light" if _dark else "dark"
        save_settings(S)
        st.rerun()
    for ch, (msg, f) in blocked().items():
        st.error(f"Kênh **{ch}** đang dừng:\n\n{msg}")
        if st.button(f"Đã xử lý xong, chạy tiếp «{ch}»", key=f"unb_{slug(ch)}"):
            f.unlink()
            st.rerun()
    def _ana_status():
        left = sum(worker.pending_counts().values())
        prev = st.session_state.get("_ana_left", 0)
        st.session_state["_ana_left"] = left
        if left:
            st.info(f"**Đang phân tích ngầm: còn {left} video.** Tắt cửa sổ cũng được, mở lại tool sẽ "
                    f"phân tích tiếp.")
            with st.popover("Dừng phân tích", width="stretch"):
                st.write("Bỏ các video chưa phân tích khỏi hàng (file vẫn nằm trong CHƯA UP, quét lại được).")
                if st.button("Dừng & bỏ khỏi hàng", key="ana_stop", type="primary"):
                    db.delete_jobs([j["id"] for j in db.list_jobs(["analyzing"], "tiktok")])
                    st.rerun(scope="app")
        elif prev:
            st.rerun(scope="app")  # vừa phân tích xong -> tải lại để hiện video ở tab Duyệt

    _live = bool(worker.pending_counts())
    st.fragment(run_every=3 if _live else None)(_ana_status)()
    _live = {"draft": [], "pending": []}
    for _j in db.list_jobs(["draft", "pending"]):
        _live[_j["status"]].append(_j)
    _today = stats.day_detail(date.today().isoformat())
    _wd = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ nhật"][date.today().weekday()]
    st.markdown(f'<div class="sx-day"><div><b>Hôm nay</b><div class="sx-note">{_wd}, {date.today():%d/%m} · '
                f'hẹn giờ và lỗi tính từ 0:00</div></div></div>', unsafe_allow_html=True)
    st.markdown(ui.tiles_html([("Chờ duyệt", len(_live["draft"]), "var(--sx-blue)"),
                               ("Chờ đăng", len(_live["pending"]), "var(--sx-purple)"),
                               ("Đã hẹn giờ", _today["hen_gio"]["total"], "var(--sx-cyan)"),
                               ("Lỗi", _today["loi"]["total"], "var(--sx-danger)")]), unsafe_allow_html=True)
    _pick = st.pills("Xem chi tiết", ["Chờ duyệt", "Chờ đăng", "Đã hẹn giờ", "Lỗi"], key="sx_pick",
                     help="Bấm 1 mục để xem số video theo từng kênh hoặc từng sản phẩm")
    if _pick:
        _by = st.radio("Xem theo", ["Kênh", "Sản phẩm"], horizontal=True, key="sx_by", label_visibility="collapsed")
        if _pick in ("Chờ duyệt", "Chờ đăng"):
            _cnt = Counter(_j["channel"] if _by == "Kênh" else item_name(_j.get("item_key"))
                           for _j in _live["draft" if _pick == "Chờ duyệt" else "pending"])
        else:
            _d = _today["hen_gio" if _pick == "Đã hẹn giờ" else "loi"]
            _cnt = Counter(_d["channels"]) if _by == "Kênh" else Counter()
            if _by != "Kênh":
                for _kk, _v in _d["items"].items():
                    _cnt[item_name(_kk)] += _v
        st.markdown(ui.table_html(_by, sorted(_cnt.items(), key=lambda x: -x[1])), unsafe_allow_html=True)
    st.caption("Các ngày trước: xem ở tab Tổng hợp.")
    _newv = new_version_cached(S.get("update_repo") or upd.DEFAULT_REPO, S.get("update_channel") or "main",
                               (S.get("github_token") or "").strip())
    if _newv:
        st.info(f"Có bản mới **{_newv}** · vào Cài đặt → Cập nhật để cài.")
    st.markdown("**Giờ vàng:** " + " · ".join(f"<span class='gold'>{g}</span>" for g in S["golden_hours"]),
                unsafe_allow_html=True)
    st.caption("Lưu ý: tool đang đăng kênh nào thì **đừng mở trình duyệt của kênh đó** (biểu tượng ngoài màn hình), "
               "mở trùng là kênh bị dừng.")
    if S.get("lan_access"):
        st.info(f"Mở trên điện thoại (cùng Wi-Fi):\n\nhttp://{desktop.local_ip()}:{desktop.PORT}")
    with st.popover("Tắt hẳn tool", width="stretch"):
        st.write("Tắt bộ đăng tự động và giao diện. Video đã **hẹn giờ trên TikTok** vẫn tự đăng. "
                 "Video **chưa tải lên** sẽ không đăng cho tới khi mở lại tool.")
        if st.button("Tắt luôn", type="primary"):
            shutdown_all()
            st.success("Đã tắt. Đóng cửa sổ này. Muốn mở lại: bấm biểu tượng Sonix Đăng Video ngoài màn hình.")
            st.stop()

    components.html(ui.theme_script(S), height=0)

_t = st.tabs(["Đăng video", "Duyệt & xác nhận", "Hàng chờ", "Tổng hợp", "Kênh & sản phẩm", "Nhạc nền", "Cài đặt",
              "Facebook", "Nhật ký"])
tabs = [_t[0], _t[1], _t[2], _t[4], _t[5], _t[6], _t[7], _t[8]]
TAB_TONGHOP = _t[3]
CHANNELS = [c for c in S.get("channels", []) if c.get("enabled", True)]
ROOT = S.get("root_folder", "")
READY = bool(ROOT and Path(ROOT).is_dir() and CHANNELS)

# =============================== ĐĂNG VIDEO ===============================
with tabs[0]:
    if not READY:
        st.header("Chào bác! Cài đặt ban đầu (làm 1 lần)")
        st.markdown("""
1. **Chọn thư mục gốc** chứa video, ví dụ `D:\\VIDEO_TIKTOK`.
2. **Nhập các kênh TikTok** sẽ đăng. Tên kênh = tên thư mục con. Tool tự tạo:
```
D:\\VIDEO_TIKTOK\\
 ├─ NHẠC NỀN\\
 └─ Tên kênh\\  ├─ CHƯA UP\\   ← bỏ video chờ đăng vào đây
               ├─ ĐÃ UP\\     ← đăng xong tool tự chuyển vào
               └─ VIDEO LỖI\\ ← đăng lỗi tool chuyển vào (kèm file .LOI.txt ghi lý do)
```
3. Qua tab **Kênh & sản phẩm**: đăng nhập TikTok cho từng kênh, đồng bộ Trưng bày sản phẩm.
4. (Nên có) Dán **Claude API key** ở tab Cài đặt để AI nhận diện sản phẩm + viết caption.""")
        c1, c2 = st.columns([4, 1])
        root_in = c1.text_input("Thư mục gốc", ROOT or "D:\\VIDEO_TIKTOK")
        c2.write("")
        c2.write("")
        if c2.button("Chọn", key="pick_root0"):
            f = pick_folder("Chọn thư mục gốc chứa video")
            if f:
                S["root_folder"] = f
                save_settings(S)
                st.rerun()
        ch_df = st.data_editor(pd.DataFrame(S.get("channels") or [{"name": "", "handle": "", "enabled": True}],
                                            columns=["name", "handle", "enabled"]),
                               num_rows="dynamic", hide_index=True, width="stretch", key="setup_ch",
                               column_config={"name": "Tên kênh (= tên thư mục)", "handle": "@ tên TikTok (vd sonphanthuoc)",
                                              "enabled": st.column_config.CheckboxColumn("Dùng", default=True)})
        if st.button("Lưu & tạo thư mục", type="primary"):
            chans = [{"name": str(r["name"]).strip(), "handle": str(r.get("handle") or "").strip().lstrip("@"),
                      "enabled": bool(r.get("enabled", True)), "profile_dir": ""}
                     for r in ch_df.fillna("").to_dict("records") if str(r["name"]).strip()]
            if not root_in.strip() or not chans:
                st.error("Cần có thư mục gốc và ít nhất 1 kênh.")
            else:
                try:
                    Path(root_in).mkdir(parents=True, exist_ok=True)
                    S.update(root_folder=root_in.strip(), channels=chans)
                    save_settings(S)
                    made = chs.ensure_structure(root_in, chans)
                    st.success(f"Đã lưu! Tạo mới {len(made)} thư mục.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Không tạo được thư mục: {e}")
    else:
        st.header("Bước 1 · Chọn kênh cần đăng")
        active = db.active_paths()
        counts = {}
        for c in CHANNELS:
            vids = [v for v in chs.todo_videos(ROOT, c["name"]) if str(v) not in active]
            counts[c["name"]] = vids
        anc = worker.pending_counts()
        sel = st.multiselect("Kênh", [c["name"] for c in CHANNELS], default=[c["name"] for c in CHANNELS],
                             format_func=lambda n: f"{n}  ({len(counts[n])} video mới trong {FOLDER_TODO}"
                             + (f", {anc[n]} đang phân tích" if anc.get(n) else "") + ")")
        cols = st.columns(max(1, len(sel)))
        for i, n in enumerate(sel):
            with cols[i]:
                st.markdown(f"**{n}** · {len(counts[n])} video mới"
                            + (f" · {anc[n]} video đang phân tích" if anc.get(n) else ""))
                if st.button("Mở thư mục CHƯA UP", key=f"open_{slug(n)}"):
                    open_folder(str(chs.channel_dir(ROOT, n) / FOLDER_TODO))
                if not prod.load_showcase(n)["products"]:
                    st.warning("Chưa đồng bộ Trưng bày sản phẩm → chưa gắn giỏ tự động được. Vào tab Kênh & sản phẩm.")
        st.header("Bước 2 · Chọn AI để nhận diện sản phẩm & viết caption")
        opts = list(MODELS) + [NO_AI]
        default = default_model()
        model = st.radio("Mức AI (chọn mỗi lần đăng)", opts, index=opts.index(default), format_func=lambda m: MODELS.get(
            m, "Không dùng AI · nhận diện theo TÊN FILE, caption mẫu (miễn phí)"))
        has_key = model == NO_AI or bool(ai_key(S, model))
        if not has_key:
            st.error(("Chưa có Gemini API key" if model.startswith("gemini") else "Chưa có Claude API key")
                     + " → vào tab Cài đặt dán key, hoặc chọn mức khác.")
        elif model.startswith("gemini"):
            st.caption("Gemini miễn phí: Google giới hạn số lượt mỗi phút/mỗi ngày và được dùng ảnh gửi lên để "
                       "cải thiện sản phẩm của họ. Hết lượt thì video đó đoán theo tên file, bấm Phân tích lại hôm sau.")
        with st.expander("Tuỳ chọn mặc định cho đợt này"):
            o1, o2, o3 = st.columns(3)
            amo0 = {"none": "Không thêm nhạc", **auto_music_opts()}
            dm = S.get("default_music", "auto::smart")
            mus0 = st.selectbox("Nhạc nền (TikTok tự chọn bài lúc đăng)", list(amo0), format_func=amo0.get,
                                index=list(amo0).index(dm) if dm in amo0 else 0,
                                help="Đổi từng video được ở tab Duyệt. Video có giỏ nên dùng nhạc thương mại.")
            vis0 = o1.selectbox("Người xem", list(VIS), format_func=VIS.get,
                                index=list(VIS).index(S.get("default_visibility", "public")))
            ai0 = o2.checkbox("Bật nhãn 'Nội dung do AI tạo'")
            ka0 = o2.checkbox("Giữ âm thanh gốc của video", bool(S.get("default_keep_audio", False)),
                              help="Bỏ tick = tắt tiếng gốc, video chỉ còn nhạc/âm thanh bác chọn")
            disc0 = o3.selectbox("Khai báo nội dung bài đăng", list(DISC), format_func=DISC.get,
                                 index=list(DISC).index(S.get("default_disclosure", "own_brand")))
        total = sum(len(counts[n]) for n in sel)
        if st.button(f"Bước 3 · Phân tích {total} video", type="primary",
                     disabled=total == 0 or (model != NO_AI and not has_key)):
            n_new = 0
            for n in sel:
                for v in counts[n]:
                    db.add_job(platform="tiktok", channel=n, video_path=str(v), status="analyzing", ai_model=model,
                               keep_audio=int(ka0),
                               visibility=vis0, ai_content=int(ai0), disclosure=disc0,
                               music_mode=mus0.partition("::")[0] if mus0 != "none" else "none",
                               music_ref=mus0.partition("::")[2])
                    n_new += 1
            worker.start()
            st.session_state["_ana_msg"] = n_new
            st.rerun()
        if st.session_state.pop("_ana_msg", 0):
            st.success("Đã đưa video vào phân tích **chạy ngầm**. Tiến độ hiện ở thanh bên trái. Bác cứ làm việc "
                       "khác hoặc tắt cửa sổ cũng được. Xong tool tự xếp lịch giờ vàng, video hiện ở tab "
                       "**Duyệt & xác nhận**.")

# =============================== DUYỆT ===============================
with tabs[1]:
    drafts = db.list_jobs(["draft"], "tiktok")
    if not drafts:
        st.info("Chưa có video chờ duyệt. Qua tab Đăng video để phân tích.")
    if default_model() == NO_AI:
        st.info("Đang để 'Không dùng AI' (hoặc chưa có API key) nên tool chỉ đoán sản phẩm theo **tên file** → mọi video đều chấm đỏ, bác bấm "
                "**Xem video** rồi chọn sản phẩm cho đúng. Có API key thì AI xem hình trong video: chấm xanh = đọc rõ chữ "
                "trên nhãn, chấm vàng = nhận ra qua màu/hình dáng (vẫn nên xem lại).")
    st.markdown("**Màu độ chắc chắn:** <span class='sx-cdot g'></span>≥80% · <span class='sx-cdot y'></span>60-79% · "
                "<span class='sx-cdot r'></span>dưới 60% — video chấm đỏ phải tick "
                "*'Tôi đã kiểm tra'* mới cho đăng. **Giờ vàng:** " +
                " · ".join(f"<span class='gold'>{g}</span>" for g in S["golden_hours"]), unsafe_allow_html=True)
    for chname in sorted({j["channel"] for j in drafts}):
        jobs = [j for j in drafts if j["channel"] == chname]
        for _i in snd.auto_assign(chname, S, jobs):  # gắn sẵn âm thanh Yêu thích đúng sản phẩm
            forget(_i, ("mu", "ka"))
        show_all = prod.load_showcase(chname)["products"]
        show = prod.usable(show_all, S)
        smap = {p["id"]: p for p in show_all}
        bad_ids = {p["id"] for p in show_all} - {p["id"] for p in show}
        favs = [f for f in snd.load_favs(chname) if f.get("title") and not f.get("skip")]
        themes = [str(p) for p in cov.theme_files(ROOT)]  # ảnh bìa có sẵn trong thư mục ẢNH BÌA
        if cov.undo_auto_defaults(S):  # bỏ bìa mặc định bản 2.3.1 tự đặt: mặc định là khung hình trong video
            save_settings(S)
        cov.auto_assign(chname, S, jobs, ROOT)  # video chưa tự chọn bìa -> dùng bìa mặc định của sản phẩm
        amo = auto_music_opts()
        fav_opts = list(dict.fromkeys("tiktok::" + snd.ref_of(f) for f in favs))  # bỏ trùng tên
        fav_items = {"tiktok::" + snd.ref_of(f): f.get("items") or [] for f in favs}
        local_opts = [f"local::{m}" for m in chs.music_files(ROOT)]
        mus_opts = ["none"] + list(amo) + fav_opts + local_opts
        mus_fmt = {"none": "Không thêm nhạc", **amo}
        for f in favs:
            tag = ", ".join(ITEMS.get(x, {}).get("name", x) for x in (f.get("items") or []))
            mus_fmt["tiktok::" + snd.ref_of(f)] = (f"Yêu thích · {f['title']} · {f.get('artist', '')} {f.get('duration', '')}"
                                                   + (f"  [{tag}]" if tag else ""))
        for m in chs.music_files(ROOT):
            mus_fmt[f"local::{m}"] = f"Trên máy: {m.name}"
        favfile = {"tiktok::" + snd.ref_of(f): f.get("file") for f in favs}
        favfile.update({f"tiktok::{f['title']}": f.get("file") for f in favs})  # video cũ chọn theo tên

        st.divider()
        st.header(f"{chname} · {len(jobs)} video")
        if not show:
            st.warning("Kênh này chưa đồng bộ Trưng bày sản phẩm → chưa có ID để gắn giỏ. Vào tab Kênh & sản phẩm bấm "
                       "'Đồng bộ Trưng bày' rồi quay lại chọn lại sản phẩm.")
        sel_ids = [j["id"] for j in jobs if st.session_state.get(k("sel", j["id"]))]

        # ----- Xếp lịch -----
        with st.expander("Xếp lịch tự động (ưu tiên giờ vàng)", expanded=False):
            p = channel_plan(S, chname)
            st.caption(f"Cài đặt này **lưu riêng cho kênh {chname}**: lần sau tự điền sẵn, và tool dùng nó để tự xếp "
                       f"lịch sau khi phân tích. Giờ vàng ngoài khung 'Đăng từ - Đến' sẽ không dùng.")
            a1, a2, a3, a4 = st.columns(4)
            sd = a1.date_input("Từ ngày", datetime.now().date(), key=f"pl_d_{slug(chname)}", format="DD/MM/YYYY")
            stt = a2.time_input("Ngày đầu: bắt đầu lúc", sch.round5(datetime.now() + timedelta(minutes=30)).time(),
                                key=f"pl_t_{slug(chname)}", step=300)
            per_day = a3.number_input("Số video/ngày", 1, 30, int(p["per_day"]), key=f"pl_n_{slug(chname)}")
            gap = a4.number_input("Cách nhau ít nhất (phút)", 5, 1440, int(p["gap_min"]), 5, key=f"pl_g_{slug(chname)}")
            b1, b2, b3, b4 = st.columns(4)
            w0 = b1.text_input("Mỗi ngày chỉ đăng từ (giờ)", p["start"], key=f"pl_w0_{slug(chname)}")
            w1 = b2.text_input("Mỗi ngày đăng đến (giờ)", p["end"], key=f"pl_w1_{slug(chname)}")
            gf = b3.checkbox("Ưu tiên giờ vàng", p["golden_first"], key=f"pl_gf_{slug(chname)}")
            gps = b4.number_input("Số video mỗi khung giờ vàng", 1, 5, int(p["golden_per_slot"]),
                                  key=f"pl_gp_{slug(chname)}", help="Tăng lên để dồn nhiều video vào giờ vàng")
            scope = st.radio("Áp dụng cho", ["all", "sel"], horizontal=True, key=f"pl_sc_{slug(chname)}",
                             format_func={"all": "Tất cả video kênh này", "sel": f"Video đang chọn ({len(sel_ids)})"}.get)
            try:
                bad_w = (datetime.strptime(w0.strip(), "%H:%M") >= datetime.strptime(w1.strip(), "%H:%M")
                         and "giờ bắt đầu phải nhỏ hơn giờ kết thúc")
            except ValueError:
                bad_w = "giờ phải ghi dạng HH:MM, ví dụ 14:50"
            if bad_w:
                st.error(f"Khung 'Đăng từ - Đến' chưa đúng: {bad_w}.")
            else:
                st.caption(f"Ngày {sd:%d/%m} bắt đầu lúc **{stt:%H:%M}** · các ngày sau đăng từ **{w0.strip()}** "
                           f"đến **{w1.strip()}**.")
                try:
                    if stt > datetime.strptime(w0.strip(), "%H:%M").time():
                        st.warning(f"Ngày đầu bắt đầu {stt:%H:%M} nhưng các ngày sau lại đăng từ {w0.strip()}. "
                                   f"Muốn ngày nào cũng từ {stt:%H:%M} thì sửa ô 'Mỗi ngày chỉ đăng từ' thành "
                                   f"{stt:%H:%M}.")
                except ValueError:
                    pass
            if st.button("Xếp lịch", key=f"pl_go_{slug(chname)}", disabled=bool(bad_w)):
                target = jobs if scope == "all" else [j for j in jobs if j["id"] in sel_ids]
                n = plan_channel(chname, target, {"start_dt": datetime.combine(sd, stt), "per_day": per_day,
                                                  "gap_min": gap, "start": w0, "end": w1, "golden_first": gf,
                                                  "golden_per_slot": gps})
                S.setdefault("plan_by_channel", {})[chname] = dict(
                    per_day=int(per_day), gap_min=int(gap), start=w0.strip(), end=w1.strip(), golden_first=bool(gf),
                    golden_per_slot=int(gps))
                save_settings(S)
                st.success(f"Đã xếp {n} video.")
                st.rerun()
            rows = {}
            for j in jobs:
                if j["scheduled_at"]:
                    d, t = j["scheduled_at"].split(" ")
                    rows.setdefault(d, []).append(t + (" (giờ vàng)" if golden_tag(j["scheduled_at"]) else ""))
            if rows:
                st.dataframe(pd.DataFrame([{"Ngày": datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m"),
                                            "Số video": len(v), "Giờ đăng": "  ·  ".join(sorted(v))}
                                           for d, v in sorted(rows.items())]), hide_index=True, width="stretch")

        # ----- Thao tác hàng loạt -----
        def _sel_all(js=jobs, v=True):
            for j in js:
                st.session_state[k("sel", j["id"])] = v

        def _sel_red(js=jobs):
            for j in js:
                st.session_state[k("sel", j["id"])] = needs_check(j)

        def _bulk(ids, chn=chname, **f):
            for i in ids:
                db.update_job(i, **f)
                forget(i)

        def _bulk_item(ids, key, chn=chname):
            products, cart = prod.resolve(S, chn, key)
            _bulk(ids, item_key=key, products=products, cart_name=cart, reviewed=1)

        def _bulk_keep(ids, which):
            for i in ids:
                j = db.get_job(i)
                if which == "all":
                    products, _ = prod.resolve(S, j["channel"], j["item_key"])
                else:
                    products = j["products"][which:which + 1] or j["products"][:1]
                db.update_job(i, products=products)
                forget(i)

        with st.container(border=True, key=f"card_bulk_{slug(chname)}"):
            st.markdown(f"**Thao tác hàng loạt** · đang chọn **{len(sel_ids)}** video")
            r1 = st.columns(5)
            r1[4].button("Đánh dấu đã kiểm tra", key=f"rv_{slug(chname)}", disabled=not sel_ids,
                         on_click=lambda ids=sel_ids: _bulk(ids, reviewed=1),
                         help="Cho các video đang chọn: bác đã xem và xác nhận sản phẩm đúng")
            r1[0].button("Chọn tất cả", key=f"sa_{slug(chname)}", on_click=_sel_all)
            r1[1].button("Bỏ chọn", key=f"sn_{slug(chname)}", on_click=_sel_all, kwargs={"v": False})
            r1[2].button("Chọn video cần kiểm tra", key=f"sr_{slug(chname)}", on_click=_sel_red)
            with r1[3].popover("Bỏ video đang chọn", disabled=not sel_ids):
                st.write(f"Bỏ **{len(sel_ids)}** video đang chọn?")
                st.button("Chuyển vào VIDEO LỖI", key=f"delx_{slug(chname)}", type="primary",
                          on_click=lambda ids=sel_ids: [discard_cb(i) for i in ids])
                st.button("Chỉ bỏ khỏi danh sách (để lại CHƯA UP)", key=f"del_{slug(chname)}",
                          on_click=lambda ids=sel_ids: (db.delete_jobs(ids), [forget(i) for i in ids]))
            r2 = st.columns([2, 1, 1, 1, 1])
            bi = r2[0].selectbox("Sản phẩm", [""] + list(ITEMS), key=f"bi_{slug(chname)}",
                                 format_func=lambda x: ITEMS[x]["name"] if x else "— Không gắn giỏ (video kiến thức) —")
            r2[1].button("Gắn cho video chọn", key=f"bia_{slug(chname)}", disabled=not sel_ids,
                         on_click=_bulk_item, args=(sel_ids, bi))
            r2[2].button("Chỉ giữ giỏ 1", key=f"k1_{slug(chname)}", disabled=not sel_ids,
                         on_click=_bulk_keep, args=(sel_ids, 0), help="Bỏ sản phẩm trùng thứ 2")
            r2[3].button("Chỉ giữ giỏ 2", key=f"k2_{slug(chname)}", disabled=not sel_ids,
                         on_click=_bulk_keep, args=(sel_ids, 1))
            r2[4].button("Gắn đủ cả 2 giỏ", key=f"ka_{slug(chname)}", disabled=not sel_ids,
                         on_click=_bulk_keep, args=(sel_ids, "all"))
            r3 = st.columns([2, 1, 2, 1])
            bm = r3[0].selectbox("Nhạc nền", mus_opts, key=f"bm_{slug(chname)}", format_func=lambda x: mus_fmt.get(x, x))
            r3[1].button("Áp dụng nhạc", key=f"bma_{slug(chname)}", disabled=not sel_ids, on_click=lambda ids=sel_ids, v=bm: _bulk(
                ids, music_mode=v.partition("::")[0] if v != "none" else "none", music_ref=v.partition("::")[2],
                music_by_user=1))
            bv = r3[2].selectbox("Người xem", list(VIS), key=f"bv_{slug(chname)}", format_func=VIS.get)
            r3[3].button("Áp dụng người xem", key=f"bva_{slug(chname)}", disabled=not sel_ids,
                         on_click=lambda ids=sel_ids, v=bv: _bulk(ids, visibility=v))
            rca = st.columns([2, 3])
            rca[0].button("Tự gắn ảnh bìa theo sản phẩm", key=f"bthauto_{slug(chname)}", type="primary",
                          disabled=not (sel_ids and themes),
                          on_click=lambda ids=sel_ids, c_=chname, m=f"thmsg_{slug(chname)}": auto_theme_cb(ids, c_, m),
                          help="Mỗi video đang chọn lấy ảnh trong thư mục ẢNH BÌA trùng tên sản phẩm AI nhận ra "
                               "(vd video Kích rễ TC01 → Kích rễ TC01.png)")
            rca[1].caption("Tool so tên ảnh với tên sản phẩm của từng video. Đặt tên ảnh theo tên sản phẩm là được, "
                           "ví dụ «Kích rễ TC01.png», «Đạm cá amino.png».")
            rcv = st.columns([2, 1, 2])
            bth = rcv[0].selectbox("Ảnh bìa có sẵn (theme)", themes or [""], key=f"bth_{slug(chname)}",
                                   format_func=lambda x: Path(x).name if x else "(chưa có ảnh, tải lên ở ô bên phải)")
            rcv[1].button("Áp dụng ảnh bìa", key=f"btha_{slug(chname)}", disabled=not (sel_ids and themes),
                          on_click=lambda ids=sel_ids, v=bth, m=f"thmsg_{slug(chname)}": use_theme_cb(ids, v, m),
                          help="Video đang chọn dùng ảnh này làm ảnh bìa (tool tự chỉnh về đúng khung video)")
            tnk = f"thn_{slug(chname)}"
            twk = f"thup_{slug(chname)}_{st.session_state.get(tnk, 0)}"
            rcv[2].file_uploader("Thêm ảnh theme vào thư viện (jpg, png, webp)", type=["jpg", "jpeg", "png", "webp"],
                                 accept_multiple_files=True, key=twk, on_change=upload_theme_cb,
                                 args=(twk, tnk, [], f"thmsg_{slug(chname)}"))
            thm = st.session_state.pop(f"thmsg_{slug(chname)}", None)
            if thm:
                st.info(thm)
            if ROOT:
                st.caption(f"Ảnh theme nằm ở thư mục **{cov.cover_dir(ROOT)}** (bỏ ảnh vào đó cũng được). Ảnh lệch "
                           "khung video thì tool đặt nguyên ảnh ở giữa trên nền mờ, không cắt mất chữ.")
            cbp = (S.get("cover_by_product") or {}).get(chname) or {}
            with st.expander(f"Ảnh bìa mặc định theo sản phẩm · đã đặt {sum(1 for v in cbp.values() if v)} sản phẩm "
                             "(1 ảnh dùng cho mọi video của sản phẩm đó)"):
                if not themes:
                    st.caption("Thư viện chưa có ảnh: tải ảnh lên ở ô Ảnh bìa có sẵn phía trên trước.")
                names = [""] + [Path(x).name for x in themes]
                for it in S.get("items", []):
                    cur = cbp.get(it["key"], "")
                    opts = names + ([cur] if cur and cur not in names else [])
                    cc = st.columns([1.4, 2.4, 0.6])
                    cc[0].markdown(f"**{it['name']}**")
                    kk = f"cbp_{slug(chname)}_{it['key']}"
                    cc[1].selectbox("Ảnh bìa mặc định", opts, index=opts.index(cur), key=kk,
                                    format_func=lambda x: x or "— Không đặt (dùng khung hình AI chọn)",
                                    label_visibility="collapsed", on_change=save_cover_default,
                                    args=(chname, it["key"], kk))
                    if cur and (cov.cover_dir(ROOT) / cur).exists():
                        try:
                            cc[2].image(cov.thumb(cov.cover_dir(ROOT) / cur), width=46)
                        except Exception:
                            pass
                st.caption("Đặt xong là các video của sản phẩm đó (bác chưa tự chọn bìa) tự đổi sang ảnh này; đổi sản phẩm "
                           "thì bìa đổi theo. Video bác đã tự chọn bìa thì giữ nguyên, muốn dùng lại bìa mặc định thì bấm "
                           "trong Đổi ảnh bìa của video đó. Lưu riêng cho từng kênh.")
            def _bulk_fav(ids, chn=chname):
                used, ok, miss = {}, 0, 0
                for i in ids:
                    jj = db.get_job(i)
                    f = snd.pick_for(chn, (jj or {}).get("item_key") or "", used)
                    if f:
                        db.update_job(i, music_mode="tiktok", music_ref=snd.ref_of(f), keep_audio=0, music_by_user=0)
                        ok += 1
                    else:
                        miss += 1
                    forget(i)
                st.session_state[f"favmsg_{slug(chn)}"] = (ok, miss)

            rf = st.columns([2, 3])
            rf[0].button("Gán âm thanh Yêu thích đúng sản phẩm", key=f"favb_{slug(chname)}", disabled=not sel_ids,
                         on_click=_bulk_fav, args=(sel_ids,),
                         help="Mỗi video lấy 1 âm thanh Yêu thích đã gắn đúng sản phẩm (xoay vòng, không trùng) và TẮT "
                              "âm gốc. Nghe thử ở từng video bên dưới rồi mới Xác nhận đăng.")
            fm = st.session_state.pop(f"favmsg_{slug(chname)}", None)
            if fm:
                rf[1].success(f"Đã gán {fm[0]} video." + (f" {fm[1]} video chưa có âm thanh Yêu thích đúng sản phẩm "
                                                         f"(gắn thêm ở tab Nhạc nền)." if fm[1] else ""))
            else:
                n_lab = sum(1 for f in favs if f.get("items"))
                rf[1].caption(f"Kênh này có {len(favs)} âm thanh Yêu thích, {n_lab} cái đã gắn sản phẩm (tab Nhạc nền).")
            r5 = st.columns([1, 1, 3])
            r5[0].button("Tắt âm gốc", key=f"mute_{slug(chname)}", disabled=not sel_ids,
                         on_click=lambda ids=sel_ids: _bulk(ids, keep_audio=0),
                         help="Video đang chọn: bỏ tiếng gốc, chỉ còn nhạc/âm thanh đã chọn")
            r5[1].button("Giữ âm gốc", key=f"unmute_{slug(chname)}", disabled=not sel_ids,
                         on_click=lambda ids=sel_ids: _bulk(ids, keep_audio=1))
            n_mute = sum(1 for j in jobs if j.get("keep_audio") is not None and int(j["keep_audio"]) == 0)
            r5[2].caption(f"{n_mute}/{len(jobs)} video đang tắt âm gốc. Tắt âm gốc thì nhạc TikTok để to bình thường.")
            def _redo_cap(ids):
                for i in ids:
                    db.update_job(i, status="analyzing", redo_caption=1, ai_model=default_model())
                    forget(i)
                worker.start()

            r4 = st.columns([2, 2, 3])
            r4[1].button("Viết lại caption", key=f"rcap_{slug(chname)}", disabled=not sel_ids,
                         on_click=_redo_cap, args=(sel_ids,),
                         help="AI viết lại caption theo Hướng dẫn trong Cài đặt. Giữ nguyên sản phẩm, ảnh bìa, giờ đăng.")
            r4[0].button("Phân tích lại video đang chọn", key=f"rax_{slug(chname)}", disabled=not sel_ids,
                         on_click=lambda ids=sel_ids: [reanalyze_cb(i) for i in ids],
                         help="Đưa vào phân tích ngầm lại (AI nhìn hình nhận sản phẩm, gắn giỏ, viết caption). "
                              "Giữ nguyên giờ đăng đã xếp.")
            r4[2].caption("Mức AI khi phân tích lại: **" + MODELS.get(default_model(), "Không dùng AI (theo tên file)")
                          + "** · đổi ở Cài đặt → Mức AI mặc định")

        # ----- Từng video -----
        per_page = 10
        pages = max(1, (len(jobs) + per_page - 1) // per_page)
        pg = st.selectbox("Trang", range(1, pages + 1), key=f"pg_{slug(chname)}") if pages > 1 else 1
        for j in jobs[(pg - 1) * per_page: pg * per_page]:
            jid = j["id"]
            if bad_ids and any(p["id"] in bad_ids for p in j["products"]):
                j["products"] = [p for p in j["products"] if p["id"] not in bad_ids]
                db.update_job(jid, products=j["products"])
                forget(jid, ("pr",))
            init_state(j)
            with st.container(border=True, key=f"card_{jid}"):
                c0, c1, c2, c3 = st.columns([0.3, 1.25, 2.3, 2.6])
                c0.checkbox("chọn", key=k("sel", jid), label_visibility="collapsed")
                with c1:
                    if j.get("cover_path") and Path(j["cover_path"]).exists():
                        st.image(j["cover_path"], width=170)
                        if cov.theme_name(j["cover_path"]):
                            st.caption(("Bìa theme: " if int(j.get("cover_by_user") or 0) else "Bìa mặc định: ")
                                       + cov.theme_name(j["cover_path"]))
                    thm_j = st.session_state.pop(f"thmsg_{jid}", None)
                    if thm_j:
                        st.info(thm_j)
                    with st.popover("Đổi ảnh bìa"):
                        st.caption("Chọn khung thấy rõ sản phẩm nhất / có người cầm sản phẩm")
                        fr = j["frames"]
                        for r0 in range(0, len(fr), 5):
                            cc = st.columns(5)
                            for i in range(r0, min(r0 + 5, len(fr))):
                                with cc[i - r0]:
                                    if Path(fr[i]["thumb"]).exists():
                                        st.image(fr[i]["thumb"], width=90)
                                    st.button("Chọn", key=f"cv_{jid}_{i}", on_click=set_cover_cb, args=(jid, i))
                        st.markdown("**Hoặc dùng ảnh bìa có sẵn (theme)**")
                        if themes:
                            tc = st.columns([2, 1])
                            tsel = tc[0].selectbox("Ảnh theme", themes, key=f"th_{jid}", format_func=lambda x: Path(x).name,
                                                   label_visibility="collapsed")
                            tc[0].button("Dùng ảnh này", key=f"thb_{jid}", on_click=use_theme_cb,
                                         args=([jid], tsel, f"thmsg_{jid}"))
                            try:
                                tc[1].image(cov.thumb(tsel), width=80)
                            except Exception:
                                tc[1].caption("(không xem trước được)")
                        tnk = f"thn_{jid}"
                        twk = f"thup_{jid}_{st.session_state.get(tnk, 0)}"
                        st.file_uploader("Tải ảnh lên, dùng luôn cho video này", type=["jpg", "jpeg", "png", "webp"],
                                         key=twk, on_change=upload_theme_cb, args=(twk, tnk, [jid], f"thmsg_{jid}"))
                        dft = cov.default_for(S, chname, j.get("item_key"))
                        if dft and int(j.get("cover_by_user") or 0):
                            st.button(f"Dùng bìa mặc định của sản phẩm ({dft})", key=f"rcv_{jid}",
                                      on_click=reset_cover_cb, args=(jid,))
                    st.caption(Path(j["video_path"]).name)
                    with st.popover("Xem video"):
                        if st.session_state.get(f"play_{jid}"):
                            try:
                                prv = ana.WORK_DIR / str(jid) / "xem_thu.mp4"
                                prv.parent.mkdir(parents=True, exist_ok=True)
                                st.video(make_preview(j["video_path"], str(prv)))
                            except Exception as e:
                                st.error(str(e))
                        else:
                            st.button("Phát", key=f"pl_{jid}",
                                      on_click=lambda i=jid: st.session_state.__setitem__(f"play_{i}", True))
                    with st.popover("Bỏ video"):
                        st.write("Chuyển video này vào thư mục **VIDEO LỖI** và bỏ khỏi danh sách duyệt?")
                        st.button("Xác nhận chuyển", key=f"dx_{jid}", type="primary", on_click=discard_cb, args=(jid,))
                with c2:
                    if not j["frames"]:
                        st.warning("Video này chưa phân tích xong.")
                        st.button("Phân tích lại", key=f"ra_{jid}", on_click=reanalyze_cb, args=(jid,))
                    st.markdown(conf_badge(int(j["confidence"] or 0), j["item_key"], j.get("reviewed")),
                                unsafe_allow_html=True)
                    if j.get("ai_note"):
                        st.caption(j["ai_note"])
                    st.selectbox("Sản phẩm trong video", [""] + list(ITEMS), key=k("it", jid),
                                 format_func=lambda x: ITEMS[x]["name"] if x in ITEMS else "— Không gắn giỏ (video kiến thức) —",
                                 on_change=save_item, args=(jid, chname))
                    if st.session_state[k("it", jid)]:
                        opts = [p["id"] for p in show] + [i for i in st.session_state[k("pr", jid)] if i not in smap]
                        st.multiselect("Sản phẩm sẽ gắn (2 giỏ trùng thì gắn cả 2)", opts, key=k("pr", jid),
                                       placeholder="Chọn sản phẩm trong Trưng bày",
                                       format_func=lambda i: prod.label(smap.get(i, {"id": i, "name": "(chưa đồng bộ)"})),
                                       on_change=save_products, args=(jid, chname))
                        cc = st.columns([3, 1])
                        cc[0].text_input("Tên giỏ hàng hiện trên video (tối đa 30 ký tự)", key=k("cart", jid),
                                         max_chars=30, on_change=save, args=(jid, "cart_name", "cart"))
                        cc[1].write("")
                        cc[1].button("Mẫu", key=f"tpl_{jid}", help="Lưu làm tên giỏ mẫu: lần sau kênh này tự dùng tên này",
                                     on_click=save_cart_template,
                                     args=(chname, jid))
                    if int(j["confidence"] or 0) < 60 and not int(j.get("reviewed") or 0):
                        st.checkbox("Tôi đã kiểm tra, sản phẩm đúng rồi", key=k("rev", jid),
                                    on_change=save, args=(jid, "reviewed", "rev", int))
                with c3:
                    st.text_area("Mô tả (caption)", key=k("cap", jid), height=105,
                                 on_change=save, args=(jid, "caption", "cap"))
                    st.text_input("Hashtag (cách nhau dấu phẩy)", key=k("tag", jid),
                                  on_change=save, args=(jid, "hashtags", "tag"))
                    cc = st.columns([1.35, 0.9, 1.25])
                    cc[0].date_input("Ngày đăng", key=k("d", jid), format="DD/MM/YYYY", on_change=save_time, args=(jid,))
                    cc[1].time_input("Giờ", key=k("t", jid), step=300, on_change=save_time, args=(jid,))
                    cc[2].selectbox("Người xem", list(VIS), key=k("vis", jid), format_func=VIS.get,
                                    on_change=save, args=(jid, "visibility", "vis"))
                    if j["scheduled_at"]:
                        st.markdown(f"{datetime.strptime(j['scheduled_at'], FMT):%d/%m %H:%M}"
                                    + golden_tag(j["scheduled_at"]), unsafe_allow_html=True)
                    match = [x for x in fav_opts if j.get("item_key") and j["item_key"] in fav_items.get(x, [])]
                    mus_opts_j = ["none"] + list(amo) + match + [x for x in fav_opts if x not in match] + local_opts
                    if st.session_state[k("mu", jid)] not in mus_opts_j:
                        mus_opts_j = mus_opts_j + [st.session_state[k("mu", jid)]]
                    st.selectbox("Nhạc nền", mus_opts_j, key=k("mu", jid), format_func=lambda x: mus_fmt.get(x, x),
                                 on_change=save_music, args=(jid,))
                    st.checkbox("Giữ âm thanh gốc", key=k("ka", jid), on_change=save, args=(jid, "keep_audio", "ka", int),
                                help="Bỏ tick = tắt tiếng gốc của video (tool tắt trên bản sao, video trong máy giữ nguyên)")
                    if not st.session_state[k("ka", jid)] and st.session_state[k("mu", jid)] == "none":
                        st.warning("Đã tắt âm gốc mà chưa chọn nhạc → video sẽ KHÔNG có tiếng.")
                    mv = st.session_state[k("mu", jid)]
                    src = favfile.get(mv) if mv.startswith("tiktok::") else (mv[7:] if mv.startswith("local::") else None)
                    if src and Path(src).exists():
                        st.audio(src)
                    if mv.startswith("tiktok::") and not int(j.get("music_by_user") or 0):
                        n_alt = sum(1 for f in favs if j.get("item_key") and j["item_key"] in (f.get("items") or [])
                                    and f.get("file"))
                        rb = st.columns([3, 1.1])
                        rb[0].caption("Tool tự gắn âm thanh Yêu thích nói đúng sản phẩm (đã tắt âm gốc). Nghe thử, "
                                      "không ưng thì bấm Bài khác hoặc chọn bài khác ở ô Nhạc nền.")
                        rb[1].button("Bài khác", key=f"nx_{jid}", on_click=next_fav, args=(jid, chname),
                                     disabled=n_alt < 2, help=f"Sản phẩm này có {n_alt} âm thanh Yêu thích")

        # ----- Xác nhận -----
        def confirm(ids, chn=chname):
            bad = []
            for i in ids:
                j = db.get_job(i)
                if needs_check(j):
                    bad.append(f"{Path(j['video_path']).name}: chấm đỏ, chưa tick 'Tôi đã kiểm tra'")
                elif j["item_key"] and not j["products"]:
                    bad.append(f"{Path(j['video_path']).name}: chưa chọn sản phẩm để gắn (hoặc chọn 'Không gắn giỏ')")
                elif j["products"] and not (j["cart_name"] or "").strip():
                    bad.append(f"{Path(j['video_path']).name}: chưa có tên giỏ hàng")
            if bad:
                st.session_state[f"cf_err_{slug(chn)}"] = bad
                return
            for i in ids:
                j = db.get_job(i)
                if not j["scheduled_at"]:
                    db.update_job(i, scheduled_at=sch.round5(datetime.now()).strftime(FMT))
                db.update_job(i, status="pending")
                stats.record("xac_nhan", j)
                forget(i)
                st.session_state.pop(k("sel", i), None)
            st.session_state[f"cf_ok_{slug(chn)}"] = len(ids)

        cc = st.columns(2)
        cc[0].button(f"Xác nhận đăng {len(sel_ids)} video đã chọn", key=f"cfs_{slug(chname)}",
                     disabled=not sel_ids, on_click=confirm, args=(sel_ids,))
        cc[1].button(f"Xác nhận đăng TẤT CẢ {len(jobs)} video kênh {chname}", key=f"cfa_{slug(chname)}",
                     type="primary", on_click=confirm, args=([j["id"] for j in jobs],))
        for e in st.session_state.pop(f"cf_err_{slug(chname)}", []):
            st.error(e)
        if st.session_state.get(f"cf_ok_{slug(chname)}"):
            st.success(f"Đã xác nhận {st.session_state.pop(f'cf_ok_{slug(chname)}')} video → bộ đăng tự động sẽ "
                       f"tải lên & hẹn giờ trên TikTok. Theo dõi ở tab Hàng chờ.")

# =============================== HÀNG CHỜ ===============================
with tabs[2]:
    f1, f2 = st.columns([4, 1])
    show_st = f1.multiselect("Lọc trạng thái", list(db.STATUS_LABELS), format_func=db.STATUS_LABELS.get,
                             default=["pending", "running", "scheduled", "error", "check", "paused", "scheduled_fb"])
    if f2.button("Làm mới"):
        st.rerun()
    jobs_q = [j for j in db.list_jobs(show_st) if j["status"] != "draft" or "draft" in show_st]
    if not jobs_q:
        st.info("Không có gì trong hàng chờ.")
    else:
        df = pd.DataFrame([{
            "Chọn": False, "ID": j["id"], "Trạng thái": db.STATUS_LABELS.get(j["status"], j["status"]),
            "Nền tảng": "TikTok" if j["platform"] == "tiktok" else "Facebook", "Kênh": j["channel"],
            "Video": Path(j["video_path"]).name, "Giờ đăng": j["scheduled_at"],
            "Giỏ hàng": (j["cart_name"] + f" ({len(j['products'])})") if j["products"] else "—",
            "Kết quả": j["result"]} for j in jobs_q])
        ed = st.data_editor(df, hide_index=True, width="stretch", key="q_ed",
                            disabled=[c for c in df.columns if c != "Chọn"])
        sel = [int(i) for i in ed[ed["Chọn"]]["ID"].tolist()]
        a = st.columns(5)
        if a[0].button("Đăng ngay", disabled=not sel):
            for i in sel:
                db.update_job(i, status="pending", scheduled_at=datetime.now().strftime(FMT))
            st.rerun()
        if a[1].button("Tạm dừng", disabled=not sel):
            for i in sel:
                db.update_job(i, status="paused")
            st.rerun()
        if a[2].button("Cho chạy lại", disabled=not sel, help="Video lỗi được chuyển lại về CHƯA UP"):
            for i in sel:
                j = db.get_job(i)
                if j["platform"] == "tiktok" and FOLDER_ERR in j["video_path"]:
                    new = chs.move_to(j["video_path"], ROOT, j["channel"], FOLDER_TODO)
                    note = Path(j["video_path"]).with_suffix(".LOI.txt")
                    if note.exists():
                        note.unlink()
                    db.rename_video_path(j["video_path"], new)
                db.update_job(i, status="pending", result="")
            st.rerun()
        if a[3].button("Đưa về Duyệt", disabled=not sel):
            for i in sel:
                if db.get_job(i)["status"] in ("pending", "paused", "error"):
                    db.update_job(i, status="draft")
            st.rerun()
        if a[4].button("Xoá", disabled=not sel):
            db.delete_jobs(sel)
            st.rerun()
        st.caption("Cần kiểm tra: tool đã bấm đăng nhưng chưa thấy TikTok xác nhận → bác mở kênh xem. "
                   "Lỗi: video đã chuyển vào VIDEO LỖI kèm file .LOI.txt ghi lý do.")

# =============================== KÊNH & SẢN PHẨM ===============================
with tabs[3]:
    st.subheader("Thư mục gốc")
    c1, c2, c3 = st.columns([4, 1, 1])
    root_new = c1.text_input("Thư mục gốc chứa video", ROOT, key="root_in")
    c2.write("")
    c2.write("")
    if c2.button("Chọn", key="pick_root"):
        f = pick_folder("Chọn thư mục gốc")
        if f:
            S["root_folder"] = f
            save_settings(S)
            st.rerun()
    c3.write("")
    c3.write("")
    if c3.button("Mở thư mục", disabled=not ROOT):
        open_folder(ROOT)

    st.subheader("Danh sách kênh")
    ch_df = st.data_editor(pd.DataFrame(S.get("channels") or [], columns=["name", "handle", "enabled", "profile_dir"]),
                           num_rows="dynamic", hide_index=True, width="stretch", key="ch_ed",
                           column_config={"name": "Tên kênh (= tên thư mục)", "handle": "@ tên TikTok",
                                          "enabled": st.column_config.CheckboxColumn("Dùng", default=True),
                                          "profile_dir": "Thư mục hồ sơ trình duyệt (để trống = tự tạo)"})
    if st.button("Lưu kênh & tạo thư mục", type="primary"):
        S["root_folder"] = root_new.strip()
        S["channels"] = [{"name": str(r["name"]).strip(), "handle": str(r.get("handle") or "").strip().lstrip("@"),
                          "enabled": bool(r.get("enabled") if r.get("enabled") is not None else True),
                          "profile_dir": str(r.get("profile_dir") or "").strip()}
                         for r in ch_df.fillna("").to_dict("records") if str(r["name"]).strip()]
        save_settings(S)
        made = chs.ensure_structure(S["root_folder"], S["channels"]) if S["root_folder"] else []
        st.success(f"Đã lưu. Tạo mới {len(made)} thư mục.")
        st.rerun()

    st.info("Mỗi kênh dùng **1 trình duyệt riêng** (hồ sơ Chrome riêng). Đăng nhập 1 lần, tool nhớ mãi. "
            "Bấm **Tạo biểu tượng** để có biểu tượng mở trình duyệt kênh đó ngoài màn hình. "
            "Khi tool đang đăng cho kênh nào thì KHÔNG mở biểu tượng của kênh đó.")
    for c in S.get("channels", []):
        n = c["name"]
        pdir = profile_dir(S, n)
        sc = prod.load_showcase(n)
        favs = favorites(n)
        logged = any(pdir.iterdir())
        with st.expander(f"{'' if logged else ''} {n}  ·  @{c.get('handle') or '?'}  ·  {len(sc['products'])} sản phẩm "
                         f"trưng bày  ·  {len(favs)} âm thanh yêu thích" + ("  ·  đang bận" if is_busy(n) else "")):
            st.caption(f"Hồ sơ trình duyệt: `{pdir}`")
            b = st.columns(5)
            if b[0].button("Đăng nhập TikTok", key=f"lg_{slug(n)}"):
                spawn(["--login", n])
                st.info("Đã mở trình duyệt. Đăng nhập xong bấm nút vàng trên trang.")
            if b[1].button("Tạo biểu tượng", key=f"sc_{slug(n)}"):
                ok, err = make_shortcut(n)
                st.success("Đã tạo biểu tượng ngoài màn hình.") if ok else st.error(f"Không tạo được: {err}")
            if b[2].button("Đồng bộ Trưng bày", key=f"ss_{slug(n)}"):
                spawn(["--sync-showcase", n])
                st.info("Đang mở trình duyệt đọc Trưng bày sản phẩm (không đăng gì). Xong bấm Làm mới.")
            if b[3].button("Đồng bộ âm thanh Yêu thích", key=f"sf_{slug(n)}"):
                spawn(["--sync-sounds", n])
                st.info("Đang đọc mục Yêu thích + tải đoạn nghe thử. Xong bấm Làm mới.")
            if b[4].button("Chụp giao diện (báo lỗi)", key=f"in_{slug(n)}",
                           help="Khi TikTok đổi giao diện làm tool bấm sai, bấm cái này rồi gửi gói báo cáo ở tab Nhật ký"):
                spawn(["--inspect", n])
            if sc["synced_at"]:
                st.caption(f"Trưng bày đồng bộ lúc {sc['synced_at']}")

            st.markdown("**Ghép sản phẩm nhận diện với sản phẩm trong Trưng bày + tên giỏ hàng mẫu**")
            if not sc["products"]:
                st.warning("Chưa đồng bộ Trưng bày → bấm Đồng bộ Trưng bày trước.")
            mp = prod.mapping(S, n)
            smap = {p["id"]: p for p in prod.usable(sc["products"], S)}
            new_map = {}
            for it in S.get("items", []):
                cc = st.columns([1.3, 1.2, 3])
                cc[0].markdown(f"**{it['name']}**")
                cart = cc[1].text_input("Tên giỏ", mp[it["key"]]["cart"], max_chars=30, key=f"mc_{slug(n)}_{it['key']}",
                                        label_visibility="collapsed")
                ids = cc[2].multiselect("ID", list(smap) + [i for i in mp[it["key"]]["ids"] if i not in smap],
                                        default=mp[it["key"]]["ids"], key=f"mi_{slug(n)}_{it['key']}",
                                        format_func=lambda i: prod.label(smap.get(i, {"id": i, "name": "(chưa đồng bộ)"})),
                                        label_visibility="collapsed", placeholder="Chọn sản phẩm trong Trưng bày")
                new_map[it["key"]] = {"cart": cart, "ids": ids}
            bb = st.columns(2)
            if bb[0].button("Lưu ghép sản phẩm", key=f"svm_{slug(n)}", type="primary"):
                S.setdefault("channel_products", {})[n] = new_map
                save_settings(S)
                st.success("Đã lưu.")
            if bb[1].button("Gợi ý lại theo từ khoá", key=f"rsm_{slug(n)}"):
                S.setdefault("channel_products", {})[n] = {k_: {"cart": v["cart"]} for k_, v in new_map.items()}
                save_settings(S)
                for it in S.get("items", []):
                    st.session_state.pop(f"mi_{slug(n)}_{it['key']}", None)
                st.rerun()

    st.subheader("Danh mục sản phẩm cần nhận diện trong video")
    st.caption("AI dựa vào 'Đặc điểm' + ảnh mẫu để nhận ra sản phẩm. 'Từ khoá' dùng để tự tìm sản phẩm trong Trưng bày "
               "và nhận diện theo tên file khi không dùng AI.")
    it_df = st.data_editor(pd.DataFrame(S["items"], columns=["key", "name", "hints", "keywords", "cart"]),
                           num_rows="dynamic", hide_index=True, width="stretch", key="it_ed",
                           column_config={"key": "Mã (không dấu)", "name": "Tên sản phẩm", "hints": "Đặc điểm nhận dạng",
                                          "keywords": "Từ khoá", "cart": "Tên giỏ mặc định"})
    if st.button("Lưu danh mục"):
        S["items"] = [{kk: str(v).strip() for kk, v in r.items()} for r in it_df.fillna("").to_dict("records")
                      if str(r["key"]).strip() and str(r["name"]).strip()]
        save_settings(S)
        st.success("Đã lưu.")
        st.rerun()
    with st.expander("Ảnh mẫu sản phẩm (không bắt buộc, giúp AI nhận diện chuẩn hơn)"):
        cols = st.columns(3)
        for i, it in enumerate(S["items"]):
            with cols[i % 3]:
                ref = REF_DIR / f"{it['key']}.jpg"
                st.markdown(f"**{it['name']}**")
                if ref.exists():
                    st.image(str(ref), width=140)
                up = st.file_uploader("Ảnh chụp thật sản phẩm", type=["jpg", "jpeg", "png"], key=f"ref_{it['key']}")
                if up is not None:
                    from PIL import Image
                    Image.open(up).convert("RGB").save(ref, "JPEG", quality=88)
                    st.success("Đã lưu ảnh mẫu.")

# =============================== NHẠC NỀN ===============================
with tabs[4]:
    st.subheader(f"Nhạc trên máy (thư mục {FOLDER_MUSIC})")
    if ROOT:
        if st.button("Mở thư mục nhạc"):
            open_folder(str(Path(ROOT) / FOLDER_MUSIC))
        mf = chs.music_files(ROOT)
        if not mf:
            st.info(f"Chép file .mp3 vào `{Path(ROOT) / FOLDER_MUSIC}` là dùng được.")
        for m in mf:
            c1, c2 = st.columns([1, 2])
            c1.write(m.name)
            c2.audio(str(m))
        st.caption("Video có gắn giỏ hàng nên dùng nhạc trong thư viện TikTok (mục Yêu thích). Nhạc ngoài dễ bị "
                   "TikTok tắt tiếng / bóp vì bản quyền.")
    st.subheader("Nhạc TikTok tự động (không cần chuẩn bị gì)")
    st.markdown("""Lúc đăng, tool mở mục **Âm thanh** của TikTok và tự chọn 1 trong 3 bài đầu (bỏ qua các bài
"original sound" vì thường là giọng nói người khác), rồi hạ nhạc nhỏ để nghe rõ giọng bác.
- **Nhạc TikTok đề xuất**: bài TikTok gợi ý cho video, hay theo xu hướng.
- **Nhạc thương mại 'Không giới hạn'**: kho nhạc TikTok cho phép dùng cho bán hàng → **nên dùng cho video có giỏ**,
  ít bị tắt tiếng vì bản quyền.
- **Tự động (khuyên dùng)**: video có giỏ → nhạc thương mại, video kiến thức không giỏ → nhạc đề xuất.
- **Tìm nhạc theo từ khoá**: sửa từ khoá ở tab Cài đặt.

Bài nào được chọn sẽ ghi ở cột *Kết quả* trong tab Hàng chờ. Thêm nhạc lỗi thì tool vẫn đăng (không nhạc).""")
    st.subheader("Âm thanh Yêu thích → gắn đúng sản phẩm")
    st.markdown("""Bấm **Đồng bộ** để tool lấy danh sách Yêu thích của kênh và **tải trọn bài để nghe thử**. Sau đó tool
**nghe lời nói trong từng âm thanh** (bộ nghe giọng nói Whisper chạy trên máy, miễn phí) và **tự gắn sản phẩm** khi nghe
thấy tên sản phẩm. Bác nghe thử, sửa lại nếu sai. Ở tab Duyệt bấm **Gán âm thanh Yêu thích đúng sản phẩm**, mỗi
video sẽ lấy đúng âm thanh của sản phẩm đó và tắt âm gốc. Nghe thử lần cuối rồi mới Xác nhận đăng.""")

    def _save_fav(chn, fid, idx, field, wkey):
        favs_ = snd.load_favs(chn)
        for i_, f_ in enumerate(favs_):
            if (f_.get("id") == fid) if fid else (i_ == idx):  # âm thanh cũ chưa có mã số -> theo thứ tự
                f_[field] = st.session_state[wkey]
                if field == "items":
                    f_["items_by"] = "user"
        snd.save_favs(chn, favs_)

    for c in S.get("channels", []):
        cn = c["name"]
        favs_c = snd.load_favs(cn)
        n_file = sum(1 for f in favs_c if f.get("file"))
        n_lab = sum(1 for f in favs_c if f.get("items"))
        with st.expander(f"{cn} · {len(favs_c)} âm thanh · {n_file} nghe thử được · {n_lab} đã gắn sản phẩm",
                         expanded=bool(favs_c) and n_lab < len(favs_c)):
            b1, b2, b3 = st.columns(3)
            if b1.button("Đồng bộ Yêu thích", key=f"fsync_{slug(cn)}",
                         help="Mở trình duyệt kênh, đọc mục Yêu thích, tải file nghe thử rồi tự nghe để gắn sản phẩm"):
                spawn(["--sync-sounds", cn])
                st.info("Đang đồng bộ... xem tiến độ ở tab Nhật ký. Xong thì bấm F5.")
            if b2.button("Nghe lại & gắn sản phẩm", key=f"flab_{slug(cn)}", disabled=not n_file,
                         help="Nghe lại tất cả âm thanh (giữ nguyên những cái bác đã tự sửa)"):
                spawn(["--label-sounds", cn])
                st.info("Đang nghe... xem tiến độ ở tab Nhật ký. Xong thì bấm F5.")
            flt = b3.selectbox("Xem", ["all", "none"] + list(ITEMS), key=f"fflt_{slug(cn)}",
                               format_func=lambda x: {"all": "Tất cả", "none": "Chưa gắn sản phẩm"}.get(
                                   x, "Sản phẩm: " + ITEMS.get(x, {}).get("name", x)))
            if not favs_c:
                st.caption("Chưa có. Bấm Đồng bộ Yêu thích.")
            n_old = sum(1 for f in favs_c if not f.get("id"))
            if n_old:
                st.warning(f"{n_old} âm thanh từ lần đồng bộ cũ chưa có mã số nên chưa nghe thử được và lúc đăng dễ chọn "
                           "nhầm bài trùng tên. Bấm **Đồng bộ Yêu thích** để cập nhật.")
            for i_f, f in enumerate(favs_c):
                its = f.get("items") or []
                if (flt == "none" and its) or (flt not in ("all", "none") and flt not in its):
                    continue
                fid = f.get("id") or ""
                kid = fid or f"i{i_f}"  # khoá riêng cho từng ô (2 bài trùng tên không bị lỗi)
                c1, c2, c3 = st.columns([1.3, 1.4, 1.3])
                c1.markdown(f"**{f.get('title')}**  \n{f.get('artist', '')} · {f.get('duration', '')}"
                            + ({"auto": "  \ntool tự gắn (nghe thấy tên sản phẩm)", "ai": "  \nAI đoán theo lời nói, nên nghe lại"}
                               .get(f.get("items_by"), "") if its else ""))
                if f.get("transcript"):
                    c1.caption("" + f["transcript"][:160] + ("…" if len(f["transcript"]) > 160 else ""))
                elif f.get("transcript") == "":
                    c1.caption("(không có lời nói, chỉ có nhạc)")
                if f.get("file") and Path(f["file"]).exists():
                    c2.audio(f["file"])
                else:
                    c2.caption("(chưa tải được file nghe thử, bấm Đồng bộ)")
                wk = f"fit_{slug(cn)}_{kid}"
                if wk not in st.session_state:
                    st.session_state[wk] = [x for x in its if x in ITEMS]
                c3.multiselect("Âm thanh này nói về", list(ITEMS), key=wk, format_func=lambda x: ITEMS[x]["name"],
                               on_change=_save_fav, args=(cn, fid, i_f, "items", wk), placeholder="Chưa gắn sản phẩm")
                sk = f"fskip_{slug(cn)}_{kid}"
                if sk not in st.session_state:
                    st.session_state[sk] = bool(f.get("skip"))
                c3.checkbox("Không dùng âm thanh này", key=sk, on_change=_save_fav, args=(cn, fid, i_f, "skip", sk))

# =============================== CÀI ĐẶT ===============================
with tabs[5]:
    st.subheader("Giao diện")
    st.caption("Đổi là thấy ngay, không cần bấm Lưu.")
    g1, g2, g3 = st.columns([1, 1.4, 1.4])
    g1.radio("Sáng / tối", ["light", "dark"], index=0 if ui.mode(S) == "light" else 1, horizontal=True,
             format_func={"light": "Sáng", "dark": "Tối"}.get, key="ui_theme_set", on_change=save_ui,
             args=("ui_theme", "ui_theme_set"))
    _bgs = list(ui.BACKGROUNDS)
    g2.selectbox("Mẫu nền", _bgs, index=_bgs.index(S.get("ui_bg", "xanh_tim")) if S.get("ui_bg", "xanh_tim") in _bgs
                 else 0, format_func=lambda x: ui.BACKGROUNDS[x][0], key="ui_bg_set", on_change=save_ui,
                 args=("ui_bg", "ui_bg_set"))
    _cards = list(ui.CARDS)
    g3.radio("Kiểu khung", _cards, index=_cards.index(S.get("ui_card", "kinh")) if S.get("ui_card", "kinh") in _cards
             else 0, format_func=ui.CARDS.get, key="ui_card_set", on_change=save_ui, args=("ui_card", "ui_card_set"))
    _pv = st.columns(5)
    for _n, _kk in enumerate(["xanh_tim", "dai_duong", "hoang_hon", "dong_lua", "dem_tim"]):
        _pv[_n].markdown(ui.preview_html(_kk), unsafe_allow_html=True)
        _pv[_n].caption(ui.BACKGROUNDS[_kk][0])
    st.toggle("Nền chuyển động nhẹ", S.get("ui_motion", True), key="ui_motion_set", on_change=save_ui,
              args=("ui_motion", "ui_motion_set"))
    if S.get("ui_bg") == "anh_rieng":
        def _up_bg():
            _f = st.session_state.get("ui_bg_file")
            if _f:
                try:
                    ui.save_bg(_f.getvalue())
                except Exception as _e:
                    st.session_state["ui_bg_err"] = str(_e)
        b1, b2 = st.columns([2, 1])
        b1.file_uploader("Ảnh nền của bác (jpg, png, webp)", type=["jpg", "jpeg", "png", "webp"], key="ui_bg_file",
                         on_change=_up_bg)
        b2.slider("Độ mờ ảnh nền", 0, 30, int(S.get("ui_bg_blur", 8)), key="ui_bg_blur_set", on_change=save_ui,
                  args=("ui_bg_blur", "ui_bg_blur_set"))
        if st.session_state.pop("ui_bg_err", None):
            st.error("Không đọc được ảnh này, bác chọn ảnh khác giúp em.")
        if not ui.BG_FILE.exists():
            st.info("Chưa có ảnh nền: tải 1 ảnh lên ở ô bên trên.")
    st.divider()
    st.subheader("Cập nhật")
    st.caption(f"Phiên bản đang dùng: {upd.local_version()}. Tool tải bản mới từ GitHub, kiểm tra mã từng file, chờ "
               "hết video đang đăng rồi mới thay. Dữ liệu (đăng nhập kênh, khoá AI, hàng chờ, thống kê) không bị đụng tới.")
    u1, u2 = st.columns([2, 1])
    u1.text_input("Mã đọc GitHub (token chỉ có quyền đọc)", S.get("github_token", ""), type="password",
                  key="gh_token_set", on_change=save_ui, args=("github_token", "gh_token_set"),
                  placeholder="github_pat_...", help="Tạo ở github.com → Settings → Developer settings → "
                  "Fine-grained tokens, chỉ chọn kho sonixdangvideo, quyền Contents: Read-only. Không gửi mã này cho ai.")
    _chs = list(upd.CHANNELS)
    u2.selectbox("Kênh cập nhật", _chs, index=_chs.index(S.get("update_channel", "main"))
                 if S.get("update_channel", "main") in _chs else 0, format_func=upd.CHANNELS.get,
                 key="upd_ch_set", on_change=save_ui, args=("update_channel", "upd_ch_set"),
                 help="Thử nghiệm: nhận tính năng mới sớm hơn, có thể còn lỗi.")
    b1, b2, b3 = st.columns(3)
    if b1.button("Kiểm tra cập nhật", icon=":material/sync:", width="stretch"):
        try:
            st.session_state["upd_info"] = upd.check(S)
        except upd.UpdateError as e:
            st.session_state["upd_info"] = None
            st.error(str(e))
    _inf = st.session_state.get("upd_info")
    if _inf:
        if _inf["newer"] or _inf["changed"]:
            st.success(f"Có bản **{_inf['latest']}** (đang dùng {_inf['current']}) · {len(_inf['changed'])} file thay đổi."
                       + (" Có thêm thư viện mới, tool sẽ tự cài." if _inf["deps"] else ""))
            if _inf["notes"]:
                st.markdown(_inf["notes"])
            if b2.button("Tải và cập nhật ngay", type="primary", icon=":material/download:", width="stretch"):
                try:
                    with st.status("Đang tải bản mới...", expanded=True) as _stt:
                        _bar = st.progress(0.0)
                        _stage = upd.download(_inf, S, lambda i, n, name: _bar.progress(i / max(n, 1), text=name))
                        _stt.update(label="Đang thay file...")
                        upd.apply(_inf, _stage)
                        _stt.update(label="Xong. Tool sẽ khởi động lại", state="complete")
                    st.session_state.pop("upd_info", None)
                    new_version_cached.clear()
                    upd.restart_later(os.getpid(), pip=_inf["deps"])
                    st.success("Đã cập nhật. Bộ đăng sẽ chờ xong video đang đăng (nếu có) rồi cả tool tự khởi động lại; "
                               "cửa sổ này tự kết nối lại sau khoảng 30 giây.")
                except upd.UpdateError as e:
                    st.error(str(e))
        else:
            st.info(f"Đang dùng bản mới nhất ({_inf['current']}).")
    if upd.last_backup():
        with b3.popover("Quay lại bản trước", icon=":material/undo:", width="stretch"):
            st.write("Trả lại các file của lần cập nhật gần nhất, rồi tự khởi động lại tool.")
            if st.button("Quay lại", type="primary", key="upd_rb"):
                try:
                    _v = upd.rollback()
                    new_version_cached.clear()
                    upd.restart_later(os.getpid())
                    st.success(f"Đã quay lại bản {_v}. Tool đang khởi động lại.")
                except upd.UpdateError as e:
                    st.error(str(e))
    st.divider()
    st.subheader("Claude API key (để AI nhận diện sản phẩm + viết caption)")
    with st.expander("API key là gì, lấy ở đâu? (bấm để xem hướng dẫn)"):
        st.markdown("""
**API key** là "chìa khoá" để tool gọi AI Claude. Trả tiền theo lượt dùng, **tách riêng** với gói Claude chat.
1. Vào **https://console.anthropic.com** → đăng nhập bằng Gmail.
2. Menu **Billing** (thanh toán) → **Buy credits** (nạp tiền) → nạp **5 USD** (~130.000đ) bằng thẻ Visa/Mastercard.
   Nên đặt **Spend limit** (giới hạn chi tiêu) ~10 USD/tháng.
3. Menu **API Keys** → **Create Key** → đặt tên `SonixDangVideo` → **Copy** (key bắt đầu bằng `sk-ant-`, chỉ hiện 1 lần).
4. Dán vào ô dưới đây → **Lưu cài đặt**. Xong!

Không gửi key cho ai, không dán vào chat. Key nằm trong thư mục `data` trên máy bác, không bị đóng gói khi chia sẻ tool.""")
    key = st.text_input("API key", S.get("anthropic_api_key", ""), type="password", placeholder="sk-ant-...")
    st.subheader("Gemini API key (AI của Google, có gói MIỄN PHÍ)")
    with st.expander("Lấy Gemini API key miễn phí thế nào? (bấm để xem)"):
        st.markdown("""
Gói Gemini trong app chat (Gemini Advanced/Google AI) **không dùng được cho tool**. Tool cần **Gemini API key** riêng,
lấy miễn phí, không cần thẻ:
1. Vào **https://aistudio.google.com/apikey** → đăng nhập Gmail.
2. Bấm **Create API key** (Tạo khoá API) → **Copy** (key bắt đầu bằng `AIza...`).
3. Dán vào ô dưới → **Lưu cài đặt** → ở **Mức AI mặc định** chọn **Gemini 3.5 Flash-Lite**.

Lưu ý gói miễn phí: Google giới hạn **số lượt mỗi phút và mỗi ngày** (xem ở aistudio.google.com/rate-limit), và
**Google được dùng nội dung gửi lên (ảnh khung hình video) để cải thiện sản phẩm của họ**.
Không dán key vào chat. Key nằm trong thư mục `data` trên máy bác.""")
    gkey = st.text_input("Gemini API key", S.get("gemini_api_key", ""), type="password", placeholder="AIza...")
    AI_DEFAULT_OPTS = list(MODELS) + [NO_AI]
    model = st.selectbox("Mức AI mặc định", AI_DEFAULT_OPTS,
                         format_func=lambda m: MODELS.get(m, "Không dùng AI · theo tên file, caption mẫu (miễn phí)"),
                         index=AI_DEFAULT_OPTS.index(S["ai_model"]) if S.get("ai_model") in AI_DEFAULT_OPTS else 0,
                         help="Mức được chọn sẵn ở Bước 2 mỗi lần phân tích. Chọn 'Không dùng AI' để không tốn tiền.")
    tags = st.text_input("Hashtag luôn gắn", S.get("default_hashtags", ""))
    excl = st.text_input("Không gắn sản phẩm có nhãn (cách nhau dấu phẩy)",
                         ", ".join(S.get("exclude_tags", ["HÀNG TẶNG", "LIVESTREAM"])),
                         help="Sản phẩm tên bắt đầu bằng [HÀNG TẶNG...] hay [LIVESTREAM] sẽ không tự ghép, không hiện để chọn")
    st.subheader("Hướng dẫn AI viết caption")
    cg1, cg2 = st.columns([3, 1])
    cguide = cg1.text_area("Hướng dẫn chung (AI làm theo cho mọi kênh)", S.get("caption_guide", ""), height=150,
                           placeholder="Ví dụ:\n- Caption 2-3 dòng, ngắn gọn, dễ đọc.\n"
                                       "- Dòng 1 hỏi đúng nỗi lo của bà con (vàng lá, thối rễ, rụng trái...).\n"
                                       "- Dòng 2 nêu 1 lợi ích chính của sản phẩm.\n"
                                       "- Dòng cuối mời bấm giỏ hàng vàng.\n- Tối đa 1 emoji.")
    cmax = cg2.number_input("Độ dài tối đa (ký tự)", 50, 2200, int(S.get("caption_max_chars", 150)), 10,
                            help="AI viết dài hơn 1,3 lần mức này thì tool tự cắt ở cuối câu gần nhất")
    with st.expander("Hướng dẫn riêng từng kênh (không bắt buộc)"):
        cg_by = {c["name"]: st.text_area(c["name"], (S.get("caption_guide_by_channel") or {}).get(c["name"], ""),
                                         key=f"cg_{slug(c['name'])}", height=80)
                 for c in S.get("channels", [])}
    st.caption("Sửa xong bấm **Lưu cài đặt**. Video đã phân tích: vào tab Duyệt, chọn video → **Viết lại "
               "caption** (giữ nguyên sản phẩm, ảnh bìa, giờ đăng).")
    st.subheader("Nhạc nền TikTok")
    m1, m2 = st.columns(2)
    amo_s = {"none": "Không thêm nhạc", **auto_music_opts()}
    dmus = m1.selectbox("Nhạc mặc định cho video mới", list(amo_s), format_func=amo_s.get,
                        index=list(amo_s).index(S.get("default_music", "auto::smart"))
                        if S.get("default_music", "auto::smart") in amo_s else 0)
    mdb = m2.slider("Âm lượng nhạc TikTok khi video có giọng nói (dB)", -30, 0, int(S.get("tt_music_db", -14)), 1,
                    help="0 = to bằng bài gốc. -14 = nhỏ làm nền, nghe rõ giọng bác. Video không có tiếng thì giữ 0.")
    dka = st.toggle("Video mới: giữ âm thanh gốc", bool(S.get("default_keep_audio", False)),
                    help="Tắt (mặc định): video mới tự TẮT tiếng gốc, chỉ còn nhạc. Đổi từng video ở tab Duyệt.")
    afs = st.toggle("Tự gắn âm thanh Yêu thích đúng sản phẩm khi duyệt", bool(S.get("auto_fav_sound", True)),
                    help="Video nào có sản phẩm đã có âm thanh Yêu thích nói về nó (tab Nhạc nền) thì tool gắn sẵn "
                         "âm thanh đó và tắt âm gốc. Bác nghe thử ở tab Duyệt, đổi bài nào thì tool để nguyên bài đó.")
    mkw = st.text_input("Từ khoá tìm nhạc (cách nhau dấu phẩy)", ", ".join(S.get("music_keywords", [])),
                        help="Mỗi từ khoá thành 1 lựa chọn 'Tự động: tìm nhạc ...' khi duyệt video")
    st.subheader("Giờ vàng")
    gh = st.text_input("Khung giờ vàng (HH:MM, cách nhau dấu phẩy)", ", ".join(S["golden_hours"]))
    st.subheader("Cách tool đăng TikTok")
    o = st.columns(3)
    confirm_cb = o[0].toggle("Dừng trên TikTok cho tôi xem lại trước khi bấm Đăng",
                             S.get("tt_confirm_before_post", False),
                             help="Tắt (mặc định): duyệt trong tab Duyệt là đủ, tool tự bấm Đăng/Lên lịch, không hỏi lại. "
                                  "Bật: tool dừng ở trang TikTok chờ bác bấm nút vàng ĐĂNG LUÔN cho từng video.")
    ask_cb = o[1].toggle("Bước nào tool không làm được thì nhờ tôi làm tay", S.get("tt_ask_on_fail", True))
    head_cb = o[2].toggle("Chạy ẩn trình duyệt", S.get("tt_headless", False),
                          help="Ẩn thì không nhờ làm tay được. Chỉ bật khi tool đã chạy ổn định.")
    o = st.columns(3)
    fast_cb = o[0].toggle("Đăng nhanh", S.get("tt_fast", True),
                          help="Rút ngắn thời gian chờ giữa các bước khi đăng. Nếu thấy tool hay bấm hụt thì tắt đi.")
    gap0, gap1 = (S.get("tt_gap_seconds") or [10, 25])[:2]
    gap_a = o[1].number_input("Nghỉ giữa 2 video: từ (giây)", 0, 600, int(gap0),
                              help="Tool nghỉ ngẫu nhiên trong khoảng này rồi mới tải video kế tiếp")
    gap_b = o[2].number_input("đến (giây)", 0, 900, int(gap1))
    o = st.columns(3)
    ahead = o[0].number_input("Hẹn giờ TikTok tối đa (ngày)", 1, 30, int(S.get("tt_max_ahead_days", 10)))
    vol = o[1].slider("Âm lượng nhạc nền (nhạc trên máy)", 0.05, 0.6, float(S.get("music_volume", 0.15)), 0.05)
    vis_d = o[2].selectbox("Người xem mặc định", list(VIS), format_func=VIS.get,
                           index=list(VIS).index(S.get("default_visibility", "public")))
    disc_d = st.selectbox("Khai báo nội dung bài đăng (mặc định)", list(DISC), format_func=DISC.get,
                          index=list(DISC).index(S.get("default_disclosure", "own_brand")),
                          help="Tool tự bật 'Khai báo nội dung bài đăng' và tick ô này cho mọi video")
    st.subheader("App trên máy tính & mở trên điện thoại")
    a1, a2 = st.columns(2)
    if a1.button("Tạo biểu tượng SonixDangVideo (màn hình + menu Start)"):
        ok, err = desktop.create_shortcuts()
        st.success("Đã tạo biểu tượng. Từ giờ bấm đúp biểu tượng là mở tool.") if ok else st.error(err)
    auto = a2.toggle("Tự bật tool (chạy nền) mỗi khi mở máy", desktop.is_autostart(),
                     help="Bật để tới giờ hẹn vẫn tự đăng dù bác quên mở tool")
    if auto != desktop.is_autostart():
        ok, err = desktop.set_autostart(auto)
        st.success("Đã lưu.") if ok else st.error(err)
    l1, l2 = st.columns(2)
    lan = l1.toggle("Cho mở tool trên điện thoại / máy khác cùng Wi-Fi", S.get("lan_access", False))
    pin = l2.text_input("Mã PIN khi mở từ máy khác (nên đặt 4-6 số)", S.get("app_pin", ""), type="password")
    if lan:
        st.caption(f"Địa chỉ mở trên điện thoại: **http://{desktop.local_ip()}:{desktop.PORT}** · Đổi xong bấm "
                   "Lưu cài đặt, rồi Tắt hẳn tool và mở lại biểu tượng. Lần đầu Windows hỏi cho phép mạng → chọn "
                   "Cho phép (Allow).")
    with st.expander("Biểu tượng app (dùng ảnh của bạn)"):
        up = st.file_uploader("Chọn ảnh (JPG/PNG)", type=["jpg", "jpeg", "png", "webp"], key="icon_up")
        if up is not None:
            from PIL import Image
            src = Image.open(up)
            i1, i2, i3 = st.columns(3)
            zoom = i1.slider("Phóng to", 1.0, 5.0, 2.2, 0.1)
            cx = i2.slider("Sang trái – phải", 0.0, 1.0, 0.53, 0.01)
            cy = i3.slider("Lên – xuống", 0.0, 1.0, 0.32, 0.01)
            icon = desktop.crop_icon(src, zoom, cx, cy)
            p1, p2, p3 = st.columns([1, 1, 4])
            p1.image(icon, caption="Ngoài màn hình", width=96)
            p2.image(icon.resize((32, 32)), caption="Cỡ nhỏ", width=32)
            if p3.button("Dùng ảnh này làm biểu tượng", type="primary"):
                ok, err = desktop.set_custom_icon(icon)
                st.success("Đã đổi biểu tượng! Nếu ngoài màn hình chưa đổi hình, bấm chuột phải ra màn hình → "
                           "Làm mới (Refresh). Thanh tác vụ đổi sau khi mở lại tool.") if ok else st.error(err)
        if desktop.CUSTOM_PNG.exists():
            st.image(str(desktop.CUSTOM_PNG), caption="Biểu tượng đang dùng", width=64)
            if st.button("Về biểu tượng mặc định"):
                desktop.reset_icon()
                st.rerun()
    if st.button("Lưu cài đặt", type="primary"):
        try:
            golden = []
            for x in gh.split(","):
                if x.strip():
                    datetime.strptime(x.strip(), "%H:%M")
                    golden.append(x.strip())
            S.update(exclude_tags=[x.strip() for x in excl.split(",") if x.strip()])
            S.update(caption_guide=cguide.strip(), caption_max_chars=int(cmax),
                     caption_guide_by_channel={kk: v.strip() for kk, v in cg_by.items() if v.strip()})
            S.update(default_keep_audio=bool(dka), auto_fav_sound=bool(afs))
            S.update(default_music=dmus, tt_music_db=int(mdb),
                     music_keywords=[x.strip() for x in mkw.split(",") if x.strip()])
            S.update(gemini_api_key=gkey.strip())
            S.update(anthropic_api_key=key.strip(), ai_model=model, default_hashtags=tags, golden_hours=golden,
                     tt_confirm_before_post=confirm_cb, tt_ask_on_fail=ask_cb, tt_headless=head_cb,
                     tt_fast=bool(fast_cb), tt_gap_seconds=[int(min(gap_a, gap_b)), int(max(gap_a, gap_b))],
                     tt_max_ahead_days=int(ahead), music_volume=float(vol), default_visibility=vis_d,
                     default_disclosure=disc_d, lan_access=bool(lan), app_pin=pin.strip())
            save_settings(S)
            st.success("Đã lưu!")
            st.rerun()
        except ValueError:
            st.error("Giờ vàng sai định dạng. Ví dụ đúng: 05:45, 11:30, 19:30")

# =============================== FACEBOOK ===============================
with tabs[6]:
    from core import fb_ui
    fb_ui.render(S)

# =============================== NHẬT KÝ ===============================
with tabs[7]:
    c = st.columns(3)
    if c[0].button("Tải lại"):
        st.rerun()
    if c[1].button("Mở thư mục ảnh lỗi"):
        open_folder(str(DEBUG_DIR))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        if RUNNER_LOG.exists():
            z.write(RUNNER_LOG, "runner.log")
        for f in sorted(DEBUG_DIR.glob("*"), key=lambda x: x.stat().st_mtime)[-40:]:
            z.write(f, f"debug/{f.name}")
    c[2].download_button("Tải gói báo cáo lỗi (gửi người hỗ trợ)", buf.getvalue(),
                         file_name=f"{APP_NAME}_baocao_{datetime.now():%Y%m%d_%H%M}.zip",
                         help="Chỉ gồm nhật ký + ảnh chụp lỗi. KHÔNG có mật khẩu, token, API key.")
    if RUNNER_LOG.exists():
        lines = RUNNER_LOG.read_text(encoding="utf-8", errors="ignore").splitlines()[-250:]
        st.code("\n".join(reversed(lines)) or "(trống)", language=None)


# =============================== TỔNG HỢP ===============================
with TAB_TONGHOP:
    st.header("Tổng hợp theo ngày")
    st.caption("Mỗi ngày tự tính lại từ 0 lúc 0:00, ngày cũ được lưu để bác xem lại. Số liệu những ngày trước khi có "
               "mục này được dựng lại gần đúng từ hàng chờ.")
    _td = date.today()
    _first = stats.first_day() or _td
    h1, h2 = st.columns([1, 3])
    _day = h1.date_input("Chọn ngày", _td, min_value=min(_first, _td), max_value=_td, format="DD/MM/YYYY", key="th_day")
    _dd = stats.day_detail(_day.isoformat())
    _kinds = list(stats.KINDS)
    _cols = {"phan_tich": "var(--sx-blue)", "xac_nhan": "var(--sx-purple)", "hen_gio": "var(--sx-cyan)",
             "loi": "var(--sx-danger)"}
    h2.markdown(ui.tiles_html([(stats.KINDS[k_], _dd[k_]["total"], _cols[k_]) for k_ in _kinds], cols=4),
                unsafe_allow_html=True)
    _chs = sorted({c_ for k_ in _kinds for c_ in _dd[k_]["channels"]} | {c["name"] for c in CHANNELS})
    _its = {}
    for k_ in _kinds:
        for it_, v_ in _dd[k_]["items"].items():
            _its.setdefault(item_name(it_), {}).setdefault(k_, 0)
            _its[item_name(it_)][k_] += v_
    t1, t2 = st.columns(2)
    with t1.container(border=True, key="card_th_kenh"):
        st.subheader("Theo kênh")
        st.markdown(ui.matrix_html("Kênh", [stats.KINDS[k_] for k_ in _kinds],
                                   [(c_, [_dd[k_]["channels"].get(c_, 0) for k_ in _kinds]) for c_ in _chs]),
                    unsafe_allow_html=True)
    with t2.container(border=True, key="card_th_sp"):
        st.subheader("Theo sản phẩm")
        st.markdown(ui.matrix_html("Sản phẩm", [stats.KINDS[k_] for k_ in _kinds],
                                   [(n_, [v_.get(k_, 0) for k_ in _kinds]) for n_, v_ in
                                    sorted(_its.items(), key=lambda x: -sum(x[1].values()))]),
                    unsafe_allow_html=True)
    with st.container(border=True, key="card_th_7ngay"):
        st.subheader("7 ngày tới ngày đã chọn")
        _m = st.pills("Xem", _kinds, default="hen_gio", format_func=stats.KINDS.get, key="th_metric")
        _ser = stats.series(_m or "hen_gio", _day, 7)
        st.bar_chart(pd.DataFrame({"Số video": [n for _x, n in _ser]},
                                  index=[f"{_x[8:10]}/{_x[5:7]}" for _x, _n in _ser]),
                     color="#6d28d9", height=260, x_label="", y_label="")
