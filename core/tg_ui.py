"""Giao diện: Cài đặt → Thông báo Telegram, và tab Báo lỗi Admin."""
import json
import platform
import re
import socket
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path

import streamlit as st

from . import db
from . import telegram as tg
from .config import DATA_DIR, DEBUG_DIR, LOG_DIR, RUNNER_LOG, save_settings

CLAUDE_SESSION = "https://claude.ai/code/session_01QfCiLvvLcZ1YWKz9qkP5G1"  # phiên Claude Code làm ra Sonix Up Video
REPORT_DIR = DATA_DIR / "bao_loi"
SHOT_DIR = REPORT_DIR / "anh_cho_gui"
KIND_LABEL = {"su_co": "Sự cố", "xong": "Đã làm xong", "cap_nhat": "Có bản cập nhật"}
APP_LABEL = {"up": "Sonix Up Video", "edit": "Sonix Edit Video"}
SECRET = re.compile(r"token|key|pass|secret|cookie|tg_bot|pin", re.I)


# =============================== CÀI ĐẶT TELEGRAM ===============================
def render_settings(S):
    st.subheader("Thông báo Telegram")
    st.caption("Tool nhắn về Telegram khi: có **sự cố** (kèm ảnh chụp lỗi + video quay màn hình), **làm xong** việc, "
               "**có bản cập nhật**. Tin có nhãn riêng [Sonix Up Video] / [Sonix Edit Video] để dễ phân biệt.")
    if not tg.ready(S):
        _setup_bot(S)
        return
    try:
        me = _bot_cached(S["tg_bot"])
        st.success(f"Đã nối bot **@{me.get('username')}**.")
    except Exception as e:
        st.error(f"Bot không dùng được: {tg._safe(e)}")
    with st.popover("Đổi / gỡ bot"):
        st.write("Gỡ bot thì tool ngừng gửi tin. Danh sách người nhận vẫn giữ.")
        if st.button("Gỡ bot", key="tg_unset"):
            S["tg_bot"] = ""
            save_settings(S)
            st.rerun()
    _receivers(S)
    q = st.toggle("Quay màn hình lúc đăng TikTok để gửi kèm khi có sự cố", value=bool(S.get("tg_quay", True)),
                  key="tg_quay_t", help="Chỉ gửi khi đăng lỗi; đăng xong bình thường thì tool tự xoá video quay. "
                                        "Tốn thêm chút CPU lúc đăng.")
    if q != bool(S.get("tg_quay", True)):
        S["tg_quay"] = q
        save_settings(S)
    _admin_box(S)


@st.cache_data(ttl=3600, show_spinner=False)
def _bot_cached(token):
    return tg.bot_info(token)


def _setup_bot(S):
    st.info("Chưa nối bot Telegram. Chọn 1 trong 2 cách:")
    a, b = st.columns(2)
    with a.container(border=True):
        st.markdown("**Cách 1 · Admin gửi mã kết nối** (người dùng thường)")
        code = st.text_input("Dán mã kết nối Sonix (bắt đầu bằng SONIX-)", key="tg_share_in", type="password")
        if st.button("Nối", key="tg_share_ok", disabled=not code):
            try:
                cfg = tg.read_share_code(code)
                tg.bot_info(cfg["tg_bot"])
                S.update(cfg)
                save_settings(S)
                st.rerun()
            except Exception as e:
                st.error(tg._safe(e))
    with b.container(border=True):
        st.markdown("**Cách 2 · Tự tạo bot** (Admin)")
        st.markdown("1. Mở Telegram, tìm **@BotFather**, gõ `/newbot`, đặt tên (vd *Sonix Auto bot*).  \n"
                    "2. BotFather gửi lại 1 **mã bot** dạng `123456:ABC...`. Dán vào ô dưới (mã chỉ lưu trên máy này).")
        tok = st.text_input("Mã bot", key="tg_tok_in", type="password")
        if st.button("Kiểm tra & lưu", key="tg_tok_ok", disabled=not tok):
            try:
                me = tg.bot_info(tok.strip())
                S["tg_bot"] = tok.strip()
                save_settings(S)
                st.success(f"Đã nối bot @{me.get('username')}")
                st.rerun()
            except Exception as e:
                st.error(tg._safe(e))


