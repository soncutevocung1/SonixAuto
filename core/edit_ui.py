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


@st.cache_data(ttl=600, show_spinner=False)
def _eleven_voices(k):
    from . import elevenlabs
    return elevenlabs.danh_sach_giong(k)


def _eleven(S):
    from . import elevenlabs
    k = elevenlabs.key(S)
    c = st.columns(2)
    if k:
        try:
            voices = _eleven_voices(k)
        except Exception as e:
            voices = {}
            st.error(str(e))
        cur = S.get("eleven_voice") or (next(iter(voices)) if voices else "")
        if voices:
            keys = list(voices)
            c[0].selectbox("Giọng ElevenLabs (giọng trong tài khoản của bác)", keys,
                           index=keys.index(cur) if cur in keys else 0, format_func=lambda x: voices[x],
                           key="ev_el_voice", on_change=_set, args=(S, "eleven_voice", "ev_el_voice"))
            if cur not in keys:
                S["eleven_voice"] = keys[0]
                save_settings(S)
        ms = list(elevenlabs.MODELS)
        c[1].selectbox("Mẫu giọng", ms, index=ms.index(S.get("eleven_model") or elevenlabs.DEFAULT_MODEL),
                       format_func=elevenlabs.MODELS.get, key="ev_el_model",
                       on_change=_set, args=(S, "eleven_model", "ev_el_model"))
        c[1].number_input("Tốc độ (0.7 - 1.2)", 0.7, 1.2, float(S.get("eleven_speed") or 1.0), 0.05,
                          key="ev_el_speed", on_change=_set, args=(S, "eleven_speed", "ev_el_speed"))
        st.caption("Muốn thêm giọng: vào elevenlabs.io → Voices → Voice Library, bấm Add to my voices "
                   "(nên chọn giọng tiếng Việt), rồi tải lại trang này.")
    with st.expander("Kết nối ElevenLabs" + (" (đã có mã)" if k else " (chưa có mã)"), expanded=not k):
        st.markdown("Vào **elevenlabs.io → Developers → API Keys → Create API Key** (bật quyền **Text to Speech** và "
                    "**Voices: Read**), chép mã dán vào đây. Mã chỉ lưu trên máy này.")
        v = st.text_input("API Key", value=S.get("eleven_key", ""), type="password", key="ev_el_key")
        if st.button("Lưu mã ElevenLabs"):
            S["eleven_key"] = v.strip()
            save_settings(S)
            st.cache_data.clear()
            st.rerun()


def _voice_settings(S):
    ten = {"vbee": "Vbee (trả phí)", "eleven": "ElevenLabs (trả phí)", "mien_phi": "Miễn phí (Microsoft)"}
    cur_eng = S.get("edit_voice_engine", "vbee")
    eng = st.radio("Giọng đọc", list(ten), horizontal=True, key="ev_engine",
                   index=list(ten).index(cur_eng) if cur_eng in ten else 0, format_func=ten.get,
                   on_change=_set, args=(S, "edit_voice_engine", "ev_engine"))
    if eng == "eleven":
        _eleven(S)
        return
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


