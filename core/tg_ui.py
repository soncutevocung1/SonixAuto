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
    st.subheader("Nhận thông báo về Telegram (tuỳ chọn)")
    st.caption("Ai muốn thì nối Telegram để nhận tin: có **sự cố** (kèm ảnh chụp lỗi + video quay màn hình), **làm xong** "
               "việc, **có bản cập nhật**. Tin có nhãn [Sonix Up Video] / [Sonix Edit Video]. Không nối cũng được: "
               "**Báo lỗi Admin không cần Telegram.**")
    if not tg.ready(S):
        _setup_bot(S)
        return
    try:
        me = _bot_cached(S["tg_bot"])
        st.success(f"Đã nối bot **@{me.get('username')}**." + (" Máy này là **Admin**." if tg.is_admin(S) else ""))
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
    if tg.is_admin(S):
        _admin_box(S)


def _qr(text):
    """Mã QR (ảnh PNG) để điện thoại quét. Chưa có thư viện segno thì bỏ qua."""
    try:
        import base64
        import segno
        return base64.b64decode(segno.make(text, error="m").png_data_uri(scale=8, border=2).split(",", 1)[1])
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def _bot_cached(token):
    return tg.bot_info(token)


def _setup_bot(S):
    st.info("Chưa nối Telegram. Chọn 1 trong 2 cách:")
    a, b = st.columns(2)
    with a.container(border=True):
        st.markdown("**Cách 1 · Dùng bot chung của Admin** (người dùng)")
        st.caption("Xin Admin «mã nhận thông báo» (bắt đầu bằng SONIX-), dán vào đây, rồi quét mã QR để nối Telegram.")
        code = st.text_input("Mã nhận thông báo", key="tg_share_in", type="password")
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
        st.markdown("**Cách 2 · Tự tạo bot riêng** (Admin, hoặc ai muốn bot riêng)")
        st.markdown("Làm trên **Telegram điện thoại**:  \n"
                    "1. Ô tìm kiếm gõ **BotFather** → chọn tài khoản có **dấu tick xanh** → bấm **BẮT ĐẦU / START**.  \n"
                    "2. Gõ `/newbot` gửi đi.  \n"
                    "3. Nó hỏi tên: gõ `Sonix Auto` gửi đi.  \n"
                    "4. Nó hỏi tên đăng nhập: gõ tên **không dấu, liền nhau, tận cùng bằng bot**, vd `sonixauto_son_bot` "
                    "(bị trùng thì thêm số: `sonixauto_son2_bot`).  \n"
                    "5. BotFather trả về 1 dòng **mã bot** dạng `8123456789:AAH...` (chữ màu, bấm vào là chép).  \n"
                    "6. Đưa mã sang máy tính: dán vào **Zalo → Cloud của tôi** trên điện thoại, mở Zalo máy tính chép ra, "
                    "dán vào ô dưới. Mã chỉ lưu trên máy này, **đừng gửi cho ai khác**.")
        tok = st.text_input("Mã bot", key="tg_tok_in", type="password")
        if st.button("Kiểm tra & lưu", key="tg_tok_ok", disabled=not tok):
            try:
                me = tg.bot_info(tok.strip())
                S["tg_bot"] = tok.strip()
                S.pop("tg_tu_ma", None)
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
        if rs and not st.toggle("Thêm 1 người nhận mới", key="tg_add_more"):
            return  # đã có người nhận: chỉ chờ Start khi bác bật thêm (đỡ hỏi Telegram liên tục)
        code = st.session_state.setdefault("tg_link_code", tg.new_link_code())
        try:
            url = f"https://t.me/{_bot_cached(S['tg_bot'])['username']}?start={code}"
        except Exception as e:
            st.error(tg._safe(e))
            return
        q, t = st.columns([1, 2])
        qr = _qr(url)
        if qr:
            q.image(qr, width=220, caption="Quét bằng camera điện thoại")
        t.markdown("**Telegram trên điện thoại:**  \n"
                   "1. Mở **camera** điện thoại (hoặc Zalo → quét mã QR), quét mã bên trái.  \n"
                   "2. Bấm vào đường link hiện ra → Telegram mở bot → bấm **BẮT ĐẦU / START** ở cuối màn hình.  \n"
                   "3. Xong. App **tự nhận** trong vài giây, bot nhắn «Đã nối Telegram» là được.")
        t.link_button("Hoặc mở Telegram trên máy tính này", url)
        t.caption("Không quét được thì gõ đường link này vào trình duyệt điện thoại:")
        t.code(url, language=None)

        @st.fragment(run_every=3)
        def _wait_start():  # tự kiểm tra 3 giây/lần, không cần bấm nút
            try:
                found = tg.find_chat(S, code)
            except Exception as e:
                st.caption(f"Đang chờ... ({tg._safe(e)[:120]})")
                return
            if not found:
                st.info("Đang chờ bác bấm Start trong Telegram...")
                return
            if not any(str(x["chat_id"]) == found["chat_id"] for x in rs):
                rs.append({**found, "kinds": list(KIND_LABEL), "apps": list(APP_LABEL), "on": True})
            if not S.get("tg_admin_chat"):  # người nhận đầu tiên = Admin (nhận Báo lỗi), đổi được ở dưới
                S["tg_admin_chat"] = found["chat_id"]
            save_settings(S)
            st.session_state.pop("tg_link_code", None)
            try:
                tg.send_to(S["tg_bot"], found["chat_id"], "up", "xong", "Đã nối Telegram với Sonix Auto",
                           "Từ giờ bác nhận thông báo ở đây.")
            except Exception:
                pass
            st.rerun(scope="app")
        _wait_start()

