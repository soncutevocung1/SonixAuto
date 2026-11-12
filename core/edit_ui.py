"""Tab Edit video: kịch bản (AI học kênh tham khảo) -> giọng (Vbee / miễn phí) -> chọn cảnh -> dự án CapCut."""
import json
import time
from pathlib import Path

import streamlit as st

from . import capcut_draft, desktop, edit_job, edit_video, giong, kich_ban, vbee
from .config import MODELS, NO_AI, save_settings

KB_DIR = edit_video.EDIT_DIR / "kich_ban"
GIONG_DIR = edit_video.EDIT_DIR / "giong"


def _flags():
    try:
        return desktop.no_window_flags()
    except Exception:
        return 0


def _env():
    try:
        return desktop.env()
    except Exception:
        return None


def _set(S, key, wkey):
    S[key] = st.session_state[wkey]
    save_settings(S)


def _kb_path(sp):
    return KB_DIR / f"{sp}.json"


def _load_kb(sp):
    p = _kb_path(sp)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"tieu_de": "", "loi": "", "giong": ""}


def _save_kb(sp, kb):
    KB_DIR.mkdir(parents=True, exist_ok=True)
    _kb_path(sp).write_text(json.dumps(kb, ensure_ascii=False, indent=1), encoding="utf-8")


# ------------------------------- việc chạy ngầm -------------------------------
def _job_box(name, title):
    """Đang chạy thì tự làm mới mỗi 4 giây; xong rồi thì chỉ hiện nhật ký (không làm mới liên tục)."""
    if edit_job.dang_chay(name):
        _job_live(name, title)
    else:
        _job_show(name, title, False)


@st.fragment(run_every=4)
def _job_live(name, title):
    chay = edit_job.dang_chay(name)
    _job_show(name, title, chay)
    if not chay:
        st.rerun()  # xong -> làm mới cả trang (cập nhật số đoạn đã quét), hết tự làm mới


def _job_show(name, title, chay):
    lines = edit_job.doc_log(name)
    if not lines and not chay:
        return
    with st.container(border=True):
        st.caption(f"{title}: {'đang chạy...' if chay else 'đã dừng'}")
        st.code("\n".join(lines) or "...", language=None)


# ------------------------------- các phần -------------------------------
def _vbee_setup(S):
    app_id, token = vbee.keys(S)
    with st.expander("Kết nối Vbee" + (" (đã có mã)" if app_id and token else " (chưa có mã)"),
                     expanded=not (app_id and token)):
        st.markdown("Vào **studio.vbee.vn → Tích hợp API → Tạo ứng dụng**, chép **App ID** và **Token** dán vào đây. "
                    "Mã chỉ lưu trên máy này, không gửi cho ai.")
        c = st.columns(2)
        a = c[0].text_input("App ID", value=S.get("vbee_app_id", ""), type="password", key="ev_appid")
        t = c[1].text_input("Token", value=S.get("vbee_token", ""), type="password", key="ev_token")
        if st.button("Lưu mã Vbee"):
            S["vbee_app_id"], S["vbee_token"] = a.strip(), t.strip()
            save_settings(S)
            st.success("Đã lưu")
            st.rerun()


