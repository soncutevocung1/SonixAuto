"""Tiện ích caption: hashtag, từ dễ bị bóp, bộ câu mẫu khi không dùng AI."""
import random
import re
import unicodedata

# Từ dễ bị TikTok/Facebook bóp tương tác hoặc vi phạm quảng cáo phân bón/thuốc BVTV
RISKY_WORDS = [
    "tốt nhất", "số 1", "số một", "100%", "cam kết", "thần kỳ", "thần dược", "chữa khỏi",
    "khỏi hẳn", "vĩnh viễn", "rẻ nhất", "duy nhất", "bao hiệu quả", "đảm bảo hiệu quả",
    "gấp đôi năng suất", "tăng gấp", "trị dứt điểm", "diệt sạch",
]


def check_policy(text: str) -> list:
    low = (text or "").lower()
    return [w for w in RISKY_WORDS if w in low]


def clean_tag(tag: str) -> str:
    t = unicodedata.normalize("NFD", tag.strip().lstrip("#")).replace("đ", "d").replace("Đ", "D")
    t = t.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9_]", "", t).lower()


def caption_tags(text: str) -> list:
    """Các hashtag đã có sẵn trong caption (đã chuẩn hoá như ô Hashtag)."""
    return [t for t in (clean_tag(m) for m in re.findall(r"#([^\s#]+)", text or "")) if t]


def split_tail_tags(text: str):
    """Tách cụm hashtag ở CUỐI caption ra: ('caption còn lại', [tag...]). Hashtag giữa câu thì để nguyên."""
    text = (text or "").strip()
    m = re.search(r"(?:\s*#[^\s#]+)+$", text)
    if not m:
        return text, []
    return text[:m.start()].rstrip(), caption_tags(m.group(0))


def parse_tags(text: str) -> list:
    out = []
    for raw in re.split(r"[,\s]+", text or ""):
        t = clean_tag(raw)
        if t and t not in out:
            out.append(t)
    return out


# ------------------- Bộ mẫu dự phòng (không cần AI) -------------------
HOOKS = {
    "Cà phê": ["Cà phê vàng lá, rụng trái non là bác coi kỹ video này nha 👇",
               "Sau thu hoạch mà bỏ quên bước này là năm sau cà phê đuối liền bác ơi",
               "Rễ cà phê yếu thì bón bao nhiêu phân cũng phí bác à"],
    "Sầu riêng": ["Sầu riêng suy, lá vàng, rễ thối là bác đừng bón phân vội nha 👇",
                  "Mùa này sầu riêng dễ sượng múi, bác lưu ý giúp em chỗ này",
                  "Nuôi trái sầu riêng mà thiếu cái này là rụng trái non liền"],
    "Tiêu": ["Tiêu vàng lá chết nhanh, 80% là do rễ bác ơi 👇",
             "Trụ tiêu xanh tốt hay không là nhờ bộ rễ đó bác",
             "Bác trồng tiêu coi kỹ cách cứu rễ này nha"],
    "Rau màu": ["Rau lên chậm, lá vàng là thiếu cái này nè bác 👇",
                "Mẹo cho rau xanh mướt mà không cần bón nhiều phân hóa học",
                "Bác trồng rau ráng xem hết video này nha"],
    "Khác": ["Bác nào đang lo cây suy, vàng lá thì coi video này nha 👇",
             "Mẹo nhỏ mà nhiều bà con làm vườn chưa biết",
             "Cây yếu là do rễ, bác xem em xử lý vầy nè"],
}
CTA_TT = ["Bác cần thì bấm giỏ hàng vàng góc trái nha, em để sẵn rồi 🛒",
          "Sản phẩm em để ở giỏ hàng vàng nha bác 🛒"]
CTA_FB = ["Link sản phẩm em để ngay bên dưới nha bác 👇",
          "Bác cần tư vấn thêm thì nhắn tin cho em nha."]
CTA_INFO = ["Bác thấy hay thì lưu lại, chia sẻ cho bà con cùng làm nha.",
            "Bác có câu hỏi gì cứ để lại bình luận, em trả lời liền."]
CROP_TAGS = {"Cà phê": ["caphe", "phanbonchocaphe"], "Sầu riêng": ["saurieng", "chamsocsaurieng"],
             "Tiêu": ["hotieu", "trongtieu"], "Rau màu": ["raumau", "trongrau"], "Khác": ["lamvuon"]}


def _template_caption(video_path, crop, product, notes, must_tags):
    crop = crop if crop in HOOKS else "Khác"
    hook = random.choice(HOOKS[crop])
    body = []
    if notes:
        body.append(notes.strip())
    if product:
        body.append(f"Em đang dùng {product['name']}: {product.get('note', '')}".strip(": "))
    tt = "\n".join([hook] + body + [random.choice(CTA_TT if product else CTA_INFO)])
    fb = "\n".join([hook] + body + [random.choice(CTA_FB if product else CTA_INFO)])
    tags = []
    for t in list(must_tags) + CROP_TAGS[crop] + (["kichre"] if product and "rễ" in product["name"].lower() else []):
        ct = clean_tag(t)
        if ct and ct not in tags:
            tags.append(ct)
    if product:
        pt = clean_tag(product["name"])
        if pt and pt not in tags:
            tags.append(pt)
    return {"tiktok": tt, "facebook": fb, "hashtags": tags[:7], "source": "Mẫu"}


def template_caption(crop, product, notes, must_tags):
    return _template_caption("", crop, product, notes, must_tags)


def build_text(caption: str, hashtags: str, product_link: str = "", platform: str = "tiktok") -> str:
    """Ghép caption + link (FB) + hashtag thành bài đăng hoàn chỉnh."""
    parts = [caption.strip()]
    if platform == "facebook" and product_link:
        parts.append(f"👉 Link sản phẩm: {product_link.strip()}")
    tags = " ".join("#" + t for t in parse_tags(hashtags))
    if tags:
        parts.append(tags)
    return "\n\n".join(p for p in parts if p)