def _admin_box(S):
    rs = S.get("tg_nguoi_nhan") or []
    with st.expander("Admin: nơi nhận Báo lỗi + mã nhận thông báo cho người dùng"):
        b = tg._builtin()
        if b and str(b[1]) == str(S.get("tg_admin_chat")):
            st.success("Báo lỗi của mọi máy (không cần Telegram) đang gửi về Telegram Admin này.")
        elif b:
            st.warning("Bot báo lỗi gắn trong app đang gửi về 1 Telegram khác với Admin chọn dưới đây.")
        else:
            st.info("App chưa gắn sẵn bot báo lỗi: máy người dùng chưa dán mã thì Báo lỗi chỉ tạo gói .zip để "
                    "gửi Zalo cho Admin.")
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
            _report_bot_box(S)
            st.markdown("**Mã nhận thông báo** · gửi RIÊNG cho người dùng muốn nhận tin qua Telegram (Zalo). Họ dán vào "
                        "Cài đặt → Nhận thông báo về Telegram → Cách 1, rồi quét QR. **Đừng đăng mã này công khai.**")
            if st.toggle("Hiện mã", key="tg_show_share"):
                st.code(tg.make_share_code(S), language=None)
        else:
            st.caption("Chọn Telegram Admin ở trên trước (thêm người nhận rồi chọn).")


def _report_bot_box(S):
    """Admin tạo bot thứ 2 chỉ để nhận Báo lỗi; app lưu mã đã mã hoá để gắn vào bản phát hành."""
    st.markdown("**Bot báo lỗi** (bot thứ 2, chỉ gửi Báo lỗi về Admin, gắn sẵn vào app để máy người dùng "
                "không cần Telegram)")
    st.caption("1. Tạo thêm 1 bot với BotFather (vd tên `Sonix Bao Loi`, tên đăng nhập `sonix_baoloi_son_bot`).  \n"
               "2. Mở bot mới đó trên Telegram điện thoại, bấm **BẮT ĐẦU / START** (bot chỉ nhắn được cho người đã Start).  \n"
               "3. Dán mã bot mới vào ô dưới, bấm Kiểm tra. Tool gửi thử 1 tin về Telegram Admin.")
    tok = st.text_input("Mã bot báo lỗi", key="tg_rb_in", type="password")
    if st.button("Kiểm tra bot báo lỗi", key="tg_rb_ok", disabled=not tok):
        try:
            me = tg.bot_info(tok.strip())
            tg.send_to(tok.strip(), S["tg_admin_chat"], "up", "bao_loi", "", raw_caption=(
                f"Bot báo lỗi @{me.get('username')} đã sẵn sàng. Báo lỗi của người dùng sẽ về đây."))
            (DATA_DIR / "lien_ket_admin.txt").write_text(tg.encode_builtin(tok.strip(), S["tg_admin_chat"]),
                                                         encoding="utf-8")
            st.success(f"Đã gửi thử từ @{me.get('username')}. Bác xem Telegram, rồi báo Claude «đã tạo bot báo lỗi» "
                       "để gắn vào bản cập nhật cho mọi máy.")
        except Exception as e:
            st.error(tg._safe(e) + " · Bác đã bấm Start ở bot báo lỗi mới chưa?")


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


