"""Tab Hàng chờ: xem theo kênh/trang, dạng thẻ có ảnh bìa, chia theo ngày, lọc nhanh, thao tác hàng loạt."""
import html
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st

from . import channels as chs
from . import covers as cov
from . import db
from .config import FOLDER_ERR, FOLDER_TODO

FMT = db.TIME_FMT
WD = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
GROUPS = {
    "sap": ("Sắp đăng", ["pending", "running", "paused", "lo_gio"]),
    "hen": ("Đã hẹn giờ", ["scheduled", "scheduled_fb"]),
    "da": ("Đã đăng", ["scheduled", "scheduled_fb", "done"]),
    "loi": ("Lỗi / cần kiểm tra", ["error", "check"]),
}
BADGE = {  # nhãn + màu
    "pending": ("Chờ đăng", "#6d28d9"), "running": ("Đang đăng", "#0e7490"), "paused": ("Tạm dừng", "#64748b"),
    "scheduled": ("Đã hẹn giờ", "#1d4ed8"), "scheduled_fb": ("Đã hẹn giờ", "#1d4ed8"), "done": ("Đã đăng", "#047857"),
    "posted": ("Đã đăng", "#047857"), "error": ("Lỗi", "#be123c"), "check": ("Cần kiểm tra", "#b45309"),
    "lo_gio": ("Lỡ giờ", "#c2410c"),
}
CSS = """<style>
.qx-day{font-family:Montserrat,sans-serif;font-weight:800;font-size:17px;margin:18px 0 6px}
.qx-day i{font-family:inherit;font-weight:400;font-style:italic;font-size:13px;opacity:.7;margin-left:8px}
.qx-b{display:inline-block;padding:2px 10px;border-radius:999px;color:#fff;font-size:12px;font-weight:700}
.qx-t{font-family:Montserrat,sans-serif;font-weight:800;font-size:17px;margin:4px 0 0}
.qx-d{font-size:12px;font-weight:600;opacity:.6}
.qx-m{font-size:11.5px;opacity:.75;line-height:1.35;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.qx-f{font-size:11.5px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.qx-c{font-size:12.5px;line-height:1.35;margin:4px 0 2px;display:-webkit-box;-webkit-line-clamp:2;
-webkit-box-orient:vertical;overflow:hidden;min-height:34px}
.qx-p{font-size:11.5px;font-style:italic;opacity:.75;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
[class*="st-key-qgrid"] [data-testid="stImage"] img{height:150px;object-fit:cover;border-radius:10px}
</style>"""


def _when(j):
    try:
        return datetime.strptime(j.get("scheduled_at") or "", FMT)
    except ValueError:
        return None


def _state(j, now):
    """Trạng thái hiển thị: bài hẹn giờ đã tới giờ = Đã đăng."""
    t = _when(j)
    if j["status"] in ("scheduled", "scheduled_fb") and t and t <= now:
        return "posted"
    return j["status"]


def _in_group(j, g, now):
    s = _state(j, now)
    if g == "hen":
        return s in ("scheduled", "scheduled_fb")
    if g == "da":
        return s in ("posted", "done")
    return j["status"] in GROUPS[g][1]


def _thumb(j):
    for p in [j.get("cover_path")] + [f.get("thumb") for f in (j.get("frames") or [])]:
        if p and Path(p).exists():
            try:
                return cov.thumb(p)
            except Exception:
                return p
    return ""


def _card(j, now, k):
    """Thẻ nhỏ: ảnh bìa, trạng thái, giờ, tên file, caption 2 dòng, sản phẩm. Chi tiết đầy đủ trong nút 'Chi tiết'."""
    s_ = _state(j, now)
    lab, col = BADGE.get(s_, (db.STATUS_LABELS.get(s_, s_), "#64748b"))
    t = _when(j)
    plat = "TT" if j["platform"] == "tiktok" else "FB"
    with st.container(border=True):
        th = _thumb(j)
        if th:
            st.image(th, width="stretch")
        cap = (j.get("caption") or "").strip()
        prod = j.get("cart_name") or ((j.get("products") or [{}])[0].get("name", "") if j.get("products") else "")
        st.markdown(
            f'<span class="qx-b" style="background:{col}">{lab}</span>'
            f'<div class="qx-t">{t:%H:%M} <span class="qx-d">{t:%d/%m}</span></div>' if t else
            f'<span class="qx-b" style="background:{col}">{lab}</span><div class="qx-t">--:--</div>',
            unsafe_allow_html=True)
        st.markdown(f'<div class="qx-m"><b>{plat}</b> · {html.escape(j["channel"])}</div>'
                    f'<div class="qx-f" title="{html.escape(Path(j["video_path"]).name)}">'
                    f'{html.escape(Path(j["video_path"]).name)}</div>'
                    f'<div class="qx-c">{html.escape(cap) or "<i>(chưa có caption)</i>"}</div>'
                    + (f'<div class="qx-p">{html.escape(prod)}</div>' if prod else ""), unsafe_allow_html=True)
        a, b = st.columns([1, 1])
        a.checkbox("Chọn", key=f"qsel_{j['id']}")
        with b.popover("⋯", width="stretch", help="Xem đủ caption, hashtag, nhạc, kết quả"):
            st.markdown(f"**#{j['id']} · {Path(j['video_path']).name}**")
            st.caption(j["video_path"])
            st.write(cap or "(chưa có caption)")
            if j.get("hashtags"):
                st.caption(" ".join("#" + x.strip().lstrip("#") for x in str(j["hashtags"]).split(",") if x.strip()))
            if prod:
                st.markdown(f"**Giỏ hàng:** {prod}")
            if j.get("music_mode") in ("tiktok", "local") and j.get("music_ref"):
                st.markdown(f"**Nhạc:** {str(j['music_ref']).split('::')[-1]}")
            if j.get("result"):
                st.info(str(j["result"]))


