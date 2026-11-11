"""Tab Facebook: kết nối trang, nhiệm vụ tuần, đăng Reels (AI viết caption, duyệt, xếp giờ)."""
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st

from . import db, facebook, fbq, ui, worker
from .config import FOLDER_DONE, FOLDER_ERR, FOLDER_TODO, MODELS, NO_AI, ai_key, save_settings

FMT = db.TIME_FMT
VER = "v23.0"
TOKEN_GUIDE = """
**Lấy mã kết nối (làm 1 lần, khoảng 15 phút):**

1. Vào **developers.facebook.com**, đăng nhập bằng tài khoản Facebook đang quản trị trang. Lần đầu Facebook hỏi đăng ký nhà phát triển thì bấm theo, xác minh số điện thoại.
2. Bấm **Ứng dụng của tôi (My Apps) → Tạo ứng dụng (Create App)**. Ở mục trường hợp sử dụng chọn **Quản lý mọi thứ trên Trang (Manage everything on your Page)**, đặt tên ví dụ `Sonix Dang Video`, bấm tạo.
3. Vào **Công cụ (Tools) → Graph API Explorer**. Ô **Meta App** chọn ứng dụng vừa tạo. Ô **User or Page** chọn **Get User Access Token**.
4. Tick đủ các quyền: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `pages_read_user_content`, `pages_manage_engagement`, `business_management`, `read_insights` (xem lượt xem từng video, không bắt buộc). Bấm **Generate Access Token**, Facebook hỏi chọn trang thì chọn trang của bác, bấm đồng ý.
5. Bấm biểu tượng **(i)** cạnh mã → **Open in Access Token Tool**. Kéo xuống cuối bấm **Extend Access Token** (gia hạn mã) → bấm **Copy**.
6. Dán mã vừa copy vào ô bên dưới → bấm **Lấy mã trang**. Tool tự đổi sang mã trang **không hết hạn**.

Mã này như chìa khoá trang: chỉ dán vào tool, **không gửi cho ai, không dán vào khung chat**.
"""


def _open_folder(p):
    try:
        Path(p).mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(p))  # noqa
        else:
            subprocess.Popen(["xdg-open", str(p)])
    except Exception as e:
        st.error(f"Không mở được thư mục: {e}")


def _save_page(S, pg):
    pages = [p for p in S.get("facebook_pages", []) if p.get("page_id") != pg.get("page_id")
             and p.get("name") != pg.get("name")]
    S["facebook_pages"] = pages + [pg]
    save_settings(S)


# ------------------------------- kết nối -------------------------------
def _connect(S):
    st.markdown(TOKEN_GUIDE)
    tok = st.text_input("Mã người dùng (đã gia hạn)", type="password", key="fb_user_tok")
    if st.button("Lấy mã trang", type="primary", disabled=not tok.strip()):
        try:
            found = facebook.pages_from_user_token(tok.strip(), S.get("fb_graph_version", VER))
        except Exception as e:
            st.error(f"Không lấy được: {facebook.safe(e)}")
            return
        if not found:
            st.error("Mã đúng nhưng không thấy trang nào. Ở bước 4 bác nhớ chọn trang và tick đủ quyền.")
            return
        old = {p.get("page_id"): p for p in S.get("facebook_pages", [])}
        old_by_name = {p.get("name"): p for p in S.get("facebook_pages", [])}
        for f in found:
            base = old.get(f["id"]) or next((p for n, p in old_by_name.items()
                                             if p.get("page_id") in (f["id"], f.get("username"))
                                             or n.lower() == f["name"].lower()), {}) or {}
            pg = {**base, "name": f["name"], "page_id": f["id"], "token": f["access_token"]}
            pg.setdefault("times", "11:30, 19:30")
            _save_page(S, pg)
        st.success("Đã kết nối: " + ", ".join(f"{f['name']} ({f.get('followers_count', '?')} người theo dõi)"
                                               for f in found))
        st.cache_data.clear()
        st.rerun()


