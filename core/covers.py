"""Ảnh bìa có sẵn (theme): thư mục <gốc>\\ẢNH BÌA.

Bác bỏ ảnh vào thư mục đó (hoặc bấm tải lên trong tool), rồi chọn cho từng video hay hàng loạt.
Trước khi tải lên TikTok, tool chỉnh ảnh về đúng khung của video: ảnh đúng khung thì giữ nguyên,
ảnh lệch khung thì đặt nguyên ảnh ở giữa trên nền mờ (không cắt mất chữ).
"""
import hashlib
import time
from pathlib import Path

from .config import FOLDER_COVER, IMAGE_EXTS, WORK_DIR

THUMB_DIR = WORK_DIR / "theme_thumbs"
PREFIX = "theme__"


def cover_dir(root) -> Path:
    return Path(root) / FOLDER_COVER


def theme_files(root) -> list:
    d = cover_dir(root) if root else None
    if not d or not d.is_dir():
        return []
    return sorted((p for p in d.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS),
                  key=lambda p: p.name.lower())


def _open(path):
    from PIL import Image, ImageOps
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)  # ảnh chụp điện thoại: xoay đúng chiều
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        return bg
    return img.convert("RGB")


def thumb(path) -> str:
    """Ảnh nhỏ để xem trước (đỡ nặng giao diện). Lưu sẵn, ảnh gốc đổi thì làm lại."""
    p = Path(path)
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    out = THUMB_DIR / f"{hashlib.md5(str(p).encode()).hexdigest()[:12]}_{int(p.stat().st_mtime)}.jpg"
    if not out.exists():
        img = _open(p)
        img.thumbnail((240, 427))
        img.save(out, "JPEG", quality=80)
    return str(out)


def save_upload(root, name, data: bytes) -> Path:
    """Lưu ảnh bác tải lên vào thư mục ẢNH BÌA (trùng tên thì thêm số, không ghi đè ảnh cũ)."""
    import io
    from PIL import Image
    Image.open(io.BytesIO(data)).verify()  # không phải ảnh thì báo lỗi ngay
    d = cover_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    dst = d / Path(name).name
    if dst.exists():
        if dst.read_bytes() == data:
            return dst
        dst = dst.with_name(f"{dst.stem}_{int(time.time())}{dst.suffix}")
    dst.write_bytes(data)
    return dst


def _frame_size(job):
    """Khung của video (rộng, cao) — ưu tiên đo từ ảnh bìa khung hình tool đã cắt, không có thì đọc video."""
    from PIL import Image
    auto = WORK_DIR / str(job["id"]) / "cover.jpg"
    try:
        if auto.exists():
            return Image.open(auto).size
    except Exception:
        pass
    from .video_utils import probe
    info = probe(job["video_path"])
    return (info["width"], info["height"]) if info["width"] and info["height"] else (1080, 1920)


def make_cover(job, theme) -> str:
    """Chỉnh ảnh theme về đúng khung video, lưu thành ảnh bìa riêng của video này. Trả về đường dẫn."""
    from PIL import ImageEnhance, ImageFilter
    src = _open(theme)
    fw, fh = _frame_size(job)
    W = 1080
    H = max(2, round(W * fh / fw))
    r_img, r_vid = src.width / src.height, W / H
    if abs(r_img - r_vid) / r_vid < 0.03:  # đúng khung (vd ảnh 9:16 làm trên Canva)
        out = src.resize((W, H))
    else:
        # nền: chính ảnh đó phóng to phủ kín khung rồi làm mờ, hơi tối; giữa: nguyên ảnh, không cắt
        s = max(W / src.width, H / src.height)
        bg = src.resize((max(W, round(src.width * s)), max(H, round(src.height * s))))
        left, top = (bg.width - W) // 2, (bg.height - H) // 2
        bg = bg.crop((left, top, left + W, top + H)).filter(ImageFilter.GaussianBlur(28))
        out = ImageEnhance.Brightness(bg).enhance(0.75)
        s = min(W / src.width, H / src.height)
        fg = src.resize((round(src.width * s), round(src.height * s)))
        out.paste(fg, ((W - fg.width) // 2, (H - fg.height) // 2))
    d = WORK_DIR / str(job["id"])
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob(PREFIX + "*.jpg"):  # chỉ giữ 1 ảnh theme mỗi video
        old.unlink(missing_ok=True)
    dst = d / f"{PREFIX}{Path(theme).stem}.jpg"
    out.save(dst, "JPEG", quality=92)
    return str(dst)


def theme_name(cover_path) -> str:
    """Tên ảnh theme đang dùng làm bìa ('' nếu bìa là khung hình cắt từ video)."""
    n = Path(cover_path or "").stem
    return n[len(PREFIX):] if n.startswith(PREFIX) else ""


def default_for(settings, channel, item_key) -> str:
    """Tên ảnh bìa mặc định bác đặt cho sản phẩm này ở kênh này ('' nếu chưa đặt)."""
    return ((settings.get("cover_by_product") or {}).get(channel) or {}).get(item_key or "", "")


def auto_assign(channel, settings, jobs, root) -> list:
    """Video bác CHƯA tự chọn bìa: dùng ảnh bìa mặc định của sản phẩm (nếu đã đặt). Đổi sản phẩm thì bìa đổi theo;
    sản phẩm không có bìa mặc định thì quay về khung hình AI chọn. Trả về id các video vừa đổi bìa."""
    if not root:
        return []
    from . import db
    changed = []
    for j in jobs:
        if int(j.get("cover_by_user") or 0):
            continue  # bác đã tự chọn bìa -> giữ nguyên
        name = default_for(settings, channel, j.get("item_key"))
        theme = cover_dir(root) / name if name else None
        cur = j.get("cover_path") or ""
        try:
            if theme and theme.exists():
                if (theme_name(cur) == theme.stem and Path(cur).exists()
                        and Path(cur).stat().st_mtime >= theme.stat().st_mtime):
                    continue  # đang đúng ảnh mặc định
                new = make_cover(j, theme)
            elif theme_name(cur):  # đang dùng bìa mặc định cũ mà sản phẩm không còn -> về khung hình AI chọn
                auto = WORK_DIR / str(j["id"]) / "cover.jpg"
                if not auto.exists():
                    continue
                new = str(auto)
            else:
                continue
        except Exception:
            continue
        db.update_job(j["id"], cover_path=new)
        j["cover_path"] = new
        changed.append(j["id"])
    return changed