def _voice_settings(S):
    eng = st.radio("Giọng đọc", ["vbee", "mien_phi"], horizontal=True, key="ev_engine",
                   index=0 if S.get("edit_voice_engine", "vbee") == "vbee" else 1,
                   format_func=lambda x: {"vbee": "Vbee (trả phí)", "mien_phi": "Miễn phí (Microsoft)"}[x],
                   on_change=_set, args=(S, "edit_voice_engine", "ev_engine"))
    c = st.columns(2)
    if eng == "vbee":
        voices = dict(vbee.VOICES)
        for code, name in (S.get("vbee_voices_extra") or {}).items():
            voices.setdefault(code, name)
        if st.session_state.get("ev_all_voices"):
            for code, name in vbee.danh_sach_giong().items():
                voices.setdefault(code, name)
        cur = S.get("vbee_voice") or vbee.DEFAULT_VOICE
        voices.setdefault(cur, cur)
        keys = list(voices)
        c[0].selectbox("Giọng Vbee", keys, index=keys.index(cur), format_func=lambda k: voices[k],
                       key="ev_voice", on_change=_set, args=(S, "vbee_voice", "ev_voice"))
        c[0].checkbox("Hiện tất cả giọng tiếng Việt của Vbee", key="ev_all_voices")
        c[1].number_input("Tốc độ", 0.5, 2.0, float(S.get("vbee_speed") or vbee.DEFAULT_SPEED), 0.05,
                          key="ev_speed", on_change=_set, args=(S, "vbee_speed", "ev_speed"))
        with c[1].popover("Thêm giọng theo mã"):
            st.caption("Giọng không có trong danh sách (vd Tuấn Anh quảng cáo): dán mã giọng lấy trên studio Vbee.")
            code = st.text_input("Mã giọng", key="ev_new_code")
            nm = st.text_input("Tên hiển thị", key="ev_new_name")
            if st.button("Thêm", disabled=not code.strip()):
                ex = S.get("vbee_voices_extra") or {}
                ex[code.strip()] = nm.strip() or code.strip()
                S["vbee_voices_extra"] = ex
                save_settings(S)
                st.rerun()
        _vbee_setup(S)
    else:
        keys = list(giong.FREE_VOICES)
        cur = S.get("free_voice") or keys[0]
        c[0].selectbox("Giọng miễn phí", keys, index=keys.index(cur) if cur in keys else 0,
                       format_func=lambda k: giong.FREE_VOICES[k], key="ev_free",
                       on_change=_set, args=(S, "free_voice", "ev_free"))
        c[1].number_input("Tốc độ", 0.8, 1.6, float(S.get("free_speed") or 1.2), 0.05,
                          key="ev_fspeed", on_change=_set, args=(S, "free_speed", "ev_fspeed"))
        st.caption("Giọng miễn phí cần mạng, đôi khi máy chủ Microsoft chậm: tool tự thử lại từng câu.")


def _script(S, sp):
    kb = _load_kb(sp)
    ref = edit_video.kich_ban_tham_khao()
    model = S.get("ai_model") or NO_AI
    co_ai = model != NO_AI and model in MODELS

    with st.expander(f"Kênh tham khảo ({sum(len(v) for v in ref.values())} kịch bản đã quét)"):
        st.markdown("AI học **cách giật tít, nhịp câu, cách dẫn** từ kênh TikTok cùng kiểu (khác sản phẩm cũng được), "
                    "rồi viết lại cho sản phẩm của mình. Mở kênh trên trình duyệt, chép **link từng video** "
                    "(nên lấy các video nhiều lượt xem) dán vào ô dưới, mỗi dòng 1 link.")
        for k, v in ref.items():
            st.caption(f"- {k}: {len(v)} kịch bản")
        ten = st.text_input("Tên kênh (đặt tuỳ ý)", key="ev_ref_name")
        links = st.text_area("Link video", key="ev_ref_links", height=120)
        chay = edit_job.dang_chay("quet_kenh_" + (ten.strip() or "kenh"))
        if st.button("Quét lời (tải tiếng + chép lời trên máy)", disabled=chay or not links.strip()):
            tn = ten.strip() or "kenh"
            f = edit_job.JOB_DIR / f"links_{tn}.txt"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(links, encoding="utf-8")
            edit_job.chay_ngam("quet_kenh_" + tn, "quet_kenh", tn, str(f), env=_env(), flags=_flags())
            st.rerun()
        for k in list(ref) + [ten.strip() or "kenh"]:
            _job_box("quet_kenh_" + k, f"Quét kênh {k}")

    y = st.text_input("Ý tưởng / ưu đãi đợt này (không bắt buộc)", key=f"ev_idea_{sp}",
                      placeholder="vd: mua 2 tặng 1, chỉ hôm nay")
    c = st.columns([1, 1, 2])
    if c[0].button("AI viết kịch bản", type="primary", disabled=not co_ai,
                   help=None if co_ai else "Chưa chọn AI trong Cài đặt"):
        with st.spinner("AI đang viết..."):
            try:
                mau = [x for v in ref.values() for x in v]
                r = kich_ban.viet(sp, mau, S, y_tuong=y)
                kb.update(r, giong="")
                _save_kb(sp, kb)
                for k_ in (f"ev_title_{sp}", f"ev_loi_{sp}"):
                    st.session_state.pop(k_, None)
                st.rerun()
            except Exception as e:
                st.error(f"AI lỗi: {e}")
    if c[1].button("Viết theo công thức (không AI)"):
        kb.update(kich_ban.mau_khong_ai(sp), giong="")
        _save_kb(sp, kb)
        for k_ in (f"ev_title_{sp}", f"ev_loi_{sp}"):
            st.session_state.pop(k_, None)
        st.rerun()

    title = st.text_area("Tiêu đề (3 dòng, dòng 1 tô vàng)", value=kb.get("tieu_de", ""), height=90,
                         key=f"ev_title_{sp}")
    loi = st.text_area("Lời đọc (sửa thoải mái trước khi lồng tiếng)", value=kb.get("loi", ""), height=200,
                       key=f"ev_loi_{sp}")
    st.caption(f"{len(loi.split())} chữ, đọc khoảng {len(loi.split()) / 4.6:.0f} giây")
    if title != kb.get("tieu_de") or loi != kb.get("loi"):
        if loi != kb.get("loi"):
            kb["giong"] = ""  # lời đổi thì phải lồng tiếng lại
        kb.update(tieu_de=title, loi=loi)
        _save_kb(sp, kb)
    return kb