def _receivers(S):
    rs = S.setdefault("tg_nguoi_nhan", [])
    st.markdown(f"**Người nhận ({len(rs)})**")
    for i, r in enumerate(list(rs)):
        with st.container(border=True):
            c = st.columns([1.4, 2, 1.6, 0.8, 0.8])
            c[0].markdown(f"**{r.get('name')}**" + ("  \nAdmin (nhận Báo lỗi)" if str(r.get("chat_id")) ==
                                                     str(S.get("tg_admin_chat")) else ""))
            kinds = c[1].multiselect("Loại tin", list(KIND_LABEL), default=r.get("kinds") or list(KIND_LABEL),
                                     format_func=KIND_LABEL.get, key=f"tgk_{i}_{r['chat_id']}")
            apps = c[2].multiselect("Mục", list(APP_LABEL), default=r.get("apps") or list(APP_LABEL),
                                    format_func=APP_LABEL.get, key=f"tga_{i}_{r['chat_id']}")
            if kinds != r.get("kinds") or apps != r.get("apps"):
                r["kinds"], r["apps"] = kinds, apps
                save_settings(S)
            if c[3].button("Gửi thử", key=f"tgt_{i}_{r['chat_id']}"):
                try:
                    tg.send_to(S["tg_bot"], r["chat_id"], "up", "xong", "Tin nhắn thử",
                               "Nối Telegram thành công. Từ giờ tool báo sự cố / việc xong / bản cập nhật về đây.")
                    st.toast("Đã gửi, bác xem Telegram.")
                except Exception as e:
                    st.error(tg._safe(e))
            with c[4].popover("Bỏ"):
                if st.button("Bỏ người nhận này", key=f"tgd_{i}_{r['chat_id']}", type="primary"):
                    rs.pop(i)
                    save_settings(S)
                    st.rerun()
    with st.expander("Thêm người nhận (Telegram của bác hoặc người khác)", expanded=not rs):
        code = st.session_state.setdefault("tg_link_code", tg.new_link_code())
        try:
            url = tg.link_url(S, code)
        except Exception as e:
            st.error(tg._safe(e))
            return
        st.markdown("1. Người nhận bấm nút dưới (hoặc quét bằng điện thoại), Telegram mở ra bot, bấm **Start / Bắt đầu**.  \n"
                    "2. Quay lại đây bấm **Đã bấm Start**.")
        c = st.columns([1, 1, 2])
        c[0].link_button("Mở Telegram", url, type="primary")
        if c[1].button("Đã bấm Start", key="tg_find"):
            try:
                found = tg.find_chat(S, code)
            except Exception as e:
                found = None
                st.error(tg._safe(e))
            if found:
                if not any(str(x["chat_id"]) == found["chat_id"] for x in rs):
                    rs.append({**found, "kinds": list(KIND_LABEL), "apps": list(APP_LABEL), "on": True})
                    save_settings(S)
                st.session_state.pop("tg_link_code", None)
                try:
                    tg.send_to(S["tg_bot"], found["chat_id"], "up", "xong", "Đã nối Telegram với Sonix Auto",
                               "Từ giờ bác nhận thông báo ở đây.")
                except Exception:
                    pass
                st.rerun()
            else:
                st.warning("Chưa thấy. Bác bấm Start trong Telegram chưa? Đợi vài giây rồi bấm lại.")
        c[2].code(url, language=None)


def _admin_box(S):
    rs = S.get("tg_nguoi_nhan") or []
    with st.expander("Admin: nhận Báo lỗi + mã kết nối cho người dùng khác"):
        if rs:
            opts = [""] + [str(r["chat_id"]) for r in rs]
            names = {str(r["chat_id"]): r.get("name") for r in rs}
            cur = str(S.get("tg_admin_chat") or "")
            sel = st.selectbox("Telegram nhận tin «Sự cố người dùng»", opts + ([cur] if cur and cur not in opts else []),
                               index=(opts + ([cur] if cur and cur not in opts else [])).index(cur),
                               format_func=lambda x: names.get(x, x) or "— chưa chọn", key="tg_admin_sel")
            if sel != cur:
                S["tg_admin_chat"] = sel
                save_settings(S)
        if S.get("tg_admin_chat"):
            st.markdown("**Mã kết nối Sonix** · gửi RIÊNG cho người dùng khác (Zalo/Telegram). Họ dán vào Cài đặt → "
                        "Thông báo Telegram là dùng chung bot, và Báo lỗi của họ gửi thẳng về Telegram Admin. "
                        "**Đừng đăng mã này công khai** (ai có mã cũng nhắn được qua bot).")
            if st.toggle("Hiện mã", key="tg_show_share"):
                st.code(tg.make_share_code(S), language=None)
        else:
            st.caption("Chọn Telegram Admin ở trên trước (thêm người nhận rồi chọn).")


