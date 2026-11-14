"""Màn hình phong cách Sơn 01 (tab Edit video): gói phong cách -> thư viện cảnh minh hoạ -> dựng -> kết quả."""
import json
import os
import time
from pathlib import Path

import streamlit as st

from . import edit_job, edit_video
from .config import VIDEO_EXTS, save_settings
from .san_pham import SAN_PHAM


def _ui():
    from . import edit_ui
    return edit_ui


def _job(name, kind, sub, cfg: dict):
    f = edit_job.JOB_DIR / f"{name}.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    e = _ui()
    edit_job.chay_ngam(name, kind, sub, str(f), env=e._env(), flags=e._flags())
    st.rerun()


def _goi(S):
    from .son01 import goi
    g = goi.thong_tin()
    name = "son01_goi_chay"
    chay = edit_job.dang_chay(name)
    with st.container(border=True):
        if g:
            st.markdown(f"**1. Gói phong cách** · đã cài · đóng gói {g.get('luc', '?')} · khuôn '{g.get('khuon_goc', '')}' "
                        f"/ timeline '{g.get('timeline', '')}'")
        else:
            st.markdown("**1. Gói phong cách** · **chưa cài**. Gói gồm khuôn CapCut của anh Sơn, hiệu ứng, font, "
                        "nhạc + tiếng hiệu ứng (khoảng 30 MB). Bấm dựng lần đầu app cũng tự tải.")
        c = st.columns([1, 2])
        if c[0].button("Cài lại gói từ GitHub" if g else "Tải + cài gói Sơn 01", disabled=chay, key="s1_cai"):
            _job(name, "son01_goi", "chay", {"viec": "cai"})
        z = c[1].text_input("…hoặc cài từ file gói .zip trên máy (dán đường dẫn)", key="s1_zip",
                            placeholder=r"vd D:\goi_son01.zip")
        if z and c[1].button("Cài từ file này", disabled=chay or not Path(z.strip('" ')).exists(), key="s1_cai_zip"):
            _job(name, "son01_goi", "chay", {"viec": "cai", "zip": z.strip('" ')})
        with st.expander("Đóng gói phong cách (máy có dự án khuôn trong CapCut, để chia sẻ cho máy khác)"):
            goc = goi.drafts_dir()
            k = st.text_input("Dự án khuôn trong CapCut", value=S.get("son01_khuon", "DAMBOTC01_SONIX"), key="s1_kh")
            tl = st.text_input("Timeline mẫu trong dự án", value=S.get("son01_timeline", "Đạm shop Bọ"), key="s1_tl")
            ra = edit_job.JOB_DIR.parent / "goi_son01.zip"
            co = (goc / k / "draft_content.json").exists()
            st.caption(f"Thư mục dự án CapCut: `{goc}` · khuôn: {'có' if co else '**không thấy**'} · gói ra: `{ra}`. "
                       "Đóng gói xong: vào GitHub > Releases > tag `goi-son01`, tải file lên để máy khác tự cài.")
            if st.button("Đóng gói", disabled=chay or not co, key="s1_dg"):
                S["son01_khuon"], S["son01_timeline"] = k, tl
                save_settings(S)
                _job(name, "son01_goi", "chay", {"viec": "dong_goi", "khuon": str(goc / k), "timeline": tl,
                                                 "ra": str(ra)})
        _ui()._job_box(name, "Gói phong cách Sơn 01")


def _thu_vien(S):
    from . import son01
    ds = son01.ds_thu_vien()
    name = "son01_tv_lap"
    chay = edit_job.dang_chay(name)
    with st.container(border=True):
        st.markdown("**2. Thư viện cảnh minh hoạ** · cảnh aff / video AI (mô phỏng rễ, ra đọt, pha thuốc, vườn đẹp...) "
                    "để chèn vào video. App tự tách cảnh, AI gắn nhãn, soi chữ để không chèn nhầm sản phẩm hãng khác.")
        if ds:
            st.caption(" · ".join(f"**{x['ten']}**: {x['dung_duoc']}/{x['so_canh']} cảnh dùng được" for x in ds))
        else:
            st.caption("Chưa có thư viện nào: video sẽ không có cảnh minh hoạ.")
        c = st.columns([3, 1])
        d = c[0].text_input("Thư mục video minh hoạ", value=S.get("son01_tv_dir", ""), key="s1_tvd",
                            placeholder=r"vd D:\VIDEO_AFF 3\Dam_Ca")
        d = d.strip('" ')
        c[1].write("")
        if c[1].button("Lập thư viện", disabled=chay or not d or not Path(d).is_dir(), key="s1_tv"):
            S["son01_tv_dir"] = d
            save_settings(S)
            f = edit_job.JOB_DIR / f"{name}.txt"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(d, encoding="utf-8")
            e = _ui()
            edit_job.chay_ngam(name, "son01_tv", "lap", str(f), env=e._env(), flags=e._flags())
            st.rerun()
        st.caption("Mỗi thư mục 1 thư viện; lập lại cùng thư mục thì chỉ làm thêm video mới. Tốn ít phí AI (xem ảnh "
                   "thu nhỏ, 30 cảnh/lần).")
        with st.expander("Video AI tạo cảnh mô phỏng (Veo) · " + ("đã có key" if S.get("veo_api_key") else "chưa có key")):
            st.caption("Dùng sau: tạo cảnh mô phỏng giống thật (rễ bung, cây hấp thụ, côn trùng chích hút) bằng AI. "
                       "Key chỉ lưu trên máy này.")
            v = st.text_input("Key Veo", value=S.get("veo_api_key", ""), type="password", key="s1_veo")
            if st.button("Lưu key", key="s1_veo_luu"):
                S["veo_api_key"] = v.strip()
                save_settings(S)
                st.success("Đã lưu")
        _ui()._job_box(name, "Lập thư viện cảnh")