@st.cache_data(ttl=600, show_spinner=False)
def _remote(page_id, token, since_ts, ver):
    since = datetime.fromtimestamp(since_ts)
    out = {"err": ""}
    try:
        out["info"] = facebook.page_info(page_id, token, ver)
    except Exception as e:
        out["err"] = facebook.safe(e)
        return out
    out["counts"] = facebook.week_counts(page_id, token, since, ver)
    try:
        out["comments"] = facebook.unreplied_comments(page_id, token, 7, ver)
    except Exception as e:
        out["comments"], out["cmt_err"] = [], facebook.safe(e)
    out["expiry"] = facebook.token_expiry(token, ver)
    return out


# ------------------------------- nhiệm vụ tuần -------------------------------
def _tasks(S, pg):
    ver = S.get("fb_graph_version", VER)
    ws = facebook.week_start()
    we = ws + timedelta(days=6)
    left = (we.date() - datetime.now().date()).days + 1  # Facebook tính cả hôm nay
    with st.spinner("Đang đọc trang từ Facebook..."):
        R = _remote(pg["page_id"], pg["token"], int(ws.timestamp()), ver)
    if R.get("err"):
        st.error(f"Không đọc được trang: {R['err']}")
        return
    info, cnt = R["info"], R["counts"]
    tw = fbq.tool_week(pg["name"], ws)
    tg = {**fbq.DEFAULT_TARGETS, **(pg.get("targets") or {})}
    h = st.columns([3, 1])
    h[0].markdown(f"### Nhiệm vụ tuần {ws:%d/%m} – {we:%d/%m}\n"
                  f"*Còn {left} ngày · {info.get('followers_count', 0):,} người theo dõi".replace(',', '.')
                  + (f" · mã: {R['expiry']}" if R.get("expiry") else "") + "*")
    if h[1].button("Làm mới số liệu", key="fb_refresh"):
        st.cache_data.clear()
        st.rerun()
    replied_need = tg["replies"]
    rows = [
        ("Thước phim (Reels)", cnt.get("reels"), tg["reels"], tw["reels_planned"]),
        ("Bài viết công khai", cnt.get("posts"), tg["posts"], tw["reels_planned"]),
        ("Tin mới", cnt.get("stories"), tg["stories"], tw["stories_planned"]),
    ]
    tiles, todo = [], []
    for name, have, need, planned in rows:
        hv = "?" if have is None else have
        tiles.append((name, f"{hv}/{need}", "var(--sx-ok)" if have is not None and have >= need
                      else "var(--sx-purple)"))
        if have is not None and have < need:
            miss = need - have
            if planned >= miss:
                todo.append(f"**{name}**: còn thiếu {miss}, tool đã hẹn đủ {planned} trong tuần này.")
            else:
                todo.append(f"**{name}**: còn thiếu {miss}" + (f" (tool đã hẹn {planned})" if planned else "")
                            + f" → cần thêm {miss - planned}.")
    ncm = len(R.get("comments", []))
    tiles.append(("Bình luận chưa trả lời", ncm, "var(--sx-danger)" if ncm else "var(--sx-ok)"))
    st.markdown(ui.tiles_html(tiles, cols=4), unsafe_allow_html=True)
    if ncm:
        todo.append(f"**Trả lời bình luận**: có {ncm} bình luận chưa trả lời (nhiệm vụ cần {replied_need}).")
    if todo:
        st.markdown("**Còn phải làm:**\n" + "\n".join(f"- {t}" for t in todo))
    else:
        st.success("Đã đủ nhiệm vụ tuần này.")
    if tg["stories"] and not pg.get("story"):
        st.caption("Gợi ý: bật **Đăng kèm vào Tin** trong mục Cài đặt đăng bên dưới để tool tự làm nhiệm vụ Tin.")
    with st.expander("Sửa chỉ tiêu tuần (xem ở Facebook → Bảng điều khiển → Trạng thái)"):
        c = st.columns(4)
        nt = {"reels": c[0].number_input("Thước phim", 0, 50, int(tg["reels"]), key="tg_r"),
              "posts": c[1].number_input("Bài viết", 0, 50, int(tg["posts"]), key="tg_p"),
              "stories": c[2].number_input("Tin", 0, 50, int(tg["stories"]), key="tg_s"),
              "replies": c[3].number_input("Trả lời bình luận", 0, 50, int(tg["replies"]), key="tg_c")}
        if st.button("Lưu chỉ tiêu", key="tg_save"):
            pg["targets"] = {k: int(v) for k, v in nt.items()}
            _save_page(S, pg)
            st.rerun()
        st.caption("Facebook đổi nhiệm vụ mỗi tuần (Chủ nhật). Số đã làm tool đọc thẳng từ trang; "
                   "bài viết tính cả Reels.")
    if R.get("cmt_err"):
        st.caption(f"Không đọc được bình luận: {R['cmt_err'][:150]}")
    if ncm:
        with st.expander(f"Trả lời {ncm} bình luận"):
            for c in R["comments"]:
                st.markdown(f"**{c['who']}** · {c['time']} · *{c['post']}*\n\n> {c['message'] or '(nhãn dán/ảnh)'}")
                a, b = st.columns([5, 1])
                txt = a.text_input("Trả lời", key=f"rp_{c['id']}", label_visibility="collapsed",
                                   placeholder="Nhập câu trả lời...")
                if b.button("Gửi", key=f"rs_{c['id']}", disabled=not txt.strip()):
                    try:
                        facebook.reply_comment(c["id"], pg["token"], txt.strip(), ver)
                        st.success("Đã trả lời")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(facebook.safe(e))
                if c.get("link"):
                    st.caption(f"[Mở bài trên Facebook]({c['link']})")


