"""Sản phẩm: danh sách trưng bày của từng kênh + cách ghép với sản phẩm AI nhận diện."""
import json
import re
from datetime import datetime

from .config import SHOWCASE_DIR, norm, slug


def showcase_file(channel):
    return SHOWCASE_DIR / f"{slug(channel)}.json"


def load_showcase(channel) -> dict:
    f = showcase_file(channel)
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"synced_at": "", "products": []}


def save_showcase(channel, products):
    SHOWCASE_DIR.mkdir(parents=True, exist_ok=True)
    data = {"synced_at": datetime.now().strftime("%d/%m/%Y %H:%M"), "products": products}
    showcase_file(channel).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


DEFAULT_EXCLUDE = ["HÀNG TẶNG", "LIVESTREAM"]


def excluded(p, tags=None) -> bool:
    """Sản phẩm có nhãn [HÀNG TẶNG...] / [LIVESTREAM] -> không dùng để gắn video."""
    n = norm(p.get("name", ""))
    for t in (DEFAULT_EXCLUDE if tags is None else tags):
        t = norm(t)
        if t and re.search(r"[\[(]\s*" + re.escape(t), n):
            return True
    return False


def usable(products, settings=None) -> list:
    tags = (settings or {}).get("exclude_tags", DEFAULT_EXCLUDE)
    return [p for p in products if not excluded(p, tags)]


def _kw(item):
    return [norm(k) for k in (item.get("keywords") or "").split(",") if k.strip()]


def auto_match(item, showcase_products) -> list:
    """Tìm sản phẩm trưng bày khớp từ khoá của sản phẩm nhận diện (có thể ra 2 cái do 2 giỏ hàng)."""
    kws = _kw(item)
    if not kws:
        return []
    size_kw = [k for k in kws if re.fullmatch(r"\d+\s*(l|lit|ml|kg|g|gr)", k)]   # "1 lit", "5l", "500ml"
    name_kw = [k for k in kws if k not in size_kw]
    if not name_kw:
        name_kw, size_kw = size_kw, []
    allow_combo = any("combo" in k for k in kws)
    hits = [p for p in showcase_products
            if any(k in norm(p.get("name", ""))[:60] for k in name_kw)  # chỉ so phần đầu tên
            and (allow_combo or not norm(p.get("name", "")).startswith("combo"))]
    if size_kw:
        sized = [p for p in hits if any(k in norm(p.get("name", "")) for k in size_kw)]
        if sized:  # tên sản phẩm có ghi dung tích thì lọc theo dung tích
            hits = sized
    return [p["id"] for p in hits]


def mapping(settings, channel) -> dict:
    """{item_key: {"cart": tên giỏ, "ids": [...]}} của 1 kênh, tự gợi ý nếu chưa cài."""
    saved = settings.get("channel_products", {}).get(channel, {})
    show_all = load_showcase(channel)["products"]
    show = usable(show_all, settings)
    ok_ids = {p["id"] for p in show}
    out = {}
    for it in settings.get("items", []):
        m = saved.get(it["key"], {})
        ids = m.get("ids")
        if ids is None:
            ids = auto_match(it, show)
        elif show_all:
            ids = [i for i in ids if i in ok_ids]  # bỏ hàng tặng / livestream
        out[it["key"]] = {"cart": m.get("cart") or it.get("cart") or it["name"][:30], "ids": ids}
    return out


def resolve(settings, channel, item_key) -> tuple:
    """Trả về (danh sách sản phẩm [{'id','name'}], tên giỏ) cho 1 sản phẩm nhận diện."""
    if not item_key:
        return [], ""
    m = mapping(settings, channel).get(item_key)
    if not m:
        return [], ""
    names = {p["id"]: p.get("name", "") for p in load_showcase(channel)["products"]}
    return [{"id": i, "name": names.get(i, "")} for i in m["ids"]], m["cart"][:30]


def label(p) -> str:
    price = f" · {p['price']}" if p.get("price") else ""
    return f"{p.get('name', '')[:55]}{price} · …{str(p['id'])[-6:]}"
