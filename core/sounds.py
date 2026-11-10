"""Âm thanh Yêu thích trên TikTok: danh sách, file nghe thử, gắn sản phẩm cho từng âm thanh.

Nhận diện âm thanh nói về sản phẩm nào: Whisper (chạy trên máy, miễn phí) chuyển giọng nói thành chữ,
rồi dò tên sản phẩm trong đoạn chữ. Người dùng nghe thử và sửa lại được trong tab 🎵 Nhạc nền.
"""
import json
import re
import subprocess
import threading
from pathlib import Path

from .config import DATA_DIR, SOUNDS_DIR, norm, slug

MODEL_DIR = DATA_DIR / "models"
_model = None
_model_lock = threading.Lock()

# Từ chỉ dung tích (1 lít, 500ml, can 5...) chỉ để phân biệt cỡ can, không tính là "nhắc tên sản phẩm"
SIZE = re.compile(r"^((\d+|mot|nam)\s*(l|lit|ml)|can \d+)$")

# Cách người ta hay NÓI tên sản phẩm (ngoài từ khoá trong danh mục). Dò không dấu, không phân biệt hoa thường.
SPOKEN = {
    "dam_ca_1l": ["đạm cá", "amino", "dịch cá", "1 lít", "một lít"],
    "dam_ca_5l": ["đạm cá", "amino", "dịch cá", "5 lít", "năm lít", "can 5"],
    "tc01": ["kích rễ", "giâm cành", "tc01", "tc 01", "tê xê", "ti xi", "ra rễ"],
    "top_one": ["bọ trĩ", "bò trễ", "top one", "top 1", "tóp oăn", "bù lạch"],
    "nano_dong": ["nano đồng", "nano", "rong rêu", "tẩy vườn", "rửa vườn", "tẩy rửa", "tây rượt", "phục hồi vườn",
                  "vệ sinh vườn", "nấm hồng", "đồng nano"],
    "bam_dinh": ["bám dính", "chất bám dính", "trải đều"],
}


def fav_file(channel) -> Path:
    return SOUNDS_DIR / slug(channel) / "favorites.json"


def load_favs(channel) -> list:
    f = fav_file(channel)
    try:
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
    except Exception:
        return []


def save_favs(channel, favs):
    f = fav_file(channel)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(favs, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(f)


def ref_of(fav) -> str:
    """Mã để tool tìm đúng âm thanh lúc đăng (nhiều âm thanh trùng tên 'original sound')."""
    return f"id:{fav['id']}|{fav.get('title', '')}" if fav.get("id") else fav.get("title", "")


def parse_ref(ref: str):
    """'id:123|tên' -> ('123', 'tên'); 'tên' -> ('', 'tên')."""
    if ref.startswith("id:"):
        mid, _, title = ref[3:].partition("|")
        return mid, title
    return "", ref


def _has(text, word) -> bool:
    """Có NGUYÊN TỪ này trong câu không ("dam ca" không được tính trong "dam canh")."""
    return re.search(r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])", text) is not None


def guess_items(text, settings) -> list:
    """Dò tên sản phẩm trong lời nói. Trả về danh sách key sản phẩm (có thể nhiều, vd đạm cá 1 lít + 5 lít)."""
    t = norm(text)
    if not t:
        return []
    scores = {}
    for it in settings.get("items", []):
        words = SPOKEN.get(it["key"], []) + [x for x in (it.get("keywords") or "").split(",")]
        hits = {norm(w) for w in words if len(norm(w)) >= 3 and not SIZE.match(norm(w)) and _has(t, norm(w))}
        if hits:
            scores[it["key"]] = len(hits)
    if not scores:
        return []
    # đạm cá: nói rõ dung tích thì chọn đúng loại, không thì gắn cả 2
    if "dam_ca_1l" in scores and "dam_ca_5l" in scores:
        five = any(_has(t, norm(w)) for w in ("5 lít", "năm lít", "can 5"))
        one = any(_has(t, norm(w)) for w in ("1 lít", "một lít"))
        if five and not one:
            scores.pop("dam_ca_1l")
        elif one and not five:
            scores.pop("dam_ca_5l")
    best = max(scores.values())
    return sorted(k for k, v in scores.items() if v == best)  # chỉ giữ sản phẩm được nhắc nhiều nhất


def _ffmpeg():
    from .video_utils import _ffmpeg as ff
    return ff()


def _read_audio(path):
    import numpy as np
    p = subprocess.run([_ffmpeg(), "-hide_banner", "-loglevel", "error", "-i", str(path), "-t", "180", "-f", "s16le",
                        "-ac", "1", "-ar", "16000", "-"], capture_output=True, creationflags=0x08000000)
    return np.frombuffer(p.stdout, np.int16).astype(np.float32) / 32768.0


def whisper_ok() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except Exception:
        return False


def transcribe(path, log=print) -> str:
    """Giọng nói -> chữ (tiếng Việt). Lần đầu tải mô hình khoảng 480 MB vào data/models."""
    global _model
    import logging
    logging.getLogger("faster_whisper").setLevel(logging.WARNING)  # bớt dòng kỹ thuật trong nhật ký
    from faster_whisper import WhisperModel
    with _model_lock:
        if _model is None:
            log("  - Nạp bộ nghe giọng nói (lần đầu phải tải ~480 MB, chờ chút)...")
            _model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=8,
                                  download_root=str(MODEL_DIR))
    segs, _ = _model.transcribe(_read_audio(path), language="vi", vad_filter=True, beam_size=1)
    return re.sub(r"\s+", " ", " ".join(s.text.strip() for s in segs)).strip()


