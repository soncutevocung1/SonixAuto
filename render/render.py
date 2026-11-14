"""Bộ máy dựng Sonix: chụp từng khung HTML bằng Playwright (Python) -> FFmpeg.

Dùng Chromium mà app đã cài sẵn (python -m playwright install chromium), không cần Node.js.
  python render/render.py --comp render/comps/subtitle.html --props p.json --out ra.mov --alpha
Tuỳ chọn:
  --w 1080 --h 1920 --fps 30 --frames N (mặc định lấy từ comp: SX_META.duration)
  --alpha      MOV ProRes 4444 nền trong suốt (thả thẳng lên CapCut) | mặc định MP4 H.264
  --workers 4  số trang Chrome chạy song song
  --audio f    ghép âm thanh vào MP4 xem thử
  --still 45   chỉ chụp 1 khung ra PNG
  --quiet
Composition (HTML) nạp ../engine/lib/runtime.js và khai báo window.renderFrame(frame) (+ tuỳ chọn window.setup,
window.SX_META). Chuyển động dùng SX.spring (lò xo vật lý, tích phân bước 1 ms -> giống nhau trên mọi máy).
"""
import asyncio
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def ffmpeg_exe() -> str:
    if os.environ.get("SONIX_FFMPEG"):
        return os.environ["SONIX_FFMPEG"]
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def tim_chrome() -> list:
    """Các file Chrome có thể dùng, ưu tiên bản Playwright đã tải (mới nhất trước), rồi Chrome/Edge của máy.
    Cần khi gói playwright và trình duyệt đã tải lệch phiên bản (vd chỉ có chromium-1254 mà playwright đòi 1248)."""
    import glob
    roots = [os.environ.get("PLAYWRIGHT_BROWSERS_PATH", ""), os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright"),
             os.path.expanduser("~/.cache/ms-playwright"), os.path.expanduser("~/Library/Caches/ms-playwright"),
             "/opt/pw-browsers"]
    names = ["chrome-headless-shell.exe", "chrome.exe", "chrome-headless-shell", "chrome", "Chromium"]
    out = []
    for r in [x for x in roots if x and os.path.isdir(x)]:
        for d in sorted(glob.glob(os.path.join(r, "chromium*")), key=lambda p: p.rsplit("-", 1)[-1], reverse=True):
            for n in names:
                out += [f for f in glob.glob(os.path.join(d, "*", n)) + glob.glob(os.path.join(d, "*", "*", "*", "*", n))
                        if os.path.isfile(f)]
    out += [p for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe") if os.path.isfile(p)]
    return out


async def _launch(p):
    args = ["--disable-gpu-vsync", "--force-color-profile=srgb", "--hide-scrollbars", "--allow-file-access-from-files"]
    exe = os.environ.get("SONIX_CHROME")
    if exe:
        return await p.chromium.launch(executable_path=exe, args=args)
    try:
        return await p.chromium.launch(args=args)
    except Exception as e:
        loi = e
    for exe in tim_chrome():
        try:
            return await p.chromium.launch(executable_path=exe, args=args)
        except Exception:
            continue
    raise RuntimeError(f"Không mở được Chrome để dựng hình: {loi}")


def _args(argv):
    o, i = {}, 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--"):
            k = a[2:]
            if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                o[k] = argv[i + 1]
                i += 1
            else:
                o[k] = True
        i += 1
    return o


def prepare_media(props: dict, props_dir: Path, fps: int, ff: str, tmp_dirs: list):
    """Tách trước mỗi video trong props.media thành chuỗi ảnh JPG (Chromium không giải mã H.264; ảnh từng khung
    cho kết quả chính xác tuyệt đối). props.media = { ten: { path, start=0, rate=1, dur, scale="720:-2" } }"""
    for name, m in (props.get("media") or {}).items():
        src = (props_dir / m["path"]).resolve() if not os.path.isabs(m["path"]) else Path(m["path"])
        if src.suffix.lower() not in (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"):
            m["url"] = src.as_uri()
            continue
        d = Path(tempfile.mkdtemp(prefix=f"sxm-{name}-"))
        tmp_dirs.append(d)
        rate, start, dur = float(m.get("rate") or 1), float(m.get("start") or 0), float(m.get("dur") or 10)
        vf = f"setpts=PTS/{rate},fps={fps},scale={m.get('scale') or '720:-2'}"
        r = subprocess.run([ff, "-v", "error", "-y", "-ss", f"{start}", "-t", f"{dur * rate + 0.2}", "-i", str(src),
                            "-an", "-vf", vf, "-q:v", "3", str(d / "f_%05d.jpg")], capture_output=True,
                           creationflags=_NO_WINDOW)
        if r.returncode != 0:
            raise RuntimeError(f"Tách khung lỗi {src}: {r.stderr.decode('utf-8', 'ignore')[-400:]}")
        m["frames"] = {"base": d.as_uri() + "/f_", "count": len(list(d.glob("*.jpg")))}


def _encoder(ff, out, fps, alpha):
    common = [ff, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "png", "-i", "-"]
    enc = (["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-vendor", "apl0"] if alpha else
           ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart"])
    return subprocess.Popen(common + enc + [str(out)], stdin=subprocess.PIPE, creationflags=_NO_WINDOW)


async def _open_page(browser, url, props, fps, w, h, log_err):
    ctx = await browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
    page = await ctx.new_page()
    page.on("pageerror", lambda e: log_err(f"[lỗi trang] {e}"))
    page.on("console", lambda m: log_err(f"[console] {m.text}") if m.type == "error" else None)
    init = ("window.__SX_PROPS__ = %s; window.__SX_FPS__ = %d; window.__SX_W__ = %d; window.__SX_H__ = %d;"
            % (json.dumps(props, ensure_ascii=False), fps, w, h))
    await page.add_init_script(init)
    await page.goto(url, wait_until="load")
    await page.evaluate("""async () => {
        if (window.SX) { window.SX.fps = window.__SX_FPS__; window.SX.props = window.__SX_PROPS__; }
        if (document.fonts) await document.fonts.ready;
        if (window.setup) await window.setup();
        const vids = [...document.querySelectorAll('video[data-sx-video]')];
        await Promise.all(vids.map((v) => v.readyState >= 1 ? 0 :
            new Promise((r) => v.addEventListener('loadedmetadata', r, { once: true }))));
    }""")
    cdp = await ctx.new_cdp_session(page)
    # Chrome mặc định tô nền trắng -> tắt đi để khung hình trong suốt thật sự
    await cdp.send("Emulation.setDefaultBackgroundColorOverride", {"color": {"r": 0, "g": 0, "b": 0, "a": 0}})
    return page, cdp


async def _grab(pg, f):
    page, cdp = pg
    await page.evaluate("(fr) => window.renderFrame(fr)", f)
    r = await cdp.send("Page.captureScreenshot", {"format": "png", "optimizeForSpeed": True,
                                                  "captureBeyondViewport": False, "fromSurface": True})
    return base64.b64decode(r["data"])


async def render(comp, out, props=None, props_dir=None, w=1080, h=1920, fps=30, frames=None, alpha=False,
                 workers=None, audio=None, still=None, quiet=False, log=print):
    from playwright.async_api import async_playwright
    t0 = time.time()
    ff = ffmpeg_exe()
    props = json.loads(json.dumps(props or {}))
    tmp_dirs = []
    errs = []

    def log_err(m):
        if len(errs) < 20:
            errs.append(m)
            print(m, file=sys.stderr)

    prepare_media(props, Path(props_dir or os.getcwd()), fps, ff, tmp_dirs)
    url = Path(comp).resolve().as_uri()
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        async with async_playwright() as p:
            browser = await _launch(p)
            try:
                first = await _open_page(browser, url, props, fps, w, h, log_err)
                meta = await first[0].evaluate("() => window.SX_META || {}")
                total = int(frames or meta.get("durationInFrames") or round(float(meta.get("duration") or 3) * fps))
                if still is not None:
                    out.write_bytes(await _grab(first, int(still)))
                    if not quiet:
                        log(f"Đã chụp khung {still} -> {out}")
                    return str(out)
                n = max(1, min(int(workers or min(4, os.cpu_count() or 2)), -(-total // 15)))
                per = -(-total // n)
                tmp = Path(tempfile.mkdtemp(prefix="sonix-"))
                tmp_dirs.append(tmp)
                ext = ".mov" if alpha else ".mp4"
                if not quiet:
                    log(f"Dựng {total} khung ({total / fps:.2f}s) {w}x{h}@{fps} - {n} luồng - "
                        f"{'MOV trong suốt' if alpha else 'MP4'}")
                pages = [first] + [await _open_page(browser, url, props, fps, w, h, log_err) for _ in range(n - 1)]
                done = [0]

                async def chay(wi, pg):
                    a, b = wi * per, min(total, (wi + 1) * per)
                    if a >= b:
                        return None
                    seg = tmp / f"seg{wi}{ext}"
                    enc = _encoder(ff, seg, fps, alpha)
                    loop = asyncio.get_running_loop()
                    for f in range(a, b):
                        png = await _grab(pg, f)
                        await loop.run_in_executor(None, enc.stdin.write, png)
                        done[0] += 1
                        if not quiet and done[0] % 90 == 0:
                            log(f"  {done[0]}/{total} khung")
                    enc.stdin.close()
                    if await loop.run_in_executor(None, enc.wait) != 0:
                        raise RuntimeError("ffmpeg mã hoá lỗi")
                    return seg

                segs = [s for s in await asyncio.gather(*(chay(i, pg) for i, pg in enumerate(pages))) if s]
            finally:
                await browser.close()
        lst = tmp / "list.txt"
        lst.write_text("\n".join(f"file '{s.as_posix()}'" for s in segs), encoding="utf-8")
        cmd = [ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst)]
        if audio:
            cmd += ["-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-shortest"]
        cmd += ["-c:v", "copy", str(out)]
        if subprocess.run(cmd, creationflags=_NO_WINDOW).returncode != 0:
            raise RuntimeError("Ghép đoạn lỗi")
        if not quiet:
            log(f"Xong -> {out} trong {time.time() - t0:.1f}s")
        return str(out)
    finally:
        for d in tmp_dirs:
            shutil.rmtree(d, ignore_errors=True)


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    o = _args(argv)
    if not o.get("comp") or not o.get("out"):
        sys.exit("Thiếu --comp hoặc --out")
    props, pdir = {}, None
    if o.get("props"):
        props = json.loads(Path(o["props"]).read_text(encoding="utf-8"))
        pdir = Path(o["props"]).resolve().parent
    asyncio.run(render(o["comp"], o["out"], props, pdir, int(o.get("w", 1080)), int(o.get("h", 1920)),
                       int(o.get("fps", 30)), o.get("frames") and int(o["frames"]), bool(o.get("alpha")),
                       o.get("workers") and int(o["workers"]), o.get("audio"),
                       o.get("still") if o.get("still") is not None else None, bool(o.get("quiet"))))


if __name__ == "__main__":
    main(sys.argv[1:])
