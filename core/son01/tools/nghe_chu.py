"""Nghe video ra chu, co moc thoi gian TUNG CHU (faster-whisper).
python nghe_chu.py <video> <out.json> [model=large-v3]
"""
import sys, json, os, subprocess, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from faster_whisper import WhisperModel

src, out = sys.argv[1], sys.argv[2]
model_name = sys.argv[3] if len(sys.argv) > 3 else "large-v3"
t0 = time.time()
wav = os.path.join(tempfile.gettempdir(), "sonix_nghe.wav")
subprocess.run([os.environ.get("SONIX_FFMPEG") or __import__("imageio_ffmpeg").get_ffmpeg_exe(), "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
print("tach am thanh xong", round(time.time() - t0, 1), "s", flush=True)

m = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=max(4, (os.cpu_count() or 8) - 2))
# Tu doc WAV (tranh loi PyAV khong khop phien ban)
import soundfile as sf, numpy as np
audio, sr = sf.read(wav, dtype="float32")
if audio.ndim > 1:
    audio = audio.mean(axis=1)
segs, info = m.transcribe(
    audio, language="vi", word_timestamps=True, vad_filter=True,
    vad_parameters={"min_silence_duration_ms": 300, "speech_pad_ms": 120},
    no_speech_threshold=0.5, log_prob_threshold=-1.0, compression_ratio_threshold=2.4,
    temperature=[0.0, 0.4], beam_size=3, condition_on_previous_text=False,
    # KHONG dung initial_prompt: large-v3 bia cau "subscribe..." khi co cau moi
)
# Bang sua tu chuyen nganh (Whisper hay nghe nham)
import re
SUA = [(r"\bnộm cá\b", "đạm cá"), (r"\bdạm cá\b", "đạm cá"), (r"\bđậm cá\b", "đạm cá"),
       (r"\ba mi nô\b", "amino"), (r"\bami nô\b", "amino"), (r"\bkích rể\b", "kích rễ"),
       (r"\bti xê không một\b", "TC01"), (r"\btê xê 01\b", "TC01"), (r"\bat[ôo]nic\b", "atonik")]
def sua(t):
    for a, b in SUA:
        t = re.sub(a, b, t, flags=re.I)
    return t
res = {"file": src, "duration": info.duration, "segments": []}
BIA = ("subscribe", "ghiền mì gõ", "đăng ký kênh", "like và share", "cảm ơn các bạn đã theo dõi", "hẹn gặp lại", "video hấp dẫn")
for s in segs:
    if any(b in s.text.lower() for b in BIA) or s.no_speech_prob > 0.6:
        print(f"[bo cau bia {s.start:.1f}-{s.end:.1f}] {s.text.strip()}", flush=True)
        continue
    words = [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3), "p": round(w.probability, 3)} for w in (s.words or [])]
    # sua tu theo cap chu lien nhau (vd "nộm"+"cá")
    for i in range(len(words) - 1):
        ghep = sua(words[i]["w"] + " " + words[i + 1]["w"])
        if ghep != words[i]["w"] + " " + words[i + 1]["w"] and len(ghep.split()) == 2:
            words[i]["w"], words[i + 1]["w"] = ghep.split()
    txt = sua(s.text.strip())
    res["segments"].append({"s": round(s.start, 3), "e": round(s.end, 3), "text": txt, "words": words})
    print(f"[{s.start:7.2f}-{s.end:7.2f}] {txt}", flush=True)
json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("XONG", out, round(time.time() - t0, 1), "s", flush=True)
