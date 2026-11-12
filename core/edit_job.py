"""Việc chạy lâu của tab Edit video (chạy ngầm, ghi nhật ký ra file để giao diện đọc).

python -m core.edit_job quet_canh <sp_key>
python -m core.edit_job quet_kenh <ten_kenh> <file_link.txt>
"""
import os
import sys
import time
import traceback
from pathlib import Path

from core.config import DATA_DIR

JOB_DIR = DATA_DIR / "edit" / "viec"


def log_file(name: str) -> Path:
    return JOB_DIR / f"{name}.log"


def pid_file(name: str) -> Path:
    return JOB_DIR / f"{name}.pid"


def dang_chay(name: str) -> bool:
    p = pid_file(name)
    if not p.exists():
        return False
    try:
        pid = int(p.read_text())
    except ValueError:
        return False
    if sys.platform == "win32":
        import subprocess
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True,
                             creationflags=0x08000000).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def chay_ngam(name: str, *args, env=None, flags=0):
    import subprocess
    JOB_DIR.mkdir(parents=True, exist_ok=True)
    log_file(name).write_text("", encoding="utf-8")
    base = Path(__file__).resolve().parent.parent
    p = subprocess.Popen([sys.executable, "-m", "core.edit_job", *args], cwd=str(base), env=env,
                         creationflags=flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pid_file(name).write_text(str(p.pid))


def doc_log(name: str, n: int = 12) -> list:
    f = log_file(name)
    if not f.exists():
        return []
    return f.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]


def main(argv):
    kind = argv[0]
    name = kind + "_" + argv[1] if len(argv) > 1 else kind
    JOB_DIR.mkdir(parents=True, exist_ok=True)
    fh = open(log_file(name), "a", encoding="utf-8")

    def log(m):
        fh.write(time.strftime("%H:%M:%S ") + str(m) + "\n")
        fh.flush()

    try:
        from core.config import load_settings
        S = load_settings()
        if kind == "quet_canh":
            from core import canh, edit_video
            sp = argv[1]
            files = edit_video.thu_muc_clip(sp, edit_video.input_root(S))
            log(f"Quét {len(files)} video (đã quét rồi thì bỏ qua)...")
            canh.quet(sp, files, log=log)
            canh.gan_nhan_ai(sp, S, log=log)
        elif kind == "quet_kenh":
            from core import tham_khao
            ten, f = argv[1], argv[2]
            links = [ln.strip() for ln in Path(f).read_text(encoding="utf-8").splitlines() if ln.strip()]
            tham_khao.quet_kenh(links, DATA_DIR / "edit" / "tham_khao" / ten, n=len(links), log=log)
        else:
            raise ValueError(f"Không biết việc {kind}")
        log("XONG")
    except Exception as e:
        log(f"LỖI: {e}")
        fh.write(traceback.format_exc())
    finally:
        fh.close()
        try:
            pid_file(name).unlink()
        except OSError:
            pass


if __name__ == "__main__":
    main(sys.argv[1:])
