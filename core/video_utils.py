"""Đọc thông tin video (thời lượng, khung hình) và cắt ảnh để AI 'xem' video."""
import re
import subprocess
import sys


def _ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# Video HDR (iPhone quay mặc định: HEVC 10-bit, HLG/Dolby Vision, màu BT.2020): cắt ảnh mà không chuyển màu thì ảnh
# bị nhạt, bệt. Chuỗi lọc dưới đây chuyển về màu thường (SDR, BT.709) để ảnh bìa/xem thử đúng màu gốc.
TONEMAP = ("zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=mobius:desat=0,"
           "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
_HDR = {}


def is_hdr(path) -> bool:
    key = str(path)
    if key not in _HDR:
        try:
            p = subprocess.run([_ffmpeg(), "-hide_banner", "-i", key], capture_output=True, text=True,
                               encoding="utf-8", errors="ignore", creationflags=_NO_WINDOW)
            v = next((ln for ln in p.stderr.splitlines() if "Video:" in ln), "")
            _HDR[key] = bool(re.search(r"arib-std-b67|smpte2084", v))
        except Exception:
            _HDR[key] = False
    return _HDR[key]


def _vfs(path, base) -> list:
    """Các bộ lọc thử lần lượt: video HDR thì chuyển màu trước; lỗi thì cắt kiểu thường."""
    return [f"{base},{TONEMAP}", base] if is_hdr(path) else [base]


def probe(path: str) -> dict:
    """Trả về {'duration': giây, 'width': .., 'height': ..} (0 nếu không đọc được)."""
    info = {"duration": 0.0, "width": 0, "height": 0}
    try:
        p = subprocess.run([_ffmpeg(), "-hide_banner", "-i", str(path)], capture_output=True,
                           text=True, encoding="utf-8", errors="ignore", creationflags=_NO_WINDOW)
        out = p.stderr
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", out)
        if m:
            info["duration"] = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
        m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", out)
        if m:
            info["width"], info["height"] = int(m[1]), int(m[2])
        if re.search(r"rotate\s*:\s*-?90|rotation of -?90", out) and info["width"] > info["height"]:
            info["width"], info["height"] = info["height"], info["width"]
    except Exception:
        pass
    return info


def extract_frames(path: str, count: int = 3, width: int = 512) -> list:
    """Cắt `count` ảnh JPEG rải đều trong video. Trả về list bytes."""
    dur = probe(path)["duration"] or 10
    frames = []
    for i in range(count):
        t = dur * (i + 1) / (count + 1)
        for vf in _vfs(path, f"scale={width}:-2"):
            try:
                p = subprocess.run(
                    [_ffmpeg(), "-hide_banner", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(path),
                     "-frames:v", "1", "-vf", vf, "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
                    capture_output=True, timeout=60, creationflags=_NO_WINDOW)
                if p.returncode == 0 and p.stdout:
                    frames.append(p.stdout)
                    break
            except Exception:
                pass
    return frames


def has_audio(path: str) -> bool:
    try:
        p = subprocess.run([_ffmpeg(), "-hide_banner", "-i", str(path)], capture_output=True, text=True,
                           encoding="utf-8", errors="ignore", creationflags=_NO_WINDOW)
        return bool(re.search(r"Stream #.*Audio:", p.stderr))
    except Exception:
        return False


def frame_times(path: str, count: int) -> list:
    """Các mốc thời gian rải đều, bỏ 0,5 giây đầu và cuối (hay bị đen/chuyển cảnh)."""
    dur = probe(path)["duration"] or 10
    a, b = min(0.5, dur * 0.1), max(dur - 0.5, dur * 0.9)
    if count == 1:
        return [dur / 2]
    return [round(a + (b - a) * i / (count - 1), 2) for i in range(count)]


def export_frame(path: str, t: float, out: str, width: int = 1080) -> bool:
    """Lưu 1 khung hình thành file JPG (dùng làm ảnh bìa / ảnh xem trước). Video HDR iPhone: chuyển màu chuẩn."""
    for vf in _vfs(path, f"scale='min({width},iw)':-2"):
        try:
            p = subprocess.run(
                [_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.2f}", "-i", str(path),
                 "-frames:v", "1", "-vf", vf, "-q:v", "2", str(out)],
                capture_output=True, timeout=90, creationflags=_NO_WINDOW)
            if p.returncode == 0:
                return True
        except Exception:
            pass
    return False


def make_blank_video(out: str) -> str:
    """Video đen 3 giây, dùng để mở trang đăng khi đồng bộ phòng trưng bày (không đăng thật)."""
    if not __import__("os").path.exists(out):
        subprocess.run([_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
                        "-f", "lavfi", "-i", "color=c=black:s=720x1280:d=3:r=25",
                        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
                        "-pix_fmt", "yuv420p", str(out)], capture_output=True, creationflags=_NO_WINDOW)
    return out


def mix_music(video: str, music: str, out: str, volume: float = 0.15) -> str:
    """Ghép nhạc nền vào video. Video có tiếng thì nhạc nhỏ lại, không lấn giọng nói."""
    ff = _ffmpeg()
    if has_audio(video):
        fc = (f"[1:a]volume={volume}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]")
    else:
        fc = f"[1:a]volume={max(volume * 3, 0.5)}[a]"
    cmd = [ff, "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-stream_loop", "-1", "-i", str(music),
           "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
           "-shortest", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore",
                       creationflags=_NO_WINDOW)
    if p.returncode != 0:
        raise RuntimeError("Ghép nhạc lỗi: " + p.stderr[-300:])
    return out


def strip_audio(video: str, out: str, music: str = "") -> str:
    """Bỏ âm thanh gốc: thay bằng im lặng, hoặc bằng nhạc trên máy (to bình thường) nếu có. Hình giữ nguyên."""
    ff = _ffmpeg()
    if music:
        src = ["-stream_loop", "-1", "-i", str(music)]
    else:
        src = ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    cmd = [ff, "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), *src, "-map", "0:v:0", "-map", "1:a:0",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore",
                       creationflags=_NO_WINDOW)
    if p.returncode != 0:
        raise RuntimeError("Tắt âm thanh gốc lỗi: " + p.stderr[-300:])
    return out


def make_preview(path: str, out: str, height: int = 640, max_sec: int = 120) -> str:
    """Bản xem thử MP4 (H.264) để trình duyệt phát được cả file .MOV của iPhone."""
    import os
    if os.path.exists(out) and os.path.getsize(out) > 0:
        return out
    for vf in _vfs(path, f"fps=30,scale=-2:'min({height},ih)'"):
        cmd = [_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(path), "-t", str(max_sec),
               "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "30",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(out)]
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore",
                           creationflags=_NO_WINDOW)
        if p.returncode == 0:
            break
    if p.returncode != 0:
        raise RuntimeError("Không tạo được bản xem thử: " + p.stderr[-200:])
    return out