# ------------------------------- cài đặt đăng -------------------------------
def _settings(S, pg):
    with st.expander("Cài đặt đăng cho trang này", expanded=not pg.get("folder")):
        fd = st.text_input("Thư mục gốc RIÊNG của trang này (trong có CHƯA UP / ĐÃ UP / VIDEO LỖI)",
                          pg.get("folder") or "", placeholder=r"Ví dụ D:\REUP")
        c1, c2 = st.columns(2)
        story = c1.toggle("Đăng kèm vào Tin (Story) lúc tới giờ", bool(pg.get("story")),
                          help="Giúp làm nhiệm vụ 'Tạo tin mới'. Tin không hẹn giờ trước được nên máy phải bật lúc "
                               "tới giờ. Chỉ video từ 60 giây trở xuống.")
        tags = c2.text_input("Hashtag luôn có", pg.get("hashtags") or "lamvuon, meolamvuon")
        guide = st.text_area("Hướng dẫn riêng cho AI viết caption trang này (không bắt buộc)",
                             pg.get("caption_guide") or "", height=80,
                             placeholder="Ví dụ: xưng 'em', gọi 'bà con'; luôn kết bằng câu mời theo dõi trang.")
        mx = st.number_input("Caption tối đa (ký tự)", 40, 1500, int(pg.get("caption_max") or 350), 10,
                             help="Từ 160 trở xuống AI chỉ viết 1-2 câu ngắn. Sửa xong bấm Lưu rồi Viết lại caption.")
        if st.button("Lưu cài đặt trang", type="primary", key="fb_pg_save"):
            other = next((p["name"] for p in fbq.pages(S) if p["name"] != pg["name"] and fd.strip()
                          and (p.get("folder") or "").strip().lower() == fd.strip().lower()), "")
            if other:
                st.error(f"Thư mục này đang dùng cho trang «{other}». Mỗi trang 1 thư mục riêng để không đăng nhầm.")
                return
            pg.update(folder=fd.strip(), story=bool(story),
                      hashtags=tags.strip(), caption_guide=guide.strip(), caption_max=int(mx))
            _save_page(S, pg)
            try:
                fbq.ensure_folders(pg)
            except Exception as e:
                st.error(f"Không tạo được thư mục: {e}")
            st.success("Đã lưu")
            st.rerun()
        st.caption(f"Tool đẩy video lên Facebook trước giờ đăng tối đa {S.get('fb_max_ahead_days', 2)} ngày, "
                   "Facebook tự giữ lịch nên tới giờ máy tắt vẫn đăng. Đăng xong video được chuyển sang ĐÃ UP.")