def _voice(S, sp, kb):
    _voice_settings(S)
    g = kb.get("giong")
    if st.button("Lồng tiếng", type="primary", disabled=not kb.get("loi", "").strip()):
        out = GIONG_DIR / f"{sp}_{time.strftime('%Y%m%d_%H%M%S')}.mp3"
        with st.spinner("Đang lồng tiếng..."):
            try:
                r = edit_video.tao_giong(kb["loi"], out, S, log=lambda m: None)
                kb["giong"] = r["path"]
                _save_kb(sp, kb)
                st.rerun()
            except Exception as e:
                st.error(f"Lồng tiếng lỗi: {e}")
    if g and Path(g).exists():
        st.audio(g)
        st.caption(Path(g).name)


def _scenes(S, sp):
    from . import canh
    idx = canh.doc_index(sp)
    files = edit_video.thu_muc_clip(sp, edit_video.input_root(S))
    doan = [d for v in idx.values() for d in v["doan"]]
    ok = [d for d in doan if canh.dung_duoc(d)]
    by = {l: sum(1 for d in ok if (d.get("loai") or "") == l) for l in ("san_pham", "su_dung", "ket_qua")}
    nguoi = sum(1 for d in doan if canh.co_nguoi(d))
    da = sum(1 for f in files if str(f) in idx)
    st.markdown(f"Thư mục: `{edit_video.input_root(S) / kich_ban.SAN_PHAM[sp]['thu_muc']}`  \n"
                f"Đã quét **{da}/{len(files)}** video · dùng được **{len(ok)}** đoạn "
                f"(sản phẩm {by['san_pham']}, cách dùng {by['su_dung']}, kết quả {by['ket_qua']}) · "
                f"{nguoi} đoạn có người cho khung 4 ô")
    st.caption("Tool tự bỏ: cảnh có người, chữ/sticker chèn, outro cuối video, ảnh tĩnh / ghép ảnh giật, sản phẩm khác hãng. "
               "Video mới thêm vào thư mục: bấm quét lại, video đã quét sẽ bỏ qua.")
    name = "quet_canh_" + sp
    chay = edit_job.dang_chay(name)
    if st.button("Quét cảnh" if da < len(files) else "Quét lại video mới", disabled=chay):
        edit_job.chay_ngam(name, "quet_canh", sp, env=_env(), flags=_flags())
        st.rerun()
    _job_box(name, "Quét cảnh")
    return len(ok)