# =============================== BÁO LỖI ADMIN ===============================
def _find_app_window():
    """Toạ độ cửa sổ app Sonix (chỉ cửa sổ app, không chụp cả màn hình)."""
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    try:
        u.SetProcessDPIAware()
    except Exception:
        pass
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _):
        if u.IsWindowVisible(h) and not u.IsIconic(h):
            n = u.GetWindowTextLengthW(h)
            if n:
                b = ctypes.create_unicode_buffer(n + 1)
                u.GetWindowTextW(h, b, n + 1)
                if "Sonix" in b.value:
                    r = wintypes.RECT()
                    u.GetWindowRect(h, ctypes.byref(r))
                    if r.right - r.left > 300 and r.bottom - r.top > 200:
                        found.append((h, (r.left, r.top, r.right, r.bottom)))
        return True
    u.EnumWindows(cb, 0)
    fg = u.GetForegroundWindow()
    for h, box in found:  # ưu tiên cửa sổ đang mở trước mặt
        if h == fg:
            return box
    return found[0][1] if found else None


def _shoot_later(delay):
    def run():
        time.sleep(delay)
        try:
            from PIL import ImageGrab
            box = _find_app_window()
            if not box:
                return
            SHOT_DIR.mkdir(parents=True, exist_ok=True)
            ImageGrab.grab(bbox=box, all_screens=True).save(SHOT_DIR / f"cua_so_{datetime.now():%H%M%S}.png")
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


def _tail(path, n=400) -> str:
    try:
        return "\n".join(Path(path).read_text(encoding="utf-8", errors="replace").splitlines()[-n:])
    except Exception:
        return ""


def _clean_settings(x):
    if isinstance(x, dict):
        return {k: ("***" if SECRET.search(k) and v else _clean_settings(v)) for k, v in x.items()}
    if isinstance(x, list):
        return [_clean_settings(v) for v in x]
    return x


def build_bundle(S, app, info: dict, shots) -> Path:
    """Gói nhật ký gửi Admin. KHÔNG có mã bot, token, API key, mật khẩu, cookie."""
    from .updater import local_version
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"bao_loi_{datetime.now():%Y%m%d_%H%M%S}.zip"
    jobs = db.list_jobs()
    counts = {}
    for j in jobs:
        counts[j["status"]] = counts.get(j["status"], 0) + 1
    errs = [{k: j.get(k) for k in ("id", "platform", "channel", "status", "scheduled_at", "result", "updated_at")}
            | {"file": Path(j.get("video_path") or "").name}
            for j in sorted(jobs, key=lambda j: j.get("updated_at") or "", reverse=True)
            if j["status"] in ("error", "check")][:40]
    meta = {**info, "app": APP_LABEL.get(app, app), "version": local_version(), "may": socket.gethostname(),
            "he_dieu_hanh": platform.platform(), "python": platform.python_version(),
            "luc": f"{datetime.now():%d/%m/%Y %H:%M:%S}", "hang_cho": counts, "viec_loi_gan_day": errs}
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("thong_tin.json", json.dumps(meta, ensure_ascii=False, indent=1))
        z.writestr("cai_dat_da_che.json", json.dumps(_clean_settings(S), ensure_ascii=False, indent=1))
        z.writestr("runner.log", _tail(RUNNER_LOG, 3000))
        for f in LOG_DIR.glob("*.log"):
            if f.name != "runner.log":
                z.writestr(f"logs/{f.name}", _tail(f, 800))
        edit_logs = sorted((DATA_DIR / "edit" / "viec").glob("*.log"), key=lambda p: p.stat().st_mtime)[-6:] \
            if (DATA_DIR / "edit" / "viec").is_dir() else []
        for f in edit_logs:
            z.writestr(f"edit/{f.name}", _tail(f, 400))
        for f in sorted(DEBUG_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime)[-12:] if DEBUG_DIR.is_dir() else []:
            z.write(f, f"anh_loi_tool/{f.name}")
        try:
            z.writestr("tien_do.json", (DATA_DIR / "tien_do.json").read_text(encoding="utf-8"))
        except Exception:
            pass
        for i, p in enumerate(shots):
            z.write(p, f"anh_nguoi_dung/{i + 1}_{Path(p).name}")
    return out


