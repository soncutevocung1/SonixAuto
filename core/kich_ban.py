"""AI viết kịch bản lồng tiếng cho Sonix Edit Video.

Đầu vào: thông tin sản phẩm + vài kịch bản tham khảo (chép từ kênh TikTok cùng kiểu, khác ngành).
AI học nhịp, cách giật tít, cách kể; viết lại cho sản phẩm của mình. Không có AI -> điền theo công thức.
"""
import random

from core.config import MODELS, NO_AI

# Danh mục sản phẩm dùng chung (sửa trong app, lưu data/edit/san_pham.json)
from core.san_pham import SAN_PHAM  # noqa: E402

CONG_THUC = """Phong cách: kênh TikTok "giảm giá kịch tính" bán phân bón cho bà con nhà vườn.
Lời đọc 35-45 giây (110-140 chữ), giọng bản tin giật gân, xưng "bà con". Văn NÓI liền mạch: mỗi câu dài
vừa phải, các ý nối bằng dấu phẩy (như "Thực sự là quá rẻ, ai săn trước được trước, ai chưa săn thì đừng buồn vì
chỉ sale mở bán một ngày ưu đãi trực tiếp trên kênh"). KHÔNG viết câu cụt 3-5 chữ liên tiếp.
Cấu trúc:
1. Câu mở = tiêu đề: [từ giật: Chấn động / Rúng động / Giật mình / Hoang mang dư luận / Bê bối / Sốc...] + vụ giá
   [sản phẩm] + giảm giá cắm đầu / tụt tận đáy + miễn ship toàn quốc.
2. Vì sao rẻ (xả kho, sale lâu lâu mới có, hiệu thuốc không có giá này, rẻ hơn bữa sáng...).
3. Thành phần / nguồn gốc (CHỈ dùng thông tin sản phẩm được cho, không bịa số liệu).
4. Lợi ích cho cây.
5. Cách dùng, độ tiết kiệm.
6. Ưu đãi (miễn ship, chỉ hôm nay).
7. Câu kết CỐ ĐỊNH: "Bà con mua được giá bao nhiêu để lại bình luận cho mọi người cùng tham khảo ý kiến nhé."
Tiêu đề: 3 dòng IN HOA không dấu câu, mỗi dòng tối đa 32 ký tự. Dòng 1 = từ giật + tên sản phẩm (tô vàng).
Viết số bằng chữ khi đọc dễ nhầm (2.000 -> hai nghìn). Không dùng emoji, không hashtag.
Nên chèn 1 câu an toàn kiểu: "Nhận hàng ưng thì thanh toán, kết quả với mỗi người dùng có thể khác nhau,
giá sẽ thay đổi tùy thời điểm" (tránh bị đánh giá quảng cáo sai sự thật). Không hứa chữa khỏi / tăng năng suất bao nhiêu %."""

SCHEMA = {
    "type": "object",
    "properties": {
        "tieu_de": {"type": "array", "items": {"type": "string"}, "description": "3 dòng tiêu đề"},
        "loi": {"type": "string", "description": "toàn bộ lời đọc"},
    },
    "required": ["tieu_de", "loi"],
    "additionalProperties": False,
}


def _goi_ai(prompt: str, settings: dict, model: str) -> dict:
    from core import analyze
    content = [{"type": "text", "text": prompt}]
    system = "Bạn là người viết kịch bản video TikTok bán hàng nông nghiệp tiếng Việt."
    if model.startswith("gemini"):
        return analyze._gemini(content, SCHEMA, settings, model, system=system)
    return analyze._claude(content, SCHEMA, settings, model, system=system)


def viet(sp_key: str, tham_khao: list, settings: dict, model: str = "", y_tuong: str = "") -> dict:
    """Trả về {'tieu_de': '3 dòng\\n', 'loi': '...'}."""
    sp = SAN_PHAM[sp_key]
    if not (sp.get("thong_tin") or "").strip():
        raise ValueError(f"Chưa có thông tin sản phẩm {sp['ten']}: điền ở mục 'Thông tin sản phẩm' trước khi viết kịch bản")
    model = model or settings.get("ai_model") or NO_AI
    if model == NO_AI or model not in MODELS:
        return mau_khong_ai(sp_key)
    mau = "\n\n".join(f"--- Kịch bản tham khảo {i + 1} ---\n{t}" for i, t in enumerate(tham_khao[:6] if tham_khao else []))
    prompt = (f"{CONG_THUC}\n\nSẢN PHẨM: {sp['ten']} ({sp['quy_cach']})\nTHÔNG TIN: {sp['thong_tin']}\n"
              + (f"\nÝ TƯỞNG / ƯU ĐÃI ĐỢT NÀY: {y_tuong}\n" if y_tuong else "")
              + ("\nCác kịch bản dưới đây của kênh khác (khác ngành, chép tự động nên có thể sai chính tả). "
                 "Học cách giật tít, nhịp câu, cách dẫn dắt, KHÔNG chép nguyên câu, KHÔNG lấy sản phẩm của họ:\n"
                 + mau if mau else "")
              + "\n\nViết 1 kịch bản mới cho sản phẩm trên.")
    r = _goi_ai(prompt, settings, model)
    tieu_de = [ln.strip().upper() for ln in r.get("tieu_de", []) if ln.strip()][:3]
    return {"tieu_de": "\n".join(tieu_de), "loi": r["loi"].strip()}


def mau_khong_ai(sp_key: str) -> dict:
    """Không có AI: ghép theo công thức (đổi từ giật ngẫu nhiên)."""
    sp = SAN_PHAM[sp_key]
    giat = random.choice(["Chấn động", "Rúng động", "Giật mình", "Hoang mang dư luận", "Bê bối"])
    ten = sp["ten"]
    loi = (f"{giat} vụ giá {ten} giảm giá cắm đầu tận đáy, cộng miễn phí ship toàn quốc. "
           f"Nhiều bà con không tin nổi, ngày thường không có giá này, hôm nay đại lý xả kho lâu lâu mới có một lần. "
           f"{sp['thong_tin']} "
           f"Ai nhanh tay đặt ngay tại video này được miễn phí vận chuyển. "
           f"Bà con mua được giá bao nhiêu để lại bình luận cho mọi người cùng tham khảo ý kiến nhé.")
    tieu_de = f"{giat} vụ {ten}\nGiảm giá cắm đầu tận đáy\nCộng miễn phí ship toàn quốc".upper()
    return {"tieu_de": tieu_de, "loi": loi}