def _ds_video(S, source) -> list:
    if not source:
        return []
    from .phong_cach import SOURCE
    d = edit_video.input_root(S) / SOURCE / source
    if not d.is_dir():
        return []
    v = [p for p in d.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
    return sorted(v, key=lambda p: p.stat().st_mtime, reverse=True)


def _dung(S, ten_pc):
    from . import phong_cach
    b = phong_cach.bo(ten_pc)
    name = "son01_dung"
    chay = edit_job.dang_chay(name)
    with st.container(border=True):
        st.markdown(f"**3. Dựng video** · bỏ video tự quay vào `SOURCE THÔ\\{b['source'] or '...'}` hoặc dán đường dẫn")
        vids = _ds_video(S, b["source"])
        c = st.columns([3, 2])
        chon = c[0].selectbox("Video quay thô", [""] + [str(v) for v in vids], key="s1_vid",
                              format_func=lambda x: Path(x).name if x else ("— chọn —" if vids else "— thư mục trống —"))
        tay = c[1].text_input("…hoặc đường dẫn video", key="s1_vid_tay", placeholder=r"vd E:\SOURCE THÔ\C3420.MP4")
        video = tay.strip('" ') or chon
        sps = list(SAN_PHAM)
        sp = st.radio("Sản phẩm trong video", sps, horizontal=True, key="s1_sp", format_func=lambda k: SAN_PHAM[k]["ten"],
                      index=sps.index(S.get("son01_sp")) if S.get("son01_sp") in sps else 0)
        c = st.columns([3, 1, 1, 1])
        ten = c[0].text_input("Tên dự án CapCut", value=f"SONIX SƠN 01 - {SAN_PHAM[sp]['ten'].upper()}", key=f"s1_ten_{sp}")
        dai = c[1].number_input("Dài (giây)", 20, 90, int(S.get("son01_dai", 36)), key="s1_dai")
        vong = c[2].number_input("Số lần sửa tối đa", 1, 5, 3, key="s1_vong")
        dat = c[3].number_input("Điểm đạt", 6.0, 9.5, 8.0, 0.5, key="s1_dat")
        ok_video = bool(video) and Path(video).exists()
        if video and not ok_video:
            st.warning("Không thấy file video này.")
        st.caption("Tắt CapCut trước khi bấm. Mỗi lần dựng: nghe lời (2-3 phút lần đầu) → AI lên kế hoạch → dự án "
                   "CapCut → xem trước → AI chấm; dưới điểm đạt thì tự sửa, dựng lại. Phí AI khoảng vài nghìn đồng / lần.")
        if st.button("Dựng", type="primary", disabled=chay or not ok_video or not S.get("anthropic_api_key"), key="s1_go"):
            S["son01_sp"], S["son01_dai"] = sp, int(dai)
            save_settings(S)
            _job(name, "son01", "dung", {"video": video, "sp": sp, "ten": ten, "vong": int(vong), "dat": float(dat),
                                         "dai": int(dai)})
        if not S.get("anthropic_api_key"):
            st.warning("Cần key Claude (tab Cài đặt) để AI lên kế hoạch và chấm điểm.")
        _ui()._job_box(name, "Dựng video Sơn 01")


def _ket_qua():
    from . import son01
    ds = son01.ket_qua_gan_day()
    if not ds:
        return
    with st.container(border=True):
        st.markdown("**4. Kết quả gần đây**")
        for i, k in enumerate(ds):
            d = k.get("diem")
            st.markdown(f"`{k.get('luc', '')}` · **{k.get('du_an', '')}** · điểm **{d}/10** "
                        f"{'✅' if isinstance(d, (int, float)) and d >= 8 else '⚠️'} · lần {k.get('vong', '')}")
            if k.get("loi"):
                with st.expander("AI nhận xét chỗ chưa ổn"):
                    for l in k["loi"]:
                        st.markdown(f"- {l.get('giay', 0):.1f}s [{l.get('tieu_chi', '')}] {l.get('mo_ta', '')}")
            xt = k.get("xem_truoc")
            if xt and Path(xt).exists() and i == 0:
                c = st.columns([1, 2])
                c[0].video(xt)
                c[1].caption("Bản xem trước do tool tự dựng (gần giống CapCut). Mở CapCut để chỉnh tiếp, rồi xuất.")
                if c[1].button("Mở thư mục", key=f"s1_mo_{i}"):
                    os.startfile(str(Path(xt).parent))  # noqa


def render(S, ten_pc):
    _goi(S)
    _thu_vien(S)
    _dung(S, ten_pc)
    _ket_qua()
