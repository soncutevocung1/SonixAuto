"""Tạo manifest.json (phiên bản + mã SHA-256 từng file) để app tự cập nhật. Chạy trước mỗi lần đưa bản mới lên GitHub."""
import json
from datetime import datetime, timezone
from pathlib import Path

from core.updater import SKIP_DIRS, SKIP_FILES, digest

base = Path(__file__).resolve().parent
version = (base / "VERSION").read_text(encoding="utf-8").strip()
log = (base / "GHI_CHU_PHIEN_BAN.md").read_text(encoding="utf-8")
notes = log.split("\n## ")[1].split("\n", 1)[1].strip() if "\n## " in log else ""
files = []
for p in sorted(base.rglob("*")):
    rel = p.relative_to(base).as_posix()
    if (p.is_file() and not set(p.relative_to(base).parts) & SKIP_DIRS and p.name not in SKIP_FILES
            and p.suffix not in (".zip", ".pyc") and not p.name.endswith(".moi")):
        files.append({"path": rel, "sha256": digest(p.read_bytes()), "size": p.stat().st_size})
man = {"version": version, "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "notes": notes,
       "files": files}
(base / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"manifest.json: phiên bản {version}, {len(files)} file")