def _ai_quick(S, desc, bundle_text):
    from .analyze import _claude, _gemini
    from .config import MODELS, ai_key
    m = S.get("ai_model")
    if m not in MODELS or not ai_key(S, m):
        raise RuntimeError("Chưa cài Mức AI / khoá AI ở Cài đặt")
    schema = {"type": "object", "additionalProperties": False, "required": ["chan_doan", "cach_xu_ly", "can_admin"],
              "properties": {"chan_doan": {"type": "string"}, "cach_xu_ly": {"type": "array", "items": {"type": "string"}},
                             "can_admin": {"type": "boolean"}}}
    system = ("Bạn là người hỗ trợ kỹ thuật của app Sonix Auto (đăng video TikTok/Facebook tự động bằng trình duyệt, "
              "dựng video CapCut). Đọc mô tả lỗi + nhật ký, chẩn đoán ngắn gọn bằng tiếng Việt dễ hiểu cho nông dân "
              "không rành máy tính, đưa các bước tự xử lý trên app (bấm nút nào, ở tab nào). Nếu là lỗi code của app "
              "thì can_admin = true.")
    content = [{"type": "text", "text": f"Mô tả của người dùng:\n{desc}\n\nNhật ký gần nhất:\n{bundle_text[-6000:]}"}]
    fn = _gemini if str(m).startswith("gemini") else _claude
    return fn(content, schema, S, m, system)