# ------------------------------- phân tích + duyệt -------------------------------
def _plan(S, pg):
    """Lịch đăng: từ ngày - đến ngày, khung giờ chung hoặc riêng từng thứ, xếp lại giờ cho video chưa đẩy lên FB."""
    jobs = [j for j in db.list_jobs(["draft", "pending"], "facebook", pg["name"])]
    with st.expander("Lịch đăng: từ ngày, đến ngày, khung giờ từng thứ", expanded=False):
        p_from, p_to = fbq.plan_range(pg)
        today = datetime.now().date()
        a, b, c = st.columns(3)
        d0 = a.date_input("Từ ngày", max(p_from or today, today), format="DD/MM/YYYY", key="fpl_d0")
        lim = b.toggle("Giới hạn đến ngày", bool(p_to), key="fpl_lim")
        d1 = c.date_input("Đến ngày", p_to or today + timedelta(days=13), format="DD/MM/YYYY", key="fpl_d1",
                          disabled=not lim)
        mode = st.radio("Khung giờ", ["chung", "thu"], horizontal=True, index=1 if pg.get("by_day") else 0,
                        key="fpl_mode", format_func={"chung": "Giống nhau mọi ngày",
                                                     "thu": "Riêng từng thứ trong tuần"}.get)
        tbd = dict(pg.get("times_by_day") or {})
        if mode == "chung":
            tm = st.text_input("Giờ đăng mỗi ngày (cách nhau dấu phẩy, mỗi giờ 1 video)", pg.get("times") or "11:30, 19:30",
                               key="fpl_times")
        else:
            st.caption("Mỗi giờ là 1 video, cách nhau dấu phẩy. Để trống = ngày đó nghỉ, không đăng.")
            cols = st.columns(7)
            for i, wd in enumerate(fbq.WEEKDAYS):
                tbd[str(i)] = cols[i].text_input(wd, tbd.get(str(i), pg.get("times") or "11:30, 19:30"),
                                                 key=f"fpl_w{i}")
            tm = pg.get("times") or "11:30, 19:30"
        sel = [j["id"] for j in jobs if st.session_state.get(f"fsel_{j['id']}")]
        scope = st.radio("Xếp lại giờ cho", ["all", "sel"], horizontal=True, key="fpl_scope",
                         format_func={"all": f"Tất cả video chưa đẩy lên Facebook ({len(jobs)})",
                                      "sel": f"Video đang chọn ({len(sel)})"}.get)
        new_pg = {**pg, "times": ", ".join(fbq.parse_times(tm)) or "11:30, 19:30", "by_day": mode == "thu",
                  "times_by_day": {k: ", ".join(fbq.parse_times(v)) for k, v in tbd.items()},
                  "plan_from": d0.isoformat(), "plan_to": d1.isoformat() if lim else ""}
        per_week = sum(len(fbq.times_for(new_pg, d0 + timedelta(days=i))) for i in range(7))
        st.caption(f"Lịch này đăng **{per_week} video/tuần**. Lưu xong, video phân tích sau cũng tự xếp theo lịch này.")
        x, y = st.columns(2)
        if x.button("Lưu lịch", key="fpl_save"):
            _save_page(S, new_pg)
            st.success("Đã lưu lịch")
            st.rerun()
        target = jobs if scope == "all" else [j for j in jobs if j["id"] in sel]
        if y.button(f"Lưu lịch và xếp lại giờ ({len(target)} video)", type="primary", key="fpl_go",
                    disabled=not target or per_week == 0):
            _save_page(S, new_pg)
            start = max(datetime.combine(d0, datetime.min.time()), datetime.now() + timedelta(minutes=30))
            ok, miss = fbq.replan(new_pg, target, start, d1 if lim else None)
            st.success(f"Đã xếp {ok} video." + (f" {miss} video không đủ chỗ trong khoảng ngày này "
                                                 "(chưa có giờ): kéo dài 'Đến ngày' hoặc thêm khung giờ." if miss else ""))
            st.rerun()
        rows = {}
        for j in db.list_jobs(["draft", "pending", "scheduled_fb"], "facebook", pg["name"]):
            if j.get("scheduled_at") and j["scheduled_at"] >= datetime.now().strftime("%Y-%m-%d"):
                d, t = j["scheduled_at"].split(" ")
                rows.setdefault(d, []).append(t + ("" if j["status"] != "scheduled_fb" else " (đã lên FB)"))
        if rows:
            import pandas as pd
            st.dataframe(pd.DataFrame([{"Ngày": fbq.WEEKDAYS[datetime.strptime(d, "%Y-%m-%d").weekday()] + " "
                                        + datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m"),
                                        "Số video": len(v), "Giờ đăng": "  ·  ".join(sorted(v))}
                                       for d, v in sorted(rows.items())]), hide_index=True, width="stretch")
        no_time = [j for j in jobs if not j.get("scheduled_at")]
        if no_time:
            st.warning(f"{len(no_time)} video chưa có giờ đăng (không đủ chỗ trong lịch).")
        st.caption("Video đã đẩy lên Facebook (đã lên FB) thì đổi giờ trong Meta Business Suite.")


