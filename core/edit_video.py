"""Sonix Edit Video: nối cả quy trình kịch bản -> giọng -> chọn cảnh -> dự án CapCut."""
import json
import random
import re
import time
from pathlib import Path

from core import capcut_draft, giong, kich_ban, vbee
from core.config import DATA_DIR, VIDEO_EXTS
from core.video_utils import probe

EDIT_DIR = DATA_DIR / "edit"
INPUT_ROOT = Path(r"D:\SONIX_EDIT_VIDEO")
INPUT_OLD = Path(r"D:\VIDEO_INPUT")  # tên cũ trước bản 2.5.2 (core/doi_thu_muc.py tự đổi tên)
TAI_NGUYEN = "TÀI NGUYÊN"
TEMPLATE = "mẫu"
THAM_KHAO_DIR = EDIT_DIR / "tham_khao"


def input_root(S: dict = None) -> Path:
    p = (S or {}).get("edit_input_root")
    if p:
        return Path(p)
    return INPUT_ROOT if INPUT_ROOT.exists() or not INPUT_OLD.exists() else INPUT_OLD


def thu_muc_sp(sp_key: str, root: Path = None) -> list:
    """Mọi thư mục của sản phẩm: "KÍCH RỄ", "KÍCH RỄ 13-11-2026" (các đợt tự lọc)... (so không phân biệt dấu)."""
    from core.san_pham import khong_dau
    root = Path(root or input_root())
    ten = khong_dau(kich_ban.SAN_PHAM[sp_key]["thu_muc"])
    if not root.exists():
        return []
    return sorted(d for d in root.iterdir() if d.is_dir() and (khong_dau(d.name) == ten
                                                               or khong_dau(d.name).startswith(ten + " ")))


def thu_muc_clip(sp_key: str, root: Path = None) -> list:
    out = []
    for folder in thu_muc_sp(sp_key, root):
        out += [p for p in folder.rglob("*") if p.suffix.lower() in VIDEO_EXTS]
    return sorted(set(out))


def nhac_nen(root: Path = None) -> list:
    folder = Path(root or INPUT_ROOT) / TAI_NGUYEN
    if not folder.exists():
        return []
    return sorted(p for p in folder.glob("*") if p.suffix.lower() in VIDEO_EXTS | {".mp3", ".m4a", ".wav"}
                  and "meme" not in p.stem.lower())


def kich_ban_tham_khao() -> dict:
    """{tên kênh: [lời...]} đã quét."""
    out = {}
    if THAM_KHAO_DIR.exists():
        for f in THAM_KHAO_DIR.glob("*/kich_ban.json"):
            try:
                out[f.parent.name] = [v["loi"] for v in json.loads(f.read_text(encoding="utf-8")).values() if v.get("loi")]
            except Exception:
                pass
    return out


def tao_giong(loi: str, out: Path, S: dict, log=print) -> dict:
    """Theo Cài đặt: edit_voice_engine = 'vbee' | 'mien_phi'."""
    out = Path(out)
    eng = S.get("edit_voice_engine", "vbee")
    if eng == "eleven":
        from core import elevenlabs
        k = elevenlabs.key(S)
        if k:
            log("ElevenLabs đang lồng tiếng...")
            elevenlabs.tao_giong(loi, str(out), k, S.get("eleven_voice", ""), S.get("eleven_model") or
                                 elevenlabs.DEFAULT_MODEL, float(S.get("eleven_speed") or 1.0))
            return {"path": str(out), "duration": probe(str(out))["duration"], "nguon": "elevenlabs"}
        raise elevenlabs.ElevenError("Chưa có mã ElevenLabs: dán vào mục Kết nối ElevenLabs")
    app_id, token = vbee.keys(S)
    if eng == "vbee" and app_id and token:
        log("Vbee đang lồng tiếng...")
        vbee.tao_giong(loi, str(out), app_id, token, S.get("vbee_voice") or vbee.DEFAULT_VOICE,
                       float(S.get("vbee_speed") or vbee.DEFAULT_SPEED))
        return {"path": str(out), "duration": probe(str(out))["duration"], "nguon": "vbee"}
    log("Giọng miễn phí (Microsoft) đang đọc...")
    rate = f"{round((float(S.get('free_speed') or 1.2) - 1) * 100):+d}%"
    g = giong.giong_mien_phi(loi, str(out), S.get("free_voice") or "vi-VN-HoaiMyNeural", rate=rate)
    g["nguon"] = "mien_phi"
    return g