def ai_guess(text, settings):
    """Không nghe thấy tên sản phẩm -> nhờ AI (mức AI mặc định) đọc ĐOẠN CHỮ để đoán. Chỉ gửi chữ, rất rẻ."""
    from .analyze import _claude, _gemini
    from .config import MODELS, ai_key
    m = settings.get("ai_model")
    if not text or m not in MODELS or not ai_key(settings, m):
        return None
    items = settings.get("items", [])
    keys = [it["key"] for it in items]
    lines = "\n".join(f"- {it['key']}: {it['name']} ({it.get('hints', '')})" for it in items)
    system = ("Bạn đọc lời nói (đã chuyển thành chữ) trong âm thanh TikTok của các kênh bán phân bón, thuốc bảo vệ "
              "thực vật. Cho biết đoạn lời nói đang giới thiệu hoặc nhắc tới sản phẩm nào trong danh sách. "
              "Chỉ chọn khi lời nói thật sự nói về sản phẩm đó; không chắc thì để danh sách trống.")
    schema = {"type": "object", "additionalProperties": False, "required": ["products", "reason"],
              "properties": {"products": {"type": "array", "items": {"type": "string", "enum": keys}},
                             "reason": {"type": "string"}}}
    content = [{"type": "text", "text": f"Danh sách sản phẩm:\n{lines}\n\nLời nói:\n\"{text[:1500]}\""}]
    fn = _gemini if str(m).startswith("gemini") else _claude
    data = fn(content, schema, settings, m, system)
    return [k for k in (data.get("products") or []) if k in keys]


def label_all(channel, settings, log=print, force=False) -> int:
    """Nghe âm thanh chưa có chữ rồi tự gắn sản phẩm (force: dò lại cả cái đã có chữ). Không đè nhãn bác đã sửa."""
    favs = load_favs(channel)
    n = 0
    for f in favs:
        if not f.get("file") or not Path(f["file"]).exists():
            continue
        if f.get("transcript") is not None and not force:
            continue
        if f.get("transcript") is None:  # chưa nghe thì nghe; đã có chữ thì chỉ dò lại sản phẩm
            try:
                f["transcript"] = transcribe(f["file"], log)
            except Exception as e:
                log(f"  ! Không nghe được «{f.get('title')}»: {e}")
                continue
        if f.get("items_by") != "user":
            items, by = guess_items(f["transcript"], settings), "auto"
            if not items and len(f["transcript"]) > 20:
                try:
                    ai = ai_guess(f["transcript"], settings)
                except Exception as e:
                    ai = None
                    log(f"    (AI chưa đoán được: {str(e)[:80]})")
                if ai:
                    items, by = ai, "ai"
            f["items"], f["items_by"] = items, by
        n += 1
        save_favs(channel, favs)
        names = ", ".join(f["items"]) or "không rõ sản phẩm"
        log(f"  - «{f.get('title')}» · {f.get('artist', '')}: {names} | \"{f['transcript'][:70]}...\"")
    return n


def pick_for(channel, item_key, used=None):
    """Chọn 1 âm thanh Yêu thích đã gắn đúng sản phẩm; xoay vòng để các video không trùng âm thanh."""
    used = used if used is not None else {}
    cands = [f for f in load_favs(channel) if item_key and item_key in (f.get("items") or [])
             and f.get("file") and not f.get("skip")]
    if not cands:
        return None
    cands.sort(key=lambda f: used.get(f["id"], 0))
    f = cands[0]
    used[f["id"]] = used.get(f["id"], 0) + 1
    return f


def auto_assign(channel, settings, jobs) -> list:
    """Video bác CHƯA tự chọn nhạc: gắn sẵn âm thanh Yêu thích đã nghe ra đúng sản phẩm (và tắt âm gốc), xoay vòng cho
    các video đỡ trùng. Đổi sản phẩm thì âm thanh đổi theo. Trả về id các video vừa đổi nhạc."""
    if not settings.get("auto_fav_sound", True):
        return []
    favs = load_favs(channel)
    if not any(f.get("items") for f in favs):
        return []
    from . import db
    by_id = {f["id"]: f for f in favs if f.get("id")}
    used = {}
    for j in jobs:  # âm thanh đang được các video dùng (để chọn cái ít dùng nhất)
        if j.get("music_mode") == "tiktok":
            mid = parse_ref(j.get("music_ref") or "")[0]
            if mid:
                used[mid] = used.get(mid, 0) + 1
    changed = []
    for j in jobs:
        if int(j.get("music_by_user") or 0):
            continue  # bác đã tự chọn nhạc -> để nguyên
        item = j.get("item_key") or ""
        cur = by_id.get(parse_ref(j.get("music_ref") or "")[0]) if j.get("music_mode") == "tiktok" else None
        if cur and item and item in (cur.get("items") or []) and not cur.get("skip"):
            continue  # đang đúng sản phẩm
        f = pick_for(channel, item, used) if item else None
        if f:
            upd = {"music_mode": "tiktok", "music_ref": ref_of(f), "keep_audio": 0}
        elif cur:  # âm thanh tool gắn trước đó không còn hợp (đổi sản phẩm / bỏ nhãn) -> về nhạc mặc định
            mode, _, ref = (settings.get("default_music") or "auto::smart").partition("::")
            upd = {"music_mode": mode if ref else "none", "music_ref": ref,
                   "keep_audio": int(bool(settings.get("default_keep_audio", False)))}
        else:
            continue
        if cur:
            used[cur["id"]] = max(0, used.get(cur["id"], 0) - 1)
        db.update_job(j["id"], **upd)
        j.update(upd)
        changed.append(j["id"])
    return changed