def _new(S, pg):
    if not pg.get("folder"):
        st.info("Trang này chưa chọn thư mục video. Mở mục **Cài đặt đăng cho trang này** ở trên, "
                "nhập thư mục riêng của trang rồi bấm Lưu.")
        return
    vids = fbq.new_videos(pg)
    nan = len(db.list_jobs(["analyzing"], "facebook", pg["name"]))
    st.markdown(f"### Đăng video mới\n**{len(vids)}** video mới trong `{fbq.folder(pg)}`"
                + (f" · {nan} video đang phân tích" if nan else ""))
    if st.button("Mở thư mục CHƯA UP", key="fb_open"):
        _open_folder(fbq.folder(pg))
    if not vids:
        return
    opts = list(MODELS) + [NO_AI]
    dm = S.get("ai_model") if S.get("ai_model") in MODELS and ai_key(S, S.get("ai_model")) else NO_AI
    a, b = st.columns([3, 1])
    model = a.selectbox("Mức AI viết caption", opts, index=opts.index(dm), key="fb_model",
                        format_func=lambda m: MODELS.get(m, "Không dùng AI · caption mẫu (miễn phí)"))
    today = datetime.now().date()
    per_week = sum(len(fbq.times_for(pg, today + timedelta(days=i))) for i in range(7)) or 7
    n = b.number_input("Số video", 1, len(vids), min(len(vids), per_week), key="fb_n",
                       help=f"Mặc định đủ 1 tuần theo lịch đăng ({per_week} video/tuần).")
    has_key = model == NO_AI or bool(ai_key(S, model))
    if not has_key:
        st.error("Chưa có API key cho mức AI này → vào tab Cài đặt dán key, hoặc chọn mức khác.")
    if st.button(f"Phân tích {n} video", type="primary", disabled=not has_key, key="fb_go"):
        for v in vids[:n]:
            db.add_job(platform="facebook", channel=pg["name"], video_path=str(v), status="analyzing",
                       ai_model=model, fb_story=1 if pg.get("story") else 0)
        worker.start()
        st.success(f"Đã đưa {n} video vào phân tích. Xong video nào hiện ngay bên dưới để bác duyệt.")
        st.rerun()


def _cover_picker(j):
    """Chọn ảnh bìa: 1 khung hình trong video, tự tải ảnh lên, hoặc để Facebook tự chọn."""
    from . import analyze as ana
    from .config import WORK_DIR
    with st.expander("Ảnh bìa"):
        frames = [(i, f) for i, f in enumerate(j.get("frames") or []) if Path(f.get("thumb", "")).exists()][:8]
        if frames:
            cols = st.columns(len(frames))
            for c_, (i, f) in zip(cols, frames):
                c_.image(f["thumb"], width="stretch")
                if c_.button(f"Khung {i + 1}", key=f"fcv_{j['id']}_{i}"):
                    try:
                        db.update_job(j["id"], cover_path=ana.set_cover(j, i), cover_by_user=1)
                    except Exception as e:
                        st.error(f"Không cắt được khung: {e}")
                    st.rerun()
        up = st.file_uploader("Hoặc tải ảnh bìa lên (dọc 9:16 đẹp nhất)", type=["jpg", "jpeg", "png", "webp"],
                              key=f"fup_{j['id']}")
        a, b = st.columns(2)
        if up is not None and a.button("Dùng ảnh này", key=f"fupok_{j['id']}", type="primary"):
            from PIL import Image, ImageOps
            import io
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(up.getvalue()))).convert("RGB")
            im.thumbnail((1080, 1920))
            out = WORK_DIR / str(j["id"]) / "cover_rieng.jpg"
            out.parent.mkdir(parents=True, exist_ok=True)
            im.save(out, "JPEG", quality=90)
            db.update_job(j["id"], cover_path=str(out), cover_by_user=1)
            st.rerun()
        if int(j.get("cover_by_user") or 0) and b.button("Để Facebook tự chọn bìa", key=f"fcvoff_{j['id']}"):
            db.update_job(j["id"], cover_by_user=0)
            st.rerun()


