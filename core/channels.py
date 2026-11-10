"""Thư mục theo kênh:  <gốc>\\<Kênh>\\CHƯA UP | ĐÃ UP | VIDEO LỖI   và   <gốc>\\NHẠC NỀN"""
import shutil
import time
from datetime import datetime
from pathlib import Path

from .config import (AUDIO_EXTS, FOLDER_COVER, FOLDER_DONE, FOLDER_ERR, FOLDER_MUSIC, FOLDER_TODO, VIDEO_EXTS)


def channel_dir(root, name) -> Path:
    return Path(root) / name


def ensure_structure(root, channels) -> list:
    """Tạo thư mục còn thiếu. Trả về danh sách thư mục vừa tạo."""
    created = []
    if not root:
        return created
    dirs = [Path(root) / FOLDER_MUSIC, Path(root) / FOLDER_COVER]
    for ch in channels:
        for sub in (FOLDER_TODO, FOLDER_DONE, FOLDER_ERR):
            dirs.append(channel_dir(root, ch["name"]) / sub)
    for d in dirs:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created.append(str(d))
    return created


def todo_videos(root, name) -> list:
    d = channel_dir(root, name) / FOLDER_TODO
    if not d.is_dir():
        return []
    return sorted([p for p in d.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS],
                  key=lambda p: p.stat().st_mtime)


def music_files(root) -> list:
    d = Path(root) / FOLDER_MUSIC if root else None
    if not d or not d.is_dir():
        return []
    return sorted([p for p in d.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTS])


def _unique(dst: Path) -> Path:
    if not dst.exists():
        return dst
    return dst.with_name(f"{dst.stem}_{int(time.time())}{dst.suffix}")


def move_to(video_path, root, channel, folder) -> str:
    """Chuyển video sang thư mục (ĐÃ UP / VIDEO LỖI / CHƯA UP) của kênh. Trả về đường dẫn mới."""
    src = Path(video_path)
    if not src.exists():
        return str(src)
    dst_dir = channel_dir(root, channel) / folder
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = _unique(dst_dir / src.name)
    shutil.move(str(src), str(dst))
    return str(dst)


def write_error_note(video_path, message):
    try:
        note = Path(video_path).with_suffix(".LOI.txt")
        note.write_text(f"{datetime.now():%d/%m/%Y %H:%M}\n{message}\n", encoding="utf-8")
    except Exception:
        pass
