"""Đóng gói tool thành file .zip để gửi máy khác.
KHÔNG đóng gói: .venv (máy kia tự cài), data/ (chứa đăng nhập TikTok, token FB, API key của bác)."""
import zipfile
from datetime import datetime
from pathlib import Path

base = Path(__file__).resolve().parent
out = base.parent / f"SonixDangVideo_{datetime.now():%Y%m%d}.zip"
SKIP_DIRS = {".venv", "python", "build", "dist", "data", "__pycache__", ".git", "patches", "static"}  # static: ảnh nền riêng của bác
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for p in base.rglob("*"):
        rel = p.relative_to(base)
        if p.is_file() and not (set(rel.parts) & SKIP_DIRS) and p.suffix not in (".pyc", ".zip"):
            z.write(p, Path("SonixDangVideo") / rel)
print(f"Đã đóng gói: {out}")
print("Gửi file zip này cho máy khác -> giải nén -> chạy 1_CAI_DAT.bat")
