"""Phân tích video: cắt khung hình -> AI nhận diện sản phẩm + chọn ảnh rõ nhất + viết caption.

Không dùng AI: nhận diện theo tên file (ví dụ file tên có chữ "tc01").
"""
import base64
import io
import json
import time
from pathlib import Path

from . import caption as cap
from . import products as prod
from .config import REF_DIR, SHOWCASE_DIR, WORK_DIR, ai_key, norm, slug
from .video_utils import export_frame, frame_times

N_FRAMES = 10

SYSTEM = """Bạn hỗ trợ một kênh TikTok tiếp thị liên kết bán phân bón, thuốc bảo vệ thực vật cho nông dân Tây Nguyên (cà phê, sầu riêng, tiêu, rau màu), 25-45 tuổi.

Nhiệm vụ với mỗi video (bạn được xem các khung hình đánh số):
1. Nhận diện sản phẩm xuất hiện trong video, so với danh sách sản phẩm và ảnh mẫu được cung cấp. Dựa vào chữ trên nhãn, màu chai/can, dung tích, hình dáng. Phân biệt kỹ can 1 lít và can 5 lít.
   - Nếu video không có sản phẩm nào trong danh sách (video chia sẻ kiến thức, cảnh vườn...) thì product_key = "none".
   - confidence 0-100: 90+ khi đọc rõ chữ trên nhãn; 60-89 khi nhận ra qua màu/hình dáng; dưới 60 khi đoán.
2. best_frame: số thứ tự khung hình thấy sản phẩm RÕ NHẤT (nhãn đọc được, không mờ, không bị che). Ưu tiên khung có người cầm sản phẩm trên tay. Nếu không có sản phẩm thì chọn khung đẹp, sáng nhất.
3. evidence: 1 câu ngắn giải thích vì sao (vd "khung 4 đọc được chữ TC 01 trên chai xanh").
4. Viết caption TikTok:
   - Giọng miền Nam, mộc mạc, xưng "em", gọi người xem là "bác". Câu ngắn. Không dùng từ tiếng Anh.
   - Dòng 1: câu móc dưới 80 ký tự, chạm nỗi lo thật (vàng lá, rụng trái, thối rễ, cây suy...) hoặc gây tò mò, có thể 1 emoji.
   - 1-3 dòng thân: lợi ích, cách dùng nếu thấy trong video. Không bịa số liệu, liều lượng.
   - Dòng cuối: kêu gọi hành động. Có sản phẩm thì mời bấm giỏ hàng vàng.
   - Tối đa 300 ký tự, không chứa hashtag.
   - Cấm dùng: tốt nhất, số 1, 100%, cam kết, thần kỳ, chữa khỏi, vĩnh viễn, rẻ nhất, duy nhất, diệt sạch, trị dứt điểm. Không hứa năng suất bằng con số. Thuốc BVTV thì nhắc nhẹ đọc kỹ hướng dẫn hoặc mang đồ bảo hộ.
5. hashtags: 4-6 cái, tiếng Việt không dấu, viết liền, chữ thường, không có dấu #."""


def _system(settings, channel="") -> str:
    """Lời dặn cho AI: quy tắc chung + độ dài tối đa + hướng dẫn riêng của chủ kênh (ưu tiên cao nhất)."""
    mx = int(settings.get("caption_max_chars") or 150)
    s = SYSTEM.replace("Tối đa 300 ký tự", f"Tối đa {mx} ký tự (tính cả dấu cách, xuống dòng)")
    g = (settings.get("caption_guide") or "").strip()
    gc = ((settings.get("caption_guide_by_channel") or {}).get(channel) or "").strip()
    if g or gc:
        s += ("\n\nHƯỚNG DẪN RIÊNG CỦA CHỦ KÊNH VỀ CAPTION (ưu tiên cao nhất; nếu khác quy tắc ở trên thì làm theo "
              "hướng dẫn này, nhưng vẫn giữ danh sách từ cấm):\n" + g
              + (f"\nRiêng kênh {channel}: {gc}" if gc else ""))
    return s