def _log_lines(app, n=40) -> list:
    """Các dòng nhật ký gần nhất trên app (Up: bộ đăng + phân tích; Edit: việc edit mới nhất)."""
    if app == "edit":
        d = DATA_DIR / "edit" / "viec"
        logs = sorted(d.glob("*.log"), key=lambda p: p.stat().st_mtime)[-2:] if d.is_dir() else []
        out = []
        for f in logs:
            out += [f"[{f.stem}] {x}" for x in _tail(f, n).splitlines()]
        return out[-n:]
    return (_tail(RUNNER_LOG, n).splitlines() + ["--- phân tích ---"] + _tail(LOG_DIR / "phan_tich.log", 8).splitlines())


def _log_image(lines, title) -> str:
    """Vẽ đoạn nhật ký thành ảnh để Admin đọc ngay trên điện thoại."""
    from PIL import Image, ImageDraw, ImageFont
    font = None
    for f in ("C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"):
        try:
            font = ImageFont.truetype(f, 17)
            break
        except Exception:
            pass
    font = font or ImageFont.load_default()
    wrapped = []
    for ln in [title, ""] + list(lines):
        ln = ln.replace("\t", "  ")
        while len(ln) > 110:
            wrapped.append(ln[:110])
            ln = "    " + ln[110:]
        wrapped.append(ln)
    wrapped = wrapped[-70:]
    img = Image.new("RGB", (1180, 30 + 22 * len(wrapped)), (24, 26, 32))
    d = ImageDraw.Draw(img)
    for i, ln in enumerate(wrapped):
        col = (255, 120, 120) if re.search(r"✖|⛔|Lỗi|LỖI|lỗi|Error|Traceback", ln) else \
              (140, 220, 140) if ln.lstrip().startswith("✔") else (225, 225, 225)
        d.text((14, 14 + 22 * i), ln, fill=col if i else (255, 210, 90), font=font)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"nhat_ky_{datetime.now():%H%M%S}.png"
    img.save(out)
    return str(out)


def render_bao_loi(S, app="up"):
    st.subheader("Báo lỗi với Admin")
    st.caption("Gặp lỗi khi dùng app? Ghi rõ tình trạng, chụp màn hình lỗi, bấm Gửi. **Không cần Telegram**: app tự gửi "
               "mô tả + ảnh + nhật ký sử dụng về cho Admin. Gói nhật ký **không** có mật khẩu, token, khoá AI.")
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
    lines = _log_lines(app)
    with st.expander("Nhật ký trên app sẽ gửi kèm (đoạn gần nhất)"):
        st.code("\n".join(lines[-40:]) or "(trống)", language=None)
    target = tg.admin_target(S)
    ok_tg = bool(target)
    b = st.columns([1, 1, 2])
    send = b[0].button("Gửi báo lỗi cho Admin", key=f"{k}_send", type="primary", disabled=not desc.strip())
    ai = b[1].button("Nhờ AI xem nhanh", key=f"{k}_ai", disabled=not desc.strip(),
                     help="AI (Mức AI mặc định ở Cài đặt) đọc mô tả + nhật ký và gợi ý cách tự xử lý. Chỉ gửi chữ, rất rẻ.")
    if not ok_tg:
        b[2].caption("App chưa có đường gửi về Admin. Vẫn bấm Gửi được: tool tạo gói báo lỗi (.zip) để bác tải về "
                     "gửi Zalo cho Admin.")
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
        try:
            imgs = imgs[:4] + [_log_image(lines, f"Nhật ký app · Sự cố người dùng #{rid} · {APP_LABEL.get(app)}")]
        except Exception:
            pass
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
                    tg.send_to(target[0], target[1], app, "bao_loi", "", photos=imgs, raw_caption=cap[:1020])
                    tg.send_to(target[0], target[1], app, "bao_loi", "", document=str(bundle),
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