def render_bao_loi(S, app="up"):
    st.subheader("Báo lỗi với Admin")
    st.caption("Gặp lỗi khi dùng app? Chụp màn hình lỗi, ghi rõ tình trạng, bấm Gửi. Tool gửi kèm nhật ký sử dụng về "
               "Telegram của Admin (tin «Sự cố người dùng»). Gói nhật ký **không** có mật khẩu, token, khoá AI.")
    k = f"bl_{app}"
    who = st.text_input("Tên bác / tên kênh (để Admin biết ai báo)", value=S.get("bl_ten", ""), key=f"{k}_ten")
    loai = st.selectbox("Lỗi xảy ra ở đâu", ["Đăng video TikTok", "Đăng Facebook", "Duyệt / phân tích video",
                                              "Ảnh bìa", "Âm thanh / nhạc", "Edit video / CapCut", "Cập nhật app",
                                              "App chậm / treo", "Khác"], key=f"{k}_loai")
    desc = st.text_area("Mô tả lỗi: đang làm gì, bấm nút nào, lỗi hiện ra sao, từ lúc nào",
                        key=f"{k}_mota", height=130,
                        placeholder="Vd: Sáng nay bấm Xác nhận đăng 5 video kênh Phân Bón Cà Phê, tới bước gắn sản phẩm "
                                    "thì báo lỗi đỏ ..., video chuyển vào VIDEO LỖI.")
    st.markdown("**Ảnh chụp màn hình lỗi**")
    c = st.columns([1.2, 2])
    with c[0]:
        if st.button("Chụp cửa sổ app sau 8 giây", key=f"{k}_shot",
                     help="Bấm xong, trong 8 giây bác chuyển sang chỗ đang lỗi trong app. Tool chỉ chụp cửa sổ app "
                          "Sonix, không chụp màn hình khác."):
            _shoot_later(8)
            st.toast("8 giây nữa tool chụp cửa sổ app. Bác chuyển sang chỗ đang lỗi ngay.")
        st.caption("Hoặc tự chụp (phím Windows + Shift + S, rồi lưu ảnh) và tải lên bên phải.")
    ups = c[1].file_uploader("Tải ảnh chụp lỗi lên", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True,
                             key=f"{k}_up")
    shots = sorted(SHOT_DIR.glob("*.png")) if SHOT_DIR.is_dir() else []
    if shots:
        cols = st.columns(min(4, len(shots)))
        for i, p in enumerate(shots[-8:]):
            with cols[i % len(cols)]:
                st.image(str(p), width="stretch")
                if st.button("Bỏ ảnh", key=f"{k}_rm_{p.name}"):
                    p.unlink(missing_ok=True)
                    st.rerun()
    st.button("Tải lại để xem ảnh vừa chụp", key=f"{k}_reload")
    ok_tg = tg.ready(S) and S.get("tg_admin_chat")
    b = st.columns([1, 1, 2])
    send = b[0].button("Gửi báo lỗi cho Admin", key=f"{k}_send", type="primary", disabled=not desc.strip())
    ai = b[1].button("Nhờ AI xem nhanh", key=f"{k}_ai", disabled=not desc.strip(),
                     help="AI (Mức AI mặc định ở Cài đặt) đọc mô tả + nhật ký và gợi ý cách tự xử lý. Chỉ gửi chữ, rất rẻ.")
    if not ok_tg:
        b[2].caption("Chưa nối Telegram Admin (Cài đặt → Thông báo Telegram → dán mã kết nối Admin gửi). "
                     "Vẫn bấm Gửi được: tool tạo gói nhật ký để bác tải về gửi Zalo cho Admin.")
    if ai:
        with st.spinner("AI đang đọc nhật ký..."):
            try:
                r = _ai_quick(S, f"[{loai}] {desc}", _tail(RUNNER_LOG, 300))
                st.info("**AI chẩn đoán:** " + r.get("chan_doan", "") + "\n\n"
                        + "\n".join(f"{i + 1}. {x}" for i, x in enumerate(r.get("cach_xu_ly") or []))
                        + ("\n\nLỗi này nên báo Admin sửa: bấm **Gửi báo lỗi cho Admin**." if r.get("can_admin") else ""))
            except Exception as e:
                st.error(f"AI chưa xem được: {str(e)[:200]}")
    if send:
        if who != S.get("bl_ten", ""):
            S["bl_ten"] = who
            save_settings(S)
        tmp = []
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        for f in ups or []:
            safe = re.sub(r"[^\w.]+", "_", f.name)
            p = REPORT_DIR / f"tai_len_{int(time.time())}_{safe}"
            p.write_bytes(f.getvalue())
            tmp.append(p)
        imgs = [str(p) for p in shots[-8:]] + [str(p) for p in tmp]
        rid = datetime.now().strftime("%m%d%H%M%S")
        bundle = build_bundle(S, app, {"ma_bao_loi": rid, "nguoi_bao": who, "loai": loai, "mo_ta": desc}, imgs)
        st.session_state[f"{k}_last"] = str(bundle)
        if ok_tg:
            from .updater import local_version
            cap = (f"<b>Sự cố người dùng #{rid}</b>\n<b>[{APP_LABEL.get(app)}] {tg._esc(loai)}</b>\n"
                   f"Người báo: {tg._esc(who or '(không ghi)')} · máy {tg._esc(socket.gethostname())} · "
                   f"bản {local_version()}\n\n{tg._esc(desc[:550])}\n\n"
                   f"Xử lý bằng Claude Code: {CLAUDE_SESSION}\n"
                   f"(mở link, gõ «Sự cố người dùng #{rid}» và kéo tệp zip này vào)")
            try:
                with st.spinner("Đang gửi về Telegram Admin..."):
                    tg.send_to(S["tg_bot"], S["tg_admin_chat"], app, "bao_loi", "", photos=imgs, raw_caption=cap[:1020])
                    tg.send_to(S["tg_bot"], S["tg_admin_chat"], app, "bao_loi", "", document=str(bundle),
                               raw_caption=f"Gói nhật ký · Sự cố người dùng #{rid}")
                st.success(f"Đã gửi báo lỗi #{rid} cho Admin. Admin sẽ xem và xử lý.")
                for p in shots:
                    p.unlink(missing_ok=True)
            except Exception as e:
                st.error(f"Gửi Telegram lỗi: {tg._safe(e)}. Bác tải gói bên dưới gửi Zalo cho Admin.")
        else:
            st.success(f"Đã tạo gói báo lỗi #{rid}. Tải về gửi cho Admin.")
    last = st.session_state.get(f"{k}_last")
    if last and Path(last).exists():
        st.download_button("Tải gói báo lỗi (.zip)", Path(last).read_bytes(), file_name=Path(last).name,
                           key=f"{k}_dl")