def _trim(text, mx):
    """AI viết quá dài (hơn 1,3 lần giới hạn) thì cắt ở cuối câu/dòng gần giới hạn nhất."""
    if len(text) <= mx * 1.3:
        return text
    cut = text[: int(mx * 1.2)]
    pos = max(cut.rfind("\n"), cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return (cut[: pos + 1] if pos > mx * 0.5 else cut.rstrip() + "…").strip()


def _b64(path):
    return base64.standard_b64encode(Path(path).read_bytes()).decode()


def _img(path) -> dict:
    """Khối ảnh gửi cho AI, ghi đúng định dạng thật của file (ảnh trưng bày TikTok hay là PNG dù đuôi .jpg)."""
    data = Path(path).read_bytes()
    if data.startswith(b"\x89PNG"):
        mt = "image/png"
    elif data.startswith(b"GIF8"):
        mt = "image/gif"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        mt = "image/webp"
    elif data.startswith(b"\xff\xd8"):
        mt = "image/jpeg"
    else:  # định dạng lạ (avif, heic...) -> đổi sang JPEG
        from PIL import Image
        buf = io.BytesIO()
        Image.open(io.BytesIO(data)).convert("RGB").save(buf, "JPEG", quality=88)
        data, mt = buf.getvalue(), "image/jpeg"
    return {"type": "image", "source": {"type": "base64", "media_type": mt,
                                        "data": base64.standard_b64encode(data).decode()}}


def _ref_image(item, channel, settings):
    """Ảnh mẫu: ảnh người dùng tải lên, nếu không có thì ảnh sản phẩm trong phòng trưng bày."""
    own = REF_DIR / f"{item['key']}.jpg"
    if own.exists():
        return own
    ids = prod.mapping(settings, channel).get(item["key"], {}).get("ids", [])
    for i in ids:
        f = SHOWCASE_DIR / slug(channel) / f"{i}.jpg"
        if f.exists():
            return f
    return None


FALLBACK_MODELS = ("claude-opus-5-5", "claude-sonnet-5-5")  # Haiku không có model dự phòng


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


def _gemini_text(obj) -> str:
    """Lấy phần chữ trả lời trong kết quả Interactions API."""
    if isinstance(obj, dict):
        if isinstance(obj.get("output_text"), str):
            return obj["output_text"]
        for k in ("outputs", "output", "content", "parts"):
            if k in obj:
                t = _gemini_text(obj[k])
                if t:
                    return t
        if obj.get("type") in (None, "text") and isinstance(obj.get("text"), str):
            return obj["text"]
        return ""
    if isinstance(obj, list):
        return "".join(t for t in (_gemini_text(x) for x in obj) if t)
    return ""


def _gemini(content, schema, settings, model, system=SYSTEM) -> dict:
    """Gọi Gemini (Google). Gói miễn phí giới hạn lượt/phút, lượt/ngày -> tự chờ khi bị giới hạn theo phút."""
    import requests
    parts = []
    for b in content:
        if b["type"] == "text":
            parts.append({"type": "text", "text": b["text"]})
        else:
            parts.append({"type": "image", "data": b["source"]["data"], "mime_type": b["source"]["media_type"]})
    body = {"model": model, "system_instruction": system, "input": parts, "store": False,
            "response_format": {"type": "text", "mime_type": "application/json",
                                "schema": {k: v for k, v in schema.items() if k != "additionalProperties"}},
            "generation_config": {"thinking_level": "low"}}
    headers = {"x-goog-api-key": ai_key(settings, model), "Content-Type": "application/json",
               "Api-Revision": "2026-05-20"}
    last = ""
    for attempt in range(6):
        r = requests.post(GEMINI_URL, json=body, headers=headers, timeout=180)
        last = f"{r.status_code}: {r.text[:300]}"
        if r.status_code == 400 and "thinking" in r.text.lower() and "generation_config" in body:
            body.pop("generation_config")  # model không nhận mức suy nghĩ -> bỏ đi rồi gửi lại
            continue
        if r.status_code == 429:
            if "perday" in r.text.lower().replace("_", "").replace(" ", ""):
                raise RuntimeError("Gemini đã HẾT LƯỢT MIỄN PHÍ hôm nay (sau 14-15 giờ chiều giờ VN mới có lại)")
            time.sleep(min(60, 20 * (attempt + 1)))  # giới hạn theo phút -> chờ rồi thử lại
            continue
        if r.status_code >= 500:
            time.sleep(10 * (attempt + 1))
            continue
        if r.status_code in (401, 403):
            raise RuntimeError("Gemini API key sai hoặc chưa bật (vào ⚙️ Cài đặt kiểm tra lại key)")
        if r.status_code != 200:
            raise RuntimeError(f"Gemini báo lỗi {last}")
        txt = _gemini_text(r.json()).strip()
        if txt.startswith("```"):
            txt = txt.strip("`").removeprefix("json").strip()
        if not txt:
            raise RuntimeError("Gemini không trả lời (có thể bị chặn nội dung)")
        return json.loads(txt)
    raise RuntimeError(f"Gemini đang quá tải hoặc vượt giới hạn mỗi phút, thử lại sau ({last[:120]})")


def _claude(content, schema, settings, model, system=SYSTEM) -> dict:
    import anthropic
    client = anthropic.Anthropic(api_key=ai_key(settings, model) or None)
    kwargs = dict(model=model, max_tokens=16000, system=system,
                  output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema}},
                  messages=[{"role": "user", "content": content}])
    resp = None
    if model in FALLBACK_MODELS:
        try:
            # fallbacks="default": model chính từ chối thì máy chủ tự chạy lại bằng model dự phòng
            resp = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default",
                                               **kwargs)
        except (TypeError, anthropic.BadRequestError):
            resp = None
    if resp is None:
        resp = client.messages.create(**kwargs)
    if resp.stop_reason == "refusal":
        raise RuntimeError("AI từ chối xử lý video này")
    return json.loads(next(b.text for b in resp.content if b.type == "text"))