def _review(S, pg):
    drafts = sorted(db.list_jobs(["draft"], "facebook", pg["name"]), key=lambda j: j.get("scheduled_at") or "z")
    busy = len(db.list_jobs(["analyzing"], "facebook", pg["name"]))
    if busy:
        worker.start()

        def _wait():  # tự kiểm tra 3 giây/lần, AI viết xong thì tải lại để hiện caption mới
            left = len(db.list_jobs(["analyzing"], "facebook", pg["name"]))
            if left:
                st.info(f"AI đang viết {left} caption... xong sẽ tự hiện, bác không cần bấm gì.")
            else:
                st.rerun(scope="app")
        st.fragment(run_every=3)(_wait)()
    if not drafts:
        return
    st.markdown(f"### Chờ duyệt ({len(drafts)} video)")
    c = st.columns([2, 2, 2])
    if c[2].button(f"Viết lại caption cả đợt ({len(drafts)})", key="fb_redo_all",
                   help="AI viết lại theo giới hạn ký tự và hướng dẫn riêng đang lưu. Giữ nguyên giờ đăng."):
        for j in drafts:
            db.update_job(j["id"], status="analyzing", redo_caption=1)
        worker.start()
        st.rerun()
    if c[0].button(f"Xác nhận tất cả {len(drafts)} video", type="primary", key="fb_all"):
        for j in drafts:
            if j.get("scheduled_at"):
                db.update_job(j["id"], status="pending", reviewed=1)
        st.rerun()
    story_all = c[1].toggle("Đăng kèm vào Tin cho cả đợt", all(int(j.get("fb_story") or 0) for j in drafts),
                            key="fb_story_all")
    if story_all != all(int(j.get("fb_story") or 0) for j in drafts):
        for j in drafts:
            db.update_job(j["id"], fb_story=1 if story_all else 0)
        st.rerun()
    for j in drafts[:30]:
        with st.container(border=True):
            l, r = st.columns([1, 4])
            l.checkbox("Chọn", key=f"fsel_{j['id']}")
            own = int(j.get("cover_by_user") or 0)
            if j.get("cover_path") and Path(j["cover_path"]).exists():
                l.image(j["cover_path"], width="stretch")
            l.caption("Bìa: tự chọn" if own else "Bìa: Facebook tự chọn")
            r.markdown(f"**{Path(j['video_path']).name}** · {j.get('ai_note') or ''}")
            v = abs(hash((j.get("caption"), j.get("hashtags"), j.get("scheduled_at")))) % 10**8  # đổi nội dung -> ô mới
            capt = r.text_area("Caption", j.get("caption") or "", key=f"fc_{j['id']}_{v}", height=130)
            x, y, z = r.columns([3, 2, 2])
            tags = x.text_input("Hashtag", j.get("hashtags") or "", key=f"fh_{j['id']}_{v}")
            try:
                t0 = datetime.strptime(j["scheduled_at"], FMT)
            except Exception:
                t0 = datetime.now() + timedelta(hours=1)
            d = y.date_input("Ngày", t0.date(), format="DD/MM/YYYY", key=f"fd_{j['id']}_{v}")
            tm = z.time_input("Giờ", t0.time(), step=300, key=f"ft_{j['id']}_{v}")
            r.caption(f"{len(capt)} ký tự")
            s1, s2, s3, s4, s5 = r.columns(5)
            sto = s1.checkbox("Kèm Tin", bool(int(j.get("fb_story") or 0)), key=f"fs_{j['id']}_{v}")
            new = dict(caption=capt, hashtags=tags, scheduled_at=datetime.combine(d, tm).strftime(FMT),
                       fb_story=1 if sto else 0)
            if s2.button("Xác nhận", key=f"fok_{j['id']}", type="primary"):
                db.update_job(j["id"], status="pending", reviewed=1, **new)
                st.rerun()
            if s3.button("Lưu", key=f"fsv_{j['id']}"):
                db.update_job(j["id"], **new)
                st.rerun()
            if s5.button("Viết lại", key=f"fre_{j['id']}"):
                db.update_job(j["id"], status="analyzing", redo_caption=1, hashtags=tags,
                              scheduled_at=new["scheduled_at"], fb_story=new["fb_story"])
                worker.start()
                st.rerun()
            if s4.button("Bỏ video", key=f"fdel_{j['id']}"):
                db.delete_jobs([j["id"]])
                st.rerun()
            _cover_picker(j)
    if len(drafts) > 30:
        st.caption(f"Còn {len(drafts) - 30} video nữa, duyệt xong đợt này sẽ hiện tiếp.")