def _phong_cach(S) -> dict:
    """Chọn phong cách mẫu (thư mục con trong MẪU). Trả về phong cách đã học hoặc {} (dùng công thức mặc định)."""
    from . import mau
    ds = mau.danh_sach(S)
    goc = mau.thu_muc(S)
    opts = [""] + list(ds)
    cur = S.get("edit_phong_cach", "")
    c = st.columns([2, 1])
    ten = c[0].selectbox("Làm theo phong cách mẫu", opts, index=opts.index(cur) if cur in opts else 0,
                         format_func=lambda x: x or "Mặc định (công thức giảm giá kịch tính + kênh tham khảo)",
                         key="ev_pc", on_change=_set, args=(S, "edit_phong_cach", "ev_pc"),
                         help=f"Mỗi thư mục con trong {goc} là 1 phong cách. Bỏ vài video mẫu vào, đặt tên thư mục "
                              "theo phong cách (vd 'Reup Aff', 'Review nhẹ nhàng'), rồi bấm Học phong cách.")
    if c[1].button("Mở thư mục MẪU"):
        goc.mkdir(parents=True, exist_ok=True)
        import os
        os.startfile(str(goc))  # noqa
    if not ds:
        st.caption(f"Chưa có phong cách nào: tạo thư mục con trong `{goc}` rồi bỏ video mẫu vào.")
    if not ten:
        return {}
    pc = mau.doc(ten)
    vids = ds.get(ten, [])
    da = len([v for v in vids if v.name in pc.get("videos", {})])
    name = "hoc_mau_" + "".join(ch for ch in ten if ch.isalnum())[:30]
    chay = edit_job.dang_chay(name)
    with st.container(border=True):
        if pc.get("nhip"):
            st.markdown(f"**{ten}** · đã học {da}/{len(vids)} video ({pc.get('luc', '')}) · mỗi cảnh ~**{pc['nhip']:.1f} giây** "
                        f"· video ~{pc.get('giay_tb', 0):.0f} giây, ~{pc.get('chu_tb', 0)} chữ")
            if pc.get("mo_ta"):
                with st.expander("Phong cách AI rút ra"):
                    st.markdown(pc["mo_ta"])
                    st.markdown("**Cách viết lời:**\n\n" + pc.get("cach_viet", ""))
        else:
            st.caption(f"**{ten}**: {len(vids)} video, chưa học.")
        if st.button("Học phong cách này" if not pc.get("nhip") else "Học lại (có video mới)", disabled=chay or not vids,
                     key="ev_hoc"):
            f = edit_job.JOB_DIR / f"{name}.txt"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(ten, encoding="utf-8")
            edit_job.chay_ngam(name, "hoc_mau", name[8:], str(f), env=_env(), flags=_flags())
            st.rerun()
        _job_box(name, "Học phong cách")
    return pc if pc.get("nhip") or pc.get("cach_viet") else {}


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

    pc = _phong_cach(S)
    y = st.text_input("Ý tưởng / ưu đãi đợt này (không bắt buộc)", key=f"ev_idea_{sp}",
                      placeholder="vd: mua 2 tặng 1, chỉ hôm nay")
    c = st.columns([1, 1, 2])
    if c[0].button("AI viết kịch bản", type="primary", disabled=not co_ai,
                   help=None if co_ai else "Chưa chọn AI trong Cài đặt"):
        with st.spinner("AI đang viết..."):
            try:
                from . import mau as mau_mod
                if pc:
                    mau = mau_mod.loi_mau(pc["ten"])
                else:
                    mau = [x for v in ref.values() for x in v]
                r = kich_ban.viet(sp, mau, S, y_tuong=y, phong_cach=pc or None)
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
    tm = edit_video.thu_muc_sp(sp, edit_video.input_root(S))
    st.markdown(f"Thư mục: {', '.join(f'`{d.name}`' for d in tm) or 'chưa có (dùng mục Tự lọc ở trên)'}  \n"
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


XEM_DIR = edit_video.EDIT_DIR / "xem"
TEN_LOAI = {"san_pham": "Sản phẩm", "su_dung": "Cách dùng", "ket_qua": "Kết quả", "khac": "Khác"}


def _anh(path, t):
    """Ảnh nhỏ 1 khung (lưu tạm để không cắt lại)."""
    import hashlib
    from . import canh
    XEM_DIR.mkdir(parents=True, exist_ok=True)
    f = XEM_DIR / (hashlib.md5(f"{path}|{t:.2f}".encode("utf-8")).hexdigest() + ".jpg")
    if not f.exists():
        im = canh.khung(path, t, 200)
        if im is None:
            return None
        import cv2
        cv2.imwrite(str(f), im, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return str(f)


def _preview(S, sp, kb, luoi):
    """Xem trước cảnh theo từng câu, đổi cảnh không ưng."""
    from . import canh
    g = kb.get("giong")
    if not (g and Path(g).exists()):
        st.caption("Lồng tiếng xong mới chọn cảnh được (hoặc bấm nút làm 1 lần ở dưới).")
        return
    clips = kb.get("canh") if kb.get("canh_giong") == g else None
    c = st.columns([1, 1, 3])
    if c[0].button("Chọn cảnh" if not clips else "Chọn lại tất cả", key="ev_chon"):
        with st.spinner("Đang chọn cảnh theo từng câu..."):
            kb["canh"] = edit_video.chon_canh(sp, kb, g, S, luoi=luoi, seed=int(time.time()) % 1000)
            kb["canh_giong"] = g
            _save_kb(sp, kb)
            st.rerun()
    if not clips:
        return
    if c[1].button("Bỏ cảnh đã chọn", key="ev_bo_chon", help="Để tool tự chọn lúc tạo dự án"):
        kb["canh"] = None
        _save_kb(sp, kb)
        st.rerun()
    cau = canh.chia_cau(kb["loi"], 1)
    c[2].caption(f"{len(clips)} cảnh · bấm **Đổi** dưới cảnh không ưng (đổi sang cảnh khác cùng loại).")
    N = 6
    for r0 in range(0, len(clips), N):
        cols = st.columns(N)
        for j, cl in enumerate(clips[r0:r0 + N]):
            i = r0 + j
            with cols[j]:
                if isinstance(cl, dict):
                    sub = st.columns(2)
                    for q, (p, s, ln) in enumerate(cl["luoi"]):
                        a = _anh(p, s + ln / 2)
                        if a:
                            sub[q % 2].image(a, width="stretch")
                    st.caption("Khung 4 ô")
                    if st.button("Đổi 4 người", key=f"ev_doi_{i}"):
                        kb["canh"] = canh.doi_luoi(sp, clips, i, seed=time.time())
                        _save_kb(sp, kb)
                        st.rerun()
                    continue
                p, s, ln = cl[0], cl[1], cl[2]
                a = _anh(p, s + ln / 2)
                if a:
                    st.image(a, width="stretch")
                loai = cl[4] if len(cl) > 4 else ""
                ci = cl[5] if len(cl) > 5 else None
                st.caption(f"{i + 1}. {TEN_LOAI.get(loai, loai)}" + (f" · câu {ci + 1}" if ci is not None else ""),
                           help=(cau[ci][0] if ci is not None and ci < len(cau) else None))
                if st.button("Đổi", key=f"ev_doi_{i}"):
                    kb["canh"] = canh.doi_canh(sp, clips, i, seed=time.time())
                    _save_kb(sp, kb)
                    st.rerun()


def _khuon(S):
    """Khuôn CapCut + tài nguyên: máy thiếu thì tải từ GitHub về cài."""
    from . import khuon
    tn = edit_video.input_root(S) / edit_video.TAI_NGUYEN
    tpl = S.get("edit_template") or edit_video.TEMPLATE
    co = (capcut_draft.CAPCUT_DRAFTS / tpl / "draft_content.json").exists()
    nhac = edit_video.nhac_nen(edit_video.input_root(S))
    if co and nhac:
        return True
    with st.container(border=True):
        st.warning(("Máy này chưa có dự án mẫu **'" + tpl + "'** trong CapCut. " if not co else "") +
                   ("Thư mục TÀI NGUYÊN chưa có nhạc nền. " if not nhac else "") +
                   "Bấm nút dưới để tải khuôn Reup Aff (khung, người dẫn, nhạc, khoảng 210 MB) từ GitHub và cài tự động.")
        name = "cai_khuon"
        chay = edit_job.dang_chay(name)
        mo = capcut_draft.capcut_dang_mo()
        if mo:
            st.caption("Tắt CapCut trước khi cài.")
        if st.button("Tải và cài khuôn Reup Aff", type="primary", disabled=chay or mo):
            edit_job.chay_ngam(name, "cai_khuon", "x", env=_env(), flags=_flags())
            st.rerun()
        _job_box(name, "Cài khuôn")
    return co


def _project(S, sp, kb, n_ok):
    co_khuon = _khuon(S)
    musics = edit_video.nhac_nen(edit_video.input_root(S))
    opts = [""] + [str(m) for m in musics] + ["none"]
    c = st.columns([2, 2, 1])
    ten = c[0].text_input("Tên dự án CapCut", value=f"SONIX {kich_ban.SAN_PHAM[sp]['ten'].upper()} "
                          f"{time.strftime('%d-%m %H%M')}", key=f"ev_name_{sp}")
    nhac = c[1].selectbox("Nhạc nền", opts, key="ev_music",
                          format_func=lambda x: {"": "Ngẫu nhiên", "none": "Không nhạc"}.get(x, Path(x).stem))
    luoi = c[2].checkbox("Khung 4 ô người dùng", value=True, key="ev_grid")
    with st.expander("Xem trước cảnh theo từng câu (đổi cảnh không ưng)", expanded=bool(kb.get("canh"))):
        _preview(S, sp, kb, luoi)
    mo = capcut_draft.capcut_dang_mo()
    if mo:
        st.info("CapCut đang mở: bấm nút vẫn được, tool sẽ chờ bác tắt CapCut rồi mới ghi dự án.")
    thieu = [m for m, ok in [("lời", kb.get("loi")), ("cảnh (bấm Quét cảnh)", n_ok), ("khuôn CapCut", co_khuon)]
             if not ok]
    if thieu:
        st.caption("Còn thiếu: " + ", ".join(thieu))
    name = "lam_video_" + sp
    chay = edit_job.dang_chay(name)
    g = kb.get("giong")
    nhan = "Tạo dự án CapCut" if g and Path(g).exists() else "Lồng tiếng + chọn cảnh + tạo dự án"
    if st.button(nhan, type="primary", disabled=bool(thieu) or chay,
                 help="Chạy nền: lồng tiếng (nếu chưa có), chọn cảnh (hoặc dùng cảnh đã duyệt), tạo dự án CapCut"):
        cfg = edit_job.JOB_DIR / f"{name}.json"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text(json.dumps({"sp": sp, "kb": str(_kb_path(sp)), "ten": ten, "nhac": nhac, "luoi": luoi},
                                  ensure_ascii=False), encoding="utf-8")
        edit_job.chay_ngam(name, "lam_video", sp, str(cfg), env=_env(), flags=_flags())
        st.rerun()
    _job_box(name, "Làm video")

    with st.expander("Làm hàng loạt (nhiều video, mỗi video lời khác nhau)"):
        st.caption("AI tự viết lời mới cho từng video (theo phong cách đang chọn, không trùng câu mở), lồng tiếng, chọn "
                   "cảnh, tạo dự án CapCut. Không duyệt lời từng bản: xem lại trong CapCut trước khi xuất.")
        h = st.columns([1, 3])
        n = h[0].number_input("Số video", 1, 10, 3, key="ev_hl_n")
        y = h[1].text_input("Ưu đãi / ý tưởng chung (không bắt buộc)", key="ev_hl_y")
        name2 = "hang_loat_" + sp
        chay2 = edit_job.dang_chay(name2)
        model = S.get("ai_model") or NO_AI
        if st.button(f"Làm {int(n)} video", disabled=chay2 or bool(thieu) or model == NO_AI or model not in MODELS):
            cfg = edit_job.JOB_DIR / f"{name2}.json"
            cfg.parent.mkdir(parents=True, exist_ok=True)
            cfg.write_text(json.dumps({"sp": sp, "n": int(n), "y_tuong": y, "nhac": nhac, "luoi": luoi},
                                      ensure_ascii=False), encoding="utf-8")
            edit_job.chay_ngam(name2, "hang_loat", sp, str(cfg), env=_env(), flags=_flags())
            st.rerun()
        _job_box(name2, "Làm hàng loạt")

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


def _loc(S):
    """Tự lọc video lẫn lộn thành thư mục theo sản phẩm (mỗi đợt thư mục mới)."""
    from . import loc_sp
    root = edit_video.input_root(S)
    with st.expander("Tự lọc video theo sản phẩm (đưa video mới vào)"):
        st.markdown("Chọn thư mục chứa video **lẫn lộn** (đặt tên file có tên sản phẩm thì nhận nhanh và chắc hơn). "
                    "Tool nhận ra sản phẩm theo **tên file → chữ trên nhãn → AI xem hình**, rồi đưa mỗi sản phẩm vào "
                    f"1 thư mục **mới** trong `{root}`, tên kèm tên đợt (vd `KÍCH RỄ 13-11-2026`). Thư mục có sẵn giữ "
                    "nguyên. Không nhận ra hoặc nhiều sản phẩm → thư mục `CẦN XEM`. Edit Video tự dùng cả thư mục cũ và mới.")
        c = st.columns([3, 2, 1])
        nguon = c[0].text_input("Thư mục video cần lọc", value=str(root / "CHƯA LỌC") if (root / "CHƯA LỌC").exists()
                                else "", key="ev_loc_src", placeholder=r"vd D:\VIDEO MỚI")
        ten_dot = c[1].text_input("Tên đợt (gắn sau tên thư mục)", value=time.strftime("%d-%m-%Y"), key="ev_loc_dot")
        chuyen = c[2].checkbox("Chuyển (không giữ bản gốc)", key="ev_loc_move")
        trung = loc_sp.trung_ten(root, ten_dot.strip()) if ten_dot.strip() else []
        if trung:
            st.error("Đã có thư mục " + ", ".join(f"`{p.name}`" for p in trung) + " trên máy. Bác đặt **tên đợt khác** "
                     "(vd thêm giờ hoặc số: `13-11-2026 lần 2`).")
        name = "loc_sp_dot"
        chay = edit_job.dang_chay(name)
        ok = nguon.strip() and Path(nguon.strip()).is_dir() and ten_dot.strip() and not trung
        if nguon.strip() and not Path(nguon.strip()).is_dir():
            st.caption("Không thấy thư mục này.")
        if st.button("Bắt đầu lọc", type="primary", disabled=chay or not ok):
            cfg = edit_job.JOB_DIR / "loc_sp.json"
            cfg.parent.mkdir(parents=True, exist_ok=True)
            cfg.write_text(json.dumps({"nguon": nguon.strip(), "ten_dot": ten_dot.strip(), "chuyen": bool(chuyen)},
                                      ensure_ascii=False), encoding="utf-8")
            edit_job.chay_ngam(name, "loc_sp", "dot", str(cfg), env=_env(), flags=_flags())
            st.rerun()
        _job_box(name, "Tự lọc video")


def _thong_tin(S, sp):
    from . import san_pham
    info = kich_ban.SAN_PHAM[sp]
    with st.expander("Thông tin sản phẩm (AI dựa vào đây để viết lời)" + ("" if info.get("thong_tin") else " · CHƯA CÓ"),
                     expanded=not info.get("thong_tin")):
        c = st.columns(2)
        ten = c[0].text_input("Tên đọc trong video", info["ten"], key=f"ev_sp_ten_{sp}")
        qc = c[1].text_input("Quy cách", info["quy_cach"], key=f"ev_sp_qc_{sp}")
        tt = st.text_area("Thành phần · công dụng · cách pha · lưu ý (chỉ ghi điều đúng, AI không bịa thêm)",
                          info.get("thong_tin", ""), height=140, key=f"ev_sp_tt_{sp}")
        nh = st.text_input("Chữ in trên nhãn (để máy nhận ra, cách nhau dấu phẩy, không dấu)",
                           ", ".join(info.get("nhan", [])), key=f"ev_sp_nh_{sp}")
        tf = st.text_input("Từ khoá trong tên file", ", ".join(info.get("ten_file", [])), key=f"ev_sp_tf_{sp}")
        if st.button("Lưu thông tin sản phẩm", key=f"ev_sp_save_{sp}"):
            san_pham.luu(sp, ten=ten.strip(), quy_cach=qc.strip(), thong_tin=tt.strip(),
                         nhan=[san_pham.khong_dau(x.strip()) for x in nh.split(",") if x.strip()],
                         ten_file=[x.strip() for x in tf.split(",") if x.strip()])
            st.success("Đã lưu")
            st.rerun()


def render(S):
    st.subheader("Sonix Edit Video: kịch bản → lồng tiếng → dựng sẵn dự án CapCut")
    _loc(S)
    sps = list(kich_ban.SAN_PHAM)
    sp = st.radio("Sản phẩm", sps, horizontal=True, key="ev_sp",
                  format_func=lambda k: kich_ban.SAN_PHAM[k]["ten"])
    _thong_tin(S, sp)
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