def ten_an_toan(s: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', " ", s).strip()[:80] or "SONIX"


def nhip_phong_cach(S: dict) -> float:
    from core import mau
    return mau.doc(S["edit_phong_cach"]).get("nhip", 0) if S.get("edit_phong_cach") else 0


def chon_canh(sp_key: str, kb: dict, giong_path: str, S: dict, luoi: bool = True, seed=None) -> list:
    from core import canh
    dur = probe(giong_path)["duration"]
    return canh.chon(sp_key, canh.chia_cau(kb["loi"], dur), seed=seed, luoi=luoi, nhip=nhip_phong_cach(S))


def tao_du_an(sp_key: str, kb: dict, giong_path: str, S: dict, ten: str = "", nhac: str = "", luoi: bool = True,
              seed=None, nhip: float = None, clips: list = None) -> dict:
    """Chọn cảnh theo câu thoại (hoặc dùng clips đã duyệt) rồi tạo dự án CapCut.
    nhac: đường dẫn file nhạc, '' = ngẫu nhiên, 'none' = không. nhip: giây mỗi cảnh (None = theo phong cách đang chọn)."""
    from core import canh
    if not clips:
        dur = probe(giong_path)["duration"]
        clips = canh.chon(sp_key, canh.chia_cau(kb["loi"], dur), seed=seed, luoi=luoi,
                          nhip=nhip_phong_cach(S) if nhip is None else nhip)
    clips = [c if isinstance(c, dict) else tuple(c) for c in clips]
    if not clips:
        raise capcut_draft.CapCutError("Chưa có cảnh dùng được. Bấm 'Quét cảnh' cho sản phẩm này trước.")
    if nhac == "none":
        music = ""
    else:
        musics = nhac_nen(input_root(S))
        src = nhac or (str(random.choice(musics)) if musics else "")
        music = capcut_draft.tach_nhac(src, EDIT_DIR / "nhac") if src else ""
    ten = ten_an_toan(ten or f"SONIX {kich_ban.SAN_PHAM[sp_key]['ten']} {time.strftime('%d-%m %H%M')}")
    return capcut_draft.tao_du_an(S.get("edit_template") or TEMPLATE, ten, clips, giong_path, music, kb["tieu_de"])


def cho_capcut_tat(log=print, phut: int = 30):
    """Chờ người dùng tắt CapCut (tối đa `phut` phút)."""
    if not capcut_draft.capcut_dang_mo():
        return
    log("CapCut đang mở: bác tắt CapCut để tool ghi dự án (tool chờ tối đa 30 phút)...")
    end = time.time() + phut * 60
    while capcut_draft.capcut_dang_mo():
        if time.time() > end:
            raise capcut_draft.CapCutError("Chờ quá lâu, CapCut vẫn mở")
        time.sleep(5)


def xuat(ten_du_an: list, S: dict, kenh: str, log=print) -> list:
    """Tự xuất 1080p từ CapCut rồi đưa vào CHƯA UP\\<ngày>\\NN.mp4 của kênh."""
    from core import xuat_capcut
    cho_capcut_tat(log)
    log(f"Tự xuất {len(ten_du_an)} video vào kênh {kenh} (đừng đụng chuột / bàn phím, ~1,5 phút / video)...")
    out = xuat_capcut.xuat_va_dua(ten_du_an, S, kenh, log=log)
    log(f"Đã đưa {len(out)}/{len(ten_du_an)} video vào CHƯA UP của {kenh}")
    return out


def lam_video(sp_key: str, kb: dict, S: dict, ten: str = "", nhac: str = "", luoi: bool = True, seed=None,
              log=print, kenh: str = "") -> dict:
    """1 nút: lồng tiếng (nếu chưa có / lời đã đổi) -> chọn cảnh (hoặc dùng cảnh đã duyệt) -> tạo dự án CapCut."""
    g = kb.get("giong")
    if not g or not Path(g).exists():
        g = tao_giong(kb["loi"], EDIT_DIR / "giong" / f"{sp_key}_{time.strftime('%Y%m%d_%H%M%S')}.mp3", S, log)["path"]
        kb["giong"], kb["canh"] = g, None
        log(f"Giọng xong: {probe(g)['duration']:.1f} giây")
    clips = kb.get("canh") if kb.get("canh_giong") == g else None
    if clips:
        log(f"Dùng {len(clips)} cảnh đã duyệt")
    else:
        log("Chọn cảnh theo từng câu...")
        clips = chon_canh(sp_key, kb, g, S, luoi=luoi, seed=seed)
    cho_capcut_tat(log)
    log("Tạo dự án CapCut...")
    r = tao_du_an(sp_key, kb, g, S, ten=ten, nhac=nhac, luoi=luoi, clips=clips)
    log(f"Đã tạo dự án: {r['name']} ({r['duration']:.1f} giây)")
    if kenh:
        xuat([r["name"]], S, kenh, log)
    return r


def hang_loat(sp_key: str, n: int, S: dict, y_tuong: str = "", nhac: str = "", luoi: bool = True, log=print,
              kenh: str = "") -> list:
    """Làm n video liền: mỗi video AI viết lời mới (khác các bản trước) -> lồng tiếng -> chọn cảnh -> dự án CapCut."""
    from core import mau
    pc = mau.doc(S["edit_phong_cach"]) if S.get("edit_phong_cach") else {}
    mau_loi = mau.loi_mau(pc["ten"]) if pc else [x for v in kich_ban_tham_khao().values() for x in v]
    da, out = [], []
    stamp = time.strftime("%d-%m %H%M")
    for i in range(1, n + 1):
        log(f"=== Video {i}/{n}: AI viết lời...")
        y = y_tuong + (("\nĐÃ VIẾT CÁC BẢN SAU, bản này phải khác câu mở và cách dẫn: " + " | ".join(da[-4:]))
                       if da else "")
        try:
            kb = kich_ban.viet(sp_key, mau_loi, S, y_tuong=y, phong_cach=pc or None)
        except Exception as e:
            log(f"Viết lời lỗi: {e}")
            continue
        da.append(kb["loi"][:80])
        luu = EDIT_DIR / "hang_loat" / f"{sp_key}_{time.strftime('%Y%m%d_%H%M%S')}_{i}.json"
        luu.parent.mkdir(parents=True, exist_ok=True)
        luu.write_text(json.dumps(kb, ensure_ascii=False, indent=1), encoding="utf-8")  # lời từng video để xem lại
        try:
            r = lam_video(sp_key, kb, S, ten=f"SONIX {kich_ban.SAN_PHAM[sp_key]['ten'].upper()} {stamp} #{i}",
                          nhac=nhac, luoi=luoi, seed=i * 7, log=log)
            out.append(r)
        except Exception as e:
            log(f"Video {i} lỗi: {e}")
    log(f"Xong {len(out)}/{n} video")
    if kenh and out:
        xuat([r["name"] for r in out], S, kenh, log)
    return out