def _actions(sel, ROOT, label=""):
    a = st.columns([1.2, 1, 1, 1.1, 1.1, 1.1])
    a[5].caption(label)
    a = a[:5]
    if a[0].button("Đăng ngay", disabled=not sel, key="qa_now"):
        for i in sel:
            db.update_job(i, status="pending", scheduled_at=datetime.now().strftime(FMT))
        st.rerun()
    if a[1].button("Tạm dừng", disabled=not sel, key="qa_pause"):
        for i in sel:
            db.update_job(i, status="paused")
        st.rerun()
    if a[2].button("Chạy lại", disabled=not sel, key="qa_retry", help="Video lỗi được chuyển lại về CHƯA UP"):
        for i in sel:
            j = db.get_job(i)
            if j["platform"] == "tiktok" and FOLDER_ERR in j["video_path"] and ROOT:
                new = chs.move_to(j["video_path"], ROOT, j["channel"], FOLDER_TODO)
                note = Path(j["video_path"]).with_suffix(".LOI.txt")
                if note.exists():
                    note.unlink()
                db.rename_video_path(j["video_path"], new)
            db.update_job(i, status="pending", result="")
        st.rerun()
    if a[3].button("Về Duyệt", disabled=not sel, key="qa_back"):
        for i in sel:
            if db.get_job(i)["status"] in ("pending", "paused", "error"):
                db.update_job(i, status="draft")
        st.rerun()
    if a[4].button("Xoá", disabled=not sel, key="qa_del"):
        db.delete_jobs(sel)
        st.rerun()


def _live_panel(S):
    """Khung 'Đang đăng': video đang đăng, bước đang làm, % tiến độ, các bước vừa xong. Tự cập nhật 2 giây/lần."""
    from . import progress
    import time as _t
    P = progress.read()
    alive = False
    try:
        from .config import HEARTBEAT_FILE
        alive = _t.time() - float(HEARTBEAT_FILE.read_text()) < 90
    except Exception:
        pass
    running = [j for j in db.list_jobs(["running"])]
    with st.container(border=True):
        h = st.columns([3, 2])
        if running and P.get("job") == running[0]["id"] and P.get("state") == "running":
            j = running[0]
            pct = min(1.0, max(0.03, P.get("idx", 0) / max(1, P.get("total", 1))))
            el = int(_t.time() - P.get("start", _t.time()))
            h[0].markdown(f"**Đang đăng:** {html.escape(P.get('file', ''))} · "
                          f"{'TikTok' if P.get('platform') == 'tiktok' else 'Facebook'} · {html.escape(P.get('channel', ''))}")
            st.progress(pct, text=f"Bước {P.get('idx', 0)}/{P.get('total', 0)} · {P.get('step', '')} · "
                                  f"đã chạy {el // 60} phút {el % 60} giây")
            a, b = st.columns([1, 9])
            th = _thumb(j)
            if th:
                a.image(th, width=70)
            b.code("\n".join(P.get("lines", [])[-5:]) or "...", language=None)
        else:
            nxt = sorted([j for j in db.list_jobs(["pending"]) if j.get("scheduled_at")], key=lambda x: x["scheduled_at"])
            msg = "**Bộ đăng đang chạy**, chưa có video nào đang đăng." if alive else \
                "**Bộ đăng tự động đang TẮT.** Bấm 'Bật bộ đăng tự động' ở thanh bên."
            if P.get("state") in ("ok", "fail") and P.get("file"):
                msg += (f"\n\nVideo vừa xong: **{html.escape(P['file'])}** · "
                        + ("xong" if P["state"] == "ok" else "LỖI") + f" · {html.escape(P.get('result', ''))[:140]}")
            if nxt:
                msg += f"\n\nCòn **{len(nxt)} video chờ đăng**, gần nhất: {nxt[0]['scheduled_at'][11:]} " \
                       f"{nxt[0]['scheduled_at'][8:10]}/{nxt[0]['scheduled_at'][5:7]} · {html.escape(nxt[0]['channel'])}"
            h[0].markdown(msg)
        show = h[1].toggle("Hiện trình duyệt khi đăng (để xem lỗi)", not bool(S.get("tt_headless", True)),
                           key="q_show_browser",
                           help="Tắt (mặc định): đăng chạy ẩn, không bật cửa sổ trình duyệt. Bật lên khi muốn xem tool "
                                "làm từng bước để tìm lỗi. Áp dụng từ video kế tiếp.")
        if show == bool(S.get("tt_headless", True)):
            from .config import save_settings
            S["tt_headless"] = not show
            save_settings(S)
            st.rerun(scope="app")