def _ai(frames, video_name, channel, settings, model, known_item=None):
    items = settings.get("items", [])
    keys = [it["key"] for it in items] + ["none"]
    content = []
    # Phần cố định (danh sách + ảnh mẫu) đặt trước để dùng bộ nhớ đệm, giảm tiền cho các video sau
    lines = ["Danh sách sản phẩm cần nhận diện:"]
    for it in items:
        lines.append(f"- key={it['key']}: {it['name']}. Đặc điểm: {it.get('hints', '')}")
    content.append({"type": "text", "text": "\n".join(lines)})
    for it in items:
        ref = _ref_image(it, channel, settings)
        if ref:
            try:
                blk = _img(ref)
            except Exception:
                continue  # ảnh mẫu hỏng thì bỏ qua, không làm hỏng cả lần phân tích
            content.append({"type": "text", "text": f"Ảnh mẫu của key={it['key']} ({it['name']}):"})
            content.append(blk)
    content[-1]["cache_control"] = {"type": "ephemeral"}

    content.append({"type": "text", "text": f"VIDEO CẦN XỬ LÝ: {video_name}. Các khung hình:"})
    if known_item is not None:  # chỉ viết lại caption: sản phẩm chủ kênh đã xác nhận
        it = next((x for x in items if x["key"] == known_item), None)
        content.append({"type": "text", "text": (
            f"Chủ kênh ĐÃ XÁC NHẬN sản phẩm trong video là {it['name']} → product_key = {known_item}, "
            f"caption phải nói đúng về sản phẩm này." if it else
            "Chủ kênh đã xác nhận video này KHÔNG gắn sản phẩm (video kiến thức) → product_key = none.")})
    for i, f in enumerate(frames):
        content.append({"type": "text", "text": f"Khung {i}:"})
        content.append(_img(f["thumb"]))
    tags = cap.parse_tags(settings.get("default_hashtags", ""))
    content.append({"type": "text", "text": "Hashtag bắt buộc phải có: " + ", ".join(tags) if tags else
                    "Trả lời theo đúng định dạng."})

    schema = {
        "type": "object",
        "properties": {
            "product_key": {"type": "string", "enum": keys},
            "confidence": {"type": "integer"},
            "best_frame": {"type": "integer"},
            "evidence": {"type": "string"},
            "tiktok_caption": {"type": "string"},
            "hashtags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["product_key", "confidence", "best_frame", "evidence", "tiktok_caption", "hashtags"],
        "additionalProperties": False,
    }
    if str(model).startswith("gemini"):
        data = _gemini(content, schema, settings, model, _system(settings, channel))
    else:
        data = _claude(content, schema, settings, model, _system(settings, channel))
    key = data["product_key"] if data["product_key"] != "none" else ""
    text, tail = cap.split_tail_tags(data["tiktok_caption"])  # AI lỡ viết hashtag cuối caption -> dời sang ô Hashtag
    data["tiktok_caption"] = text
    hashtags = []
    for t in tags + tail + data.get("hashtags", []):
        t = cap.clean_tag(t)
        if t and t not in hashtags:
            hashtags.append(t)
    return {"item_key": key, "confidence": max(0, min(100, int(data["confidence"]))),
            "best": max(0, min(len(frames) - 1, int(data["best_frame"]))),
            "note": "AI: " + data.get("evidence", ""), "caption": _trim(data["tiktok_caption"].strip(), int(settings.get("caption_max_chars") or 150)),
            "hashtags": hashtags[:8]}


def _by_filename(video_path, settings):
    name = norm(Path(video_path).stem)
    compact = name.replace(" ", "")
    best, best_hits = "", []
    for it in settings.get("items", []):
        hits = [k for k in (norm(x) for x in (it.get("keywords") or "").split(","))
                if len(k) >= 2 and (k in name or k.replace(" ", "") in compact)]
        if len(hits) > len(best_hits):  # khớp nhiều từ khoá nhất (vd "đạm cá" + "5 lít")
            best, best_hits = it["key"], hits
    if best:
        return best, f"Theo tên file (có chữ «{', '.join(best_hits)}»)"
    return "", "Không dùng AI, tên file không có từ khoá sản phẩm"


def analyze(job_id, video_path, channel, settings, model, caption_only=False, known_item="") -> dict:
    """Trả về dict để cập nhật vào job. caption_only: chỉ viết lại caption cho sản phẩm đã xác nhận."""
    work = WORK_DIR / str(job_id)
    work.mkdir(parents=True, exist_ok=True)
    frames = []
    for i, t in enumerate(frame_times(video_path, N_FRAMES)):
        out = work / f"f{i}.jpg"
        if export_frame(video_path, t, str(out), width=448):
            frames.append({"t": t, "thumb": str(out)})
    if not frames:
        raise RuntimeError("Không đọc được video (file hỏng hoặc định dạng lạ)")

    error = ""
    res = None
    if model and model != "khong_ai" and ai_key(settings, model):
        try:
            res = _ai(frames, Path(video_path).name, channel, settings, model,
                      known_item=(known_item or "") if caption_only else None)
        except Exception as e:
            error = f"AI lỗi ({type(e).__name__}: {str(e)[:120]}) → dùng cách dự phòng. "
    if res is None:
        key, why = _by_filename(video_path, settings)
        item = next((it for it in settings["items"] if it["key"] == key), None)
        tags = cap.parse_tags(settings.get("default_hashtags", ""))
        tpl = cap.template_caption("Khác", {"name": item["name"], "note": ""} if item else None, "", tags)
        res = {"item_key": key, "confidence": 40 if key else 30, "best": len(frames) // 2,
               "note": error + why, "caption": tpl["tiktok"], "hashtags": tpl["hashtags"]}

    if caption_only:
        warn = cap.check_policy(res["caption"])
        return {"caption": res["caption"], "hashtags": ", ".join(res["hashtags"]),
                "ai_note": "✍️ Đã viết lại caption. " + res["note"]
                + (f" | ⚠️ Có từ dễ bị bóp: {', '.join(warn)}" if warn else "")}
    cover = work / "cover.jpg"
    export_frame(video_path, frames[res["best"]]["t"], str(cover), width=1080)
    products, cart = prod.resolve(settings, channel, res["item_key"])
    warn = cap.check_policy(res["caption"])
    note = res["note"] + (f" | ⚠️ Có từ dễ bị bóp: {', '.join(warn)}" if warn else "")
    return {"item_key": res["item_key"], "confidence": res["confidence"], "ai_note": note,
            "caption": res["caption"], "hashtags": ", ".join(res["hashtags"]), "frames": frames,
            "cover_path": str(cover), "products": products, "cart_name": cart}


def set_cover(job, frame_index) -> str:
    """Người dùng chọn khung khác làm ảnh bìa."""
    f = job["frames"][frame_index]
    cover = WORK_DIR / str(job["id"]) / "cover.jpg"
    export_frame(job["video_path"], f["t"], str(cover), width=1080)
    return str(cover)


# ======================= Facebook: video chia sẻ kiến thức (chưa gắn sản phẩm) =======================
FB_SYSTEM = """Bạn viết caption cho Reels của trang Facebook «{page}», trang chia sẻ mẹo và kiến thức làm vườn, trồng trọt cho bà con nông dân Việt Nam. Mục tiêu: người xem dừng lại xem hết, bình luận, và bấm theo dõi trang.

Bạn được xem các khung hình đánh số của 1 video. Trong video có phụ đề tiếng Việt: đọc kỹ phụ đề để hiểu đúng mẹo/kiến thức.

Viết:
1. caption:
   - Giọng miền Nam, gần gũi, xưng "em", gọi người xem là "bác". Câu ngắn, dễ hiểu. Không dùng từ tiếng Anh.
   - Dòng 1: câu móc dưới 80 ký tự, gây tò mò hoặc chạm đúng cái sai bà con hay mắc (vd "Tỉa ngọn ớt sai lúc này là mất cả lứa trái"), có thể 1 emoji.
   - 1-3 dòng thân: mẹo chính trong video, đúng những gì thấy/đọc được. Không bịa số liệu, liều lượng, giống cây.
   - Dòng cuối: mời bình luận hoặc theo dõi trang (vd "Bác thấy mẹo này được không? Theo dõi trang để xem mẹo mỗi ngày nha").
   - Tối đa {mx} ký tự, không chứa hashtag.
   - Cấm dùng: tốt nhất, số 1, 100%, cam kết, thần kỳ, chữa khỏi, vĩnh viễn, rẻ nhất, duy nhất, diệt sạch, trị dứt điểm. Không hứa năng suất bằng con số.
2. title: tên ngắn của video 3-8 chữ (vd "Mẹo tỉa ngọn ớt"), để chủ trang dễ nhận ra.
3. best_frame: số thứ tự khung hình đẹp, rõ nội dung nhất.
4. hashtags: 3-5 cái, tiếng Việt không dấu, viết liền, chữ thường, không có dấu #."""


def _fb_system(settings, page) -> str:
    pg = next((p for p in settings.get("facebook_pages", []) if p.get("name") == page), {}) or {}
    mx = int(pg.get("caption_max") or settings.get("fb_caption_max_chars") or 350)
    s = FB_SYSTEM.replace("{page}", page).replace("{mx}", str(mx))
    if mx <= 160:  # caption ngắn: bỏ khuôn 3 phần, chỉ 1-2 câu
        a = s.index("   - Dòng 1:")
        b = s.index("   - Tối đa")
        s = s[:a] + ("   - CHỈ 1-2 câu ngắn trên 1 dòng: nói mẹo chính hoặc đặt câu hỏi gây tò mò mà lời giải nằm "
                     "trong video. Không thêm câu mời theo dõi, không giải thích dài. Có thể 1 emoji.\n") + s[b:]
        s = s.replace(f"Tối đa {mx} ký tự", f"TUYỆT ĐỐI không quá {mx} ký tự")
    g = (pg.get("caption_guide") or "").strip()
    if g:
        s += ("\n\nHƯỚNG DẪN RIÊNG CỦA CHỦ TRANG (ưu tiên cao nhất, nhưng vẫn giữ danh sách từ cấm):\n" + g)
    return s, mx


def _trim_fb(text, mx):
    """Facebook: vượt giới hạn quá 10% thì cắt ở cuối câu gần nhất (không thì cắt chữ + '…')."""
    if len(text) <= mx * 1.1:
        return text
    cut = text[:mx]
    pos = max(cut.rfind("\n"), cut.rfind(". "), cut.rfind("! "), cut.rfind("? "), cut.rfind("?"))
    return (cut[: pos + 1] if pos > mx * 0.4 else cut.rstrip(" ,.") + "…").strip()


def analyze_fb(job_id, video_path, page, settings, model) -> dict:
    """Video Facebook: AI xem khung hình + phụ đề -> caption, tên ngắn, khung bìa, hashtag."""
    work = WORK_DIR / str(job_id)
    work.mkdir(parents=True, exist_ok=True)
    frames = []
    for i, t in enumerate(frame_times(video_path, 8)):
        out = work / f"f{i}.jpg"
        if export_frame(video_path, t, str(out), width=448):
            frames.append({"t": t, "thumb": str(out)})
    if not frames:
        raise RuntimeError("Không đọc được video (file hỏng hoặc định dạng lạ)")
    pg = next((p for p in settings.get("facebook_pages", []) if p.get("name") == page), {}) or {}
    fixed = cap.parse_tags(pg.get("hashtags") or "")
    system, mx = _fb_system(settings, page)
    res, note = None, ""
    if model and model != "khong_ai" and ai_key(settings, model):
        content = [{"type": "text", "text": f"VIDEO: {Path(video_path).name}. Các khung hình:"}]
        for i, f in enumerate(frames):
            content.append({"type": "text", "text": f"Khung {i}:"})
            content.append(_img(f["thumb"]))
        content.append({"type": "text", "text": "Hashtag bắt buộc phải có: " + ", ".join(fixed) if fixed
                        else "Trả lời theo đúng định dạng."})
        schema = {"type": "object", "properties": {
            "caption": {"type": "string"}, "title": {"type": "string"}, "best_frame": {"type": "integer"},
            "hashtags": {"type": "array", "items": {"type": "string"}}},
            "required": ["caption", "title", "best_frame", "hashtags"], "additionalProperties": False}
        try:
            data = (_gemini if str(model).startswith("gemini") else _claude)(content, schema, settings, model, system)
            text, tail = cap.split_tail_tags(data["caption"])
            tags = []
            for t in fixed + tail + data.get("hashtags", []):
                t = cap.clean_tag(t)
                if t and t not in tags:
                    tags.append(t)
            res = {"caption": _trim_fb(text.strip(), mx), "hashtags": tags[:6],
                   "best": max(0, min(len(frames) - 1, int(data["best_frame"]))),
                   "note": "AI: " + (data.get("title") or "").strip()}
        except Exception as e:
            note = f"AI lỗi ({type(e).__name__}: {str(e)[:120]}) → dùng caption mẫu. "
    if res is None:
        name = pg.get("name") or page
        res = {"caption": f"Mẹo làm vườn hay, bác xem tới cuối nha 🌱\nTheo dõi {name} để xem mẹo mỗi ngày.",
               "hashtags": fixed or ["lamvuon", "meolamvuon", "nongnghiep"], "best": len(frames) // 2,
               "note": note + "Caption mẫu"}
    cover = work / "cover.jpg"
    export_frame(video_path, frames[res["best"]]["t"], str(cover), width=720)
    warn = cap.check_policy(res["caption"])
    return {"caption": res["caption"], "hashtags": ", ".join(res["hashtags"]), "frames": frames,
            "cover_path": str(cover), "confidence": 0,
            "ai_note": res["note"] + (f" | Có từ dễ bị bóp: {', '.join(warn)}" if warn else "")}
