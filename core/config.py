"""Cài đặt chung của SonixDangVideo: đường dẫn, tên thư mục, đọc/ghi settings.json."""
import copy
import json
import re
import unicodedata
from pathlib import Path

APP_NAME = "SonixDangVideo"
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"            # KHÔNG chia sẻ (đăng nhập TikTok, token, API key)
PROFILES_DIR = DATA_DIR / "profiles"    # mỗi kênh 1 hồ sơ trình duyệt riêng
LOG_DIR = DATA_DIR / "logs"
DEBUG_DIR = LOG_DIR / "debug"
WORK_DIR = DATA_DIR / "work"            # ảnh khung hình, ảnh bìa, video đã ghép nhạc
SHOWCASE_DIR = DATA_DIR / "showcase"    # danh sách sản phẩm trưng bày từng kênh
SOUNDS_DIR = DATA_DIR / "sounds"        # âm thanh Yêu thích đã đồng bộ (để nghe thử)
REF_DIR = DATA_DIR / "ref"              # ảnh mẫu sản phẩm cho AI so sánh
LOCK_DIR = DATA_DIR / "locks"
DB_FILE = DATA_DIR / "sonix.db"
SETTINGS_FILE = DATA_DIR / "settings.json"
HEARTBEAT_FILE = DATA_DIR / "runner_heartbeat.txt"
RUNNER_LOG = LOG_DIR / "runner.log"

FOLDER_TODO = "CHƯA UP"
FOLDER_DONE = "ĐÃ UP"
FOLDER_ERR = "VIDEO LỖI"
FOLDER_MUSIC = "NHẠC NỀN"
FOLDER_COVER = "ẢNH BÌA"            # ảnh bìa có sẵn (theme) bác tự làm

VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm"}
AUDIO_EXTS = {".mp3", ".m4a", ".wav", ".aac", ".ogg"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

MODELS = {
    "claude-opus-5-5": "Opus · nhận diện & viết hay nhất (~1.300đ/video)",
    "claude-sonnet-5-5": "Sonnet · cân bằng (~650đ/video)",
    "claude-haiku-5-5": "Haiku · rẻ nhất (~50đ/video)",
    "gemini-3.5-flash-lite": "Gemini 3.5 Flash-Lite · MIỄN PHÍ (cần Gemini API key, giới hạn lượt/ngày)",
    "gemini-3.8-flash": "Gemini 3.8 Flash · MIỄN PHÍ (nhìn kỹ hơn, ít lượt/ngày hơn)",
}
NO_AI = "khong_ai"

# Danh mục sản phẩm cần nhận diện trong video (sửa được trong tool)
DEFAULT_ITEMS = [
    {"key": "dam_ca_1l", "name": "Đạm cá Amino can 1 lít",
     "hints": "Can nhựa trắng NHỎ loại 1 lít (có quai nhỏ, cầm gọn trong 1 tay), nhãn ĐẠM CÁ AMINO. "
              "Video có cả can nhỏ và can lớn thì chọn can đang được cầm/giới thiệu",
     "keywords": "đạm cá, 1 lít, 1l", "cart": "Đạm Cá Amino 1 Lít"},
    {"key": "dam_ca_5l", "name": "Đạm cá Amino can 5 lít",
     "hints": "Can nhựa trắng LỚN 5 lít (to gấp 3-4 lần can 1 lít, quai xách to, thường đặt dưới đất), "
              "nhãn ĐẠM CÁ AMINO",
     "keywords": "đạm cá, 5 lít, 5l", "cart": "Đạm Cá Amino Can 5 Lít"},
    {"key": "tc01", "name": "Kích rễ giâm cành TC01",
     "hints": "Chai nhựa màu xanh lá, nắp xanh, chữ KÍCH RỄ GIẢM CÀNH / GIÂM CÀNH TC 01",
     "keywords": "tc01, tc 01", "cart": "Kích Rễ Giâm Cành TC01"},
    {"key": "top_one", "name": "Bọ trĩ Top One 200ml",
     "hints": "Chai 200ml, chữ TOP ONE / BO TRI ONE / bọ trĩ",
     "keywords": "top one, tri one", "cart": "Bọ Trĩ Top One 200ml"},
    {"key": "nano_dong", "name": "Nano Đồng tẩy vườn 500ml",
     "hints": "Chai 500ml, chữ NANO ĐỒNG / tẩy vườn",
     "keywords": "nano đồng, 500ml", "cart": "Nano Đồng Tẩy Vườn 500ml"},
    {"key": "bam_dinh", "name": "Siêu bám dính 100ml",
     "hints": "Chai nhỏ 100ml, chữ SIÊU BÁM DÍNH TOÀN CẦU",
     "keywords": "bám dính", "cart": "Siêu Bám Dính 100ml"},
]

DEFAULTS = {
    "root_folder": "",
    # mỗi kênh: {"name": "Sơn Phân Thuốc", "handle": "sonphanthuoc", "profile_dir": "", "enabled": True}
    "channels": [],
    "items": DEFAULT_ITEMS,
    # {"Tên kênh": {"item_key": {"cart": "Tên giỏ", "ids": ["1735..."]}}}
    "channel_products": {},
    "anthropic_api_key": "",
    "gemini_api_key": "",                 # Gemini API key (aistudio.google.com) — gói miễn phí
    "ai_model": "claude-haiku-5-5",   # rẻ nhất (~50đ/video), đọc nhãn sản phẩm tốt
    "default_hashtags": "nongnghiep, phanbon",
    "caption_guide": "",                  # hướng dẫn AI viết caption (chung mọi kênh)
    "caption_guide_by_channel": {},
    "cover_by_product": {},               # {"Tên kênh": {"key sản phẩm": "tên ảnh trong thư mục ẢNH BÌA"}}       # {"Tên kênh": "hướng dẫn riêng"}
    "caption_max_chars": 150,             # độ dài tối đa caption (ký tự)
    "golden_hours": ["05:45", "11:30", "19:30", "21:00"],
    "plan": {"per_day": 4, "gap_min": 90, "start": "05:00", "end": "22:30",
             "golden_first": True, "golden_per_slot": 1},
    "tt_confirm_before_post": False,  # True = dừng trên TikTok cho người dùng xem lại trước khi bấm Đăng
    "tt_ask_on_fail": True,           # bước nào tool không làm được -> nhờ người dùng làm tay
    "tt_headless": False,
    "tt_max_ahead_days": 10,          # TikTok cho hẹn giờ tối đa ~10 ngày
    "tt_gap_seconds": [10, 25],       # nghỉ giữa 2 lần tải video lên (giây)
    "tt_fast": True,                  # đăng nhanh: rút ngắn thời gian chờ giữa các bước
    "default_visibility": "public",
    "exclude_tags": ["HÀNG TẶNG", "LIVESTREAM"],  # sản phẩm có nhãn này không dùng gắn video
    "default_disclosure": "own_brand",    # tự tick "Thương hiệu của bạn" ở mục Khai báo nội dung bài đăng
    "lan_access": False,                  # cho mở tool trên điện thoại cùng Wi-Fi
    "app_pin": "",                        # mã PIN khi mở từ điện thoại
    "music_volume": 0.15,
    "auto_fav_sound": True,               # tự gắn âm thanh Yêu thích đúng sản phẩm khi duyệt (tắt âm gốc)
    "default_keep_audio": False,          # video mới: False = TẮT âm thanh gốc (chỉ còn nhạc), True = giữ
    "default_music": "auto::smart",       # nhạc mặc định cho video mới
    "tt_music_db": -14,                   # âm lượng nhạc TikTok khi video có giọng nói (0 = giữ nguyên)
    "music_keywords": ["nhạc vui tươi", "nhạc quê hương", "nhạc sôi động"],
    # Facebook (giữ nguyên như bản cũ)
    "facebook_pages": [],
    "fb_graph_version": "v23.0",
    "fb_last_folder": "",
}


def ensure_dirs():
    for d in (DATA_DIR, PROFILES_DIR, LOG_DIR, DEBUG_DIR, WORK_DIR, SHOWCASE_DIR, SOUNDS_DIR, REF_DIR, LOCK_DIR):
        d.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict:
    ensure_dirs()
    data = copy.deepcopy(DEFAULTS)
    if SETTINGS_FILE.exists():
        try:
            saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            data.update(saved)
            data["plan"] = {**DEFAULTS["plan"], **saved.get("plan", {})}
        except Exception:
            pass
    return data


def save_settings(data: dict):
    ensure_dirs()
    tmp = SETTINGS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(SETTINGS_FILE)


def strip_accents(text: str) -> str:
    t = unicodedata.normalize("NFD", text or "").replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def slug(text: str) -> str:
    t = re.sub(r"[^a-zA-Z0-9]+", "_", strip_accents(text)).strip("_").lower()
    return t or "kenh"


def norm(text: str) -> str:
    """Chuẩn hoá để so khớp: bỏ dấu, chữ thường, gom khoảng trắng."""
    return re.sub(r"\s+", " ", strip_accents(text).lower()).strip()


def ai_key(settings, model) -> str:
    """API key cần cho mức AI này (Gemini dùng key Google, còn lại dùng key Claude)."""
    k = settings.get("gemini_api_key") if str(model).startswith("gemini") else settings.get("anthropic_api_key")
    return (k or "").strip()


def channel_plan(settings, channel) -> dict:
    """Cài đặt xếp lịch của 1 kênh (kênh chưa lưu riêng thì dùng cài đặt chung)."""
    return {**settings["plan"], **(settings.get("plan_by_channel") or {}).get(channel, {})}


def get_channel(settings, name):
    return next((c for c in settings.get("channels", []) if c["name"] == name), None)


def profile_dir(settings, name) -> Path:
    ch = get_channel(settings, name) or {}
    custom = (ch.get("profile_dir") or "").strip()
    p = Path(custom) if custom else PROFILES_DIR / slug(name)
    p.mkdir(parents=True, exist_ok=True)
    return p