def render(S, ROOT):
    st.markdown(CSS, unsafe_allow_html=True)
    live = bool(db.list_jobs(["running"]))
    st.fragment(run_every=2 if live else 15)(_live_panel)(S)
    now = datetime.now()
    jobs = [j for j in db.list_jobs(None) if j["status"] not in ("draft", "analyzing")]
    names = []
    for j in jobs:
        key = ("TikTok" if j["platform"] == "tiktok" else "Facebook", j["channel"])
        if key not in names:
            names.append(key)
    names.sort()
    opts = ["Tất cả"] + [f"{p} · {c}" for p, c in names]
    cnt = {o: 0 for o in opts}
    for j in jobs:
        cnt["Tất cả"] += 1
        cnt[f"{'TikTok' if j['platform'] == 'tiktok' else 'Facebook'} · {j['channel']}"] += 1
    top = st.columns([5, 1])
    pick = top[0].pills("Kênh / trang", opts, default="Tất cả", key="q_ch",
                        format_func=lambda o: f"{o} ({cnt[o]})") or "Tất cả"
    if top[1].button("Làm mới", key="q_ref"):
        st.rerun()
    js = jobs if pick == "Tất cả" else [j for j in jobs if f"{'TikTok' if j['platform'] == 'tiktok' else 'Facebook'} · {j['channel']}" == pick]

    gcount = {g: sum(_in_group(j, g, now) for j in js) for g in GROUPS}
    f1, f2, f3 = st.columns([2.6, 1, 1.4])
    grp = f1.segmented_control("Xem", list(GROUPS), default="sap", key="q_grp",
                               format_func=lambda g: f"{GROUPS[g][0]} ({gcount[g]})") or "sap"
    rng = f2.selectbox("Thời gian", ["Tất cả", "Hôm nay", "7 ngày tới", "7 ngày qua"], key="q_rng")
    q = f3.text_input("Tìm theo caption / tên file", key="q_q", placeholder="vd: bọ trĩ, DJI_0017")
    js = [j for j in js if _in_group(j, grp, now)]
    today = now.date()
    if rng != "Tất cả":
        def ok(j):
            t = _when(j)
            if not t:
                return False
            if rng == "Hôm nay":
                return t.date() == today
            if rng == "7 ngày tới":
                return today <= t.date() <= today + timedelta(days=7)
            return today - timedelta(days=7) <= t.date() <= today
        js = [j for j in js if ok(j)]
    if q.strip():
        qq = q.strip().lower()
        js = [j for j in js if qq in (j.get("caption") or "").lower() or qq in Path(j["video_path"]).name.lower()]
    newest_first = grp == "da"
    js.sort(key=lambda j: j.get("scheduled_at") or "9999", reverse=newest_first)

    sel = [j["id"] for j in js if st.session_state.get(f"qsel_{j['id']}")]
    c = st.columns([1.1, 0.9, 6])
    if c[0].button("Chọn tất cả", key="q_all", disabled=not js):
        for j in js:
            st.session_state[f"qsel_{j['id']}"] = True
        st.rerun()
    if c[1].button("Bỏ chọn", key="q_none", disabled=not sel):
        for j in js:
            st.session_state[f"qsel_{j['id']}"] = False
        st.rerun()
    with c[2]:
        _actions(sel, ROOT, f"**{len(js)} video** · chọn {len(sel)}")

    if not js:
        st.info("Không có video nào ở mục này.")
        return
    limit = st.session_state.get("q_lim", 40)
    by_day = {}
    for j in js[:limit]:
        t = _when(j)
        by_day.setdefault(t.date() if t else None, []).append(j)
    for d, items in by_day.items():
        if d:
            rel = {0: "hôm nay", 1: "ngày mai", -1: "hôm qua"}.get((d - today).days, "")
            st.markdown(f'<div class="qx-day">{WD[d.weekday()]} · {d:%d/%m}<i>{rel + " · " if rel else ""}'
                        f'{len(items)} video</i></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="qx-day">Chưa có giờ</div>', unsafe_allow_html=True)
        with st.container(key=f"qgrid_{d or 'x'}"):
            for r0 in range(0, len(items), 5):
                cols = st.columns(5)
                for c_, j in zip(cols, items[r0:r0 + 5]):
                    with c_:
                        _card(j, now, 0)
    if len(js) > limit:
        if st.button(f"Xem thêm ({len(js) - limit} video)", key="q_more"):
            st.session_state["q_lim"] = limit + 40
            st.rerun()
    st.caption("Đã đăng: bài hẹn giờ đã tới giờ. Cần kiểm tra: tool đã bấm đăng nhưng chưa thấy xác nhận, hoặc "
               "thiếu ảnh bìa. Lỗi: video đã chuyển vào VIDEO LỖI kèm file .LOI.txt ghi lý do.")