def _queue(pg):
    rows = sorted(db.list_jobs(["pending", "running", "scheduled_fb", "error"], "facebook", pg["name"]),
                  key=lambda j: j.get("scheduled_at") or "")
    upcoming = [j for j in rows if j["status"] != "error" and (j.get("scheduled_at") or "") >= datetime.now().strftime(FMT)]
    errs = [j for j in rows if j["status"] == "error"]
    if upcoming:
        st.markdown(f"### Lịch đăng sắp tới ({len(upcoming)} video)")
        lines = []
        for j in upcoming[:14]:
            t = datetime.strptime(j["scheduled_at"], FMT)
            lines.append(f"- {t:%a %d/%m %H:%M} · {Path(j['video_path']).name} · "
                         f"{db.STATUS_LABELS.get(j['status'], j['status'])}"
                         + (" · kèm Tin" if int(j.get("fb_story") or 0) else ""))
        st.markdown("\n".join(lines).replace("Mon", "T2").replace("Tue", "T3").replace("Wed", "T4")
                    .replace("Thu", "T5").replace("Fri", "T6").replace("Sat", "T7").replace("Sun", "CN"))
        if upcoming[-1:]:
            last = datetime.strptime(upcoming[-1]["scheduled_at"], FMT)
            st.caption(f"Đã có lịch tới {last:%d/%m}. Còn {len(fbq.new_videos(pg))} video chưa phân tích.")
    if errs:
        with st.expander(f"{len(errs)} video lỗi"):
            for j in errs[-10:]:
                st.markdown(f"- **{Path(j['video_path']).name}**: {j.get('result', '')[:200]}")
            if st.button("Đăng lại các video lỗi (xếp giờ mới)", key="fb_retry"):
                slots = fbq.next_slots(pg, len(errs))
                for j, t in zip(errs, slots):
                    db.update_job(j["id"], status="pending", scheduled_at=t.strftime(FMT), result="")
                st.rerun()


def render(S):
    pages = fbq.pages(S)
    ready = [p for p in pages if p.get("token") and str(p.get("page_id", "")).isdigit()]
    if not ready:
        st.markdown("## Kết nối trang Facebook")
        if pages:
            st.caption("Trang " + ", ".join(p["name"] for p in pages) + " chưa có mã kết nối.")
        _connect(S)
        return
    names = [p["name"] for p in ready]
    a, b = st.columns([3, 1])
    first = next((i for i, p in enumerate(ready) if p.get("folder")), 0)
    name = a.selectbox("Trang", names, index=first, key="fb_page") if len(names) > 1 else names[0]
    if len(names) == 1:
        a.markdown(f"## {name}")
    with b.popover("Kết nối lại / thêm trang"):
        _connect(S)
    pg = fbq.page(S, name)
    _tasks(S, pg)
    st.divider()
    _settings(S, pg)
    _plan(S, pg)
    _new(S, pg)
    _review(S, pg)
    _queue(pg)