def _project(S, sp, kb, n_ok):
    musics = edit_video.nhac_nen(edit_video.input_root(S))
    opts = [""] + [str(m) for m in musics] + ["none"]
    c = st.columns([2, 2, 1])
    ten = c[0].text_input("Tên dự án CapCut", value=f"SONIX {kich_ban.SAN_PHAM[sp]['ten'].upper()} "
                          f"{time.strftime('%d-%m %H%M')}", key=f"ev_name_{sp}")
    nhac = c[1].selectbox("Nhạc nền", opts, key="ev_music",
                          format_func=lambda x: {"": "Ngẫu nhiên", "none": "Không nhạc"}.get(x, Path(x).stem))
    luoi = c[2].checkbox("Khung 4 ô người dùng", value=True, key="ev_grid")
    mo = capcut_draft.capcut_dang_mo()
    if mo:
        st.warning("CapCut đang mở: tắt CapCut rồi mới tạo dự án (tránh CapCut ghi đè danh sách dự án).")
    g = kb.get("giong")
    thieu = [m for m, ok in [("lời", kb.get("loi")), ("giọng (bấm Lồng tiếng)", g and Path(g).exists()),
                             ("cảnh (bấm Quét cảnh)", n_ok)] if not ok]
    if thieu:
        st.caption("Còn thiếu: " + ", ".join(thieu))
    if st.button("Tạo dự án CapCut", type="primary", disabled=bool(mo or thieu)):
        with st.spinner("Đang chọn cảnh và dựng dự án..."):
            try:
                r = edit_video.tao_du_an(sp, kb, g, S, ten=ten, nhac=nhac, luoi=luoi)
                st.success(f"Đã tạo **{r['name']}** ({r['duration']:.1f} giây). Mở CapCut, dự án nằm đầu danh sách.")
            except Exception as e:
                st.error(f"Lỗi: {e}")
    with st.expander("Dự án mẫu & thư mục nguồn"):
        st.markdown(f"Tool chép dự án mẫu **{S.get('edit_template') or edit_video.TEMPLATE}** trong CapCut "
                    "(khung, chữ, người dẫn, màu, mũi tên) rồi thay video, giọng, nhạc, tiêu đề. "
                    "Muốn đổi khung cho mọi video: sửa trong dự án mẫu.")
        S_t = st.text_input("Tên dự án mẫu", value=S.get("edit_template") or edit_video.TEMPLATE, key="ev_tpl")
        S_r = st.text_input("Thư mục nguồn (chứa ĐẠM CÁ, KÍCH RỄ, TÀI NGUYÊN)", value=str(edit_video.input_root(S)),
                            key="ev_root")
        if st.button("Lưu", key="ev_save_paths"):
            S["edit_template"], S["edit_input_root"] = S_t.strip(), S_r.strip()
            save_settings(S)
            st.rerun()


def render(S):
    st.subheader("Sonix Edit Video: kịch bản → lồng tiếng → dựng sẵn dự án CapCut")
    sps = list(kich_ban.SAN_PHAM)
    sp = st.radio("Sản phẩm", sps, horizontal=True, key="ev_sp",
                  format_func=lambda k: kich_ban.SAN_PHAM[k]["ten"])
    with st.container(border=True):
        st.markdown("**1. Kịch bản**")
        kb = _script(S, sp)
    with st.container(border=True):
        st.markdown("**2. Lồng tiếng**")
        _voice(S, sp, kb)
    with st.container(border=True):
        st.markdown("**3. Cảnh quay**")
        n_ok = _scenes(S, sp)
    with st.container(border=True):
        st.markdown("**4. Tạo dự án CapCut**")
        _project(S, sp, kb, n_ok)
