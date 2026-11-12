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
INPUT_ROOT = Path(r"D:\VIDEO_INPUT")
TAI_NGUYEN = "TÀI NGUYÊN"
TEMPLATE = "mẫu"
THAM_KHAO_DIR = EDIT_DIR / "tham_khao"


def input_root(S: dict = None) -> Path:
    return Path((S or {}).get("edit_input_root") or INPUT_ROOT)


def thu_muc_clip(sp_key: str, root: Path = None) -> list:
    folder = Path(root or INPUT_ROOT) / kich_ban.SAN_PHAM[sp_key]["thu_muc"]
    return sorted(p for p in folder.rglob("*") if p.suffix.lower() in VIDEO_EXTS)


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
    app_id, token = vbee.keys(S)
    if S.get("edit_voice_engine", "vbee") == "vbee" and app_id and token:
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


def tao_du_an(sp_key: str, kb: dict, giong_path: str, S: dict, ten: str = "", nhac: str = "", luoi: bool = True,
              seed=None) -> dict:
    """Chọn cảnh theo câu thoại rồi tạo dự án CapCut. nhac: đường dẫn file nhạc, '' = ngẫu nhiên, 'none' = không."""
    from core import canh
    dur = probe(giong_path)["duration"]
    clips = canh.chon(sp_key, canh.chia_cau(kb["loi"], dur), seed=seed, luoi=luoi)
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
