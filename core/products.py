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


def item_for(settings, channel, products) -> str:
    """Sản phẩm (key) ứng với giỏ hàng đang gắn: giỏ đầu tiên thuộc sản phẩm nào. '' nếu không rõ."""
    ids = [str(p.get("id")) for p in (products or []) if p.get("id")]
    if not ids:
        return ""
    mp = mapping(settings, channel)
    for pid in ids:
        for key, m in mp.items():
            if pid in [str(x) for x in (m.get("ids") or [])]:
                return key
    return ""


def label(p) -> str:
    price = f" · {p['price']}" if p.get("price") else ""
    return f"{p.get('name', '')[:55]}{price} · …{str(p['id'])[-6:]}"


def image_of(channel, pid) -> str:
    """Ảnh sản phẩm trưng bày đã tải về máy ('' nếu chưa có)."""
    f = SHOWCASE_DIR / slug(channel) / f"{pid}.jpg"
    return str(f) if f.exists() and f.stat().st_size > 500 else ""


def candidates(settings, channel, item_key, selected=()) -> list:
    """Các sản phẩm trưng bày có thể gắn cho 1 sản phẩm nhận diện: đang gắn + gợi ý theo từ khoá (mọi shop, mọi dung
    tích đúng). Trả về danh sách dict sản phẩm (đủ tên, giá, tồn, shop, ảnh)."""
    show_all = load_showcase(channel)["products"]
    smap = {p["id"]: p for p in show_all}
    it = next((x for x in settings.get("items", []) if x["key"] == item_key), None)
    ids = list(selected)
    if it:
        ids += mapping(settings, channel).get(item_key, {}).get("ids", [])
        ids += auto_match(it, usable(show_all, settings))
    out, seen = [], set()
    for i in ids:
        if i in seen:
            continue
        seen.add(i)
        out.append(smap.get(i) or {"id": i, "name": "(chưa đồng bộ Trưng bày)"})
    return out


def shops(channel) -> list:
    """Tên các shop có trong Trưng bày (nếu lúc đồng bộ đọc được tên shop)."""
    return sorted({p["shop"] for p in load_showcase(channel)["products"] if p.get("shop")})


# ------------------------------- shop của từng sản phẩm -------------------------------
# TikTok không trả tên shop trong danh sách Trưng bày -> bác ghi tên shop cho từng sản phẩm 1 lần (lưu riêng, đồng bộ
# lại Trưng bày không mất).
def _shop_file(channel):
    return SHOWCASE_DIR / f"{slug(channel)}_shop.json"


def shop_tags(channel) -> dict:
    try:
        return json.loads(_shop_file(channel).read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_shop_tags(channel, tags: dict):
    SHOWCASE_DIR.mkdir(parents=True, exist_ok=True)
    _shop_file(channel).write_text(json.dumps({k: v for k, v in tags.items() if v}, ensure_ascii=False, indent=1),
                                   encoding="utf-8")


def shop_of(channel, p, tags=None) -> str:
    pid = p["id"] if isinstance(p, dict) else p
    t = (shop_tags(channel) if tags is None else tags).get(str(pid), "")
    return t or (p.get("shop", "") if isinstance(p, dict) else "")


def shop_names(settings, channel) -> list:
    """Tên các shop của kênh: bác đặt ở Kênh & sản phẩm + tên đã ghi cho sản phẩm."""
    names = [s.strip() for s in (settings.get("channel_shops", {}).get(channel) or []) if s.strip()]
    if names:
        return names
    for v in list(shop_tags(channel).values()) + shops(channel):
        if v and v not in names:
            names.append(v)
    return names


def pick_by_shop(settings, channel, item_key, shop) -> list:
    """Sản phẩm [{'id','name'}] gắn cho video theo shop: shop = tên 1 shop, hoặc 'all' (mỗi shop 1 mã).
    Không có mã nào của shop đó -> []."""
    tags = shop_tags(channel)
    cands = [p for p in candidates(settings, channel, item_key) if p.get("name") != "(chưa đồng bộ Trưng bày)"]
    out, seen_shop = [], set()
    for p in cands:
        s = shop_of(channel, p, tags)
        if shop == "all":
            if s and s not in seen_shop:
                seen_shop.add(s)
                out.append(p)
        elif s == shop:
            out.append(p)
            break
    return [{"id": p["id"], "name": p.get("name", "")} for p in out]


_THUMB = {}


def thumb_uri(channel, pid, size=96) -> str:
    """Ảnh nhỏ của sản phẩm dạng data URI (để hiện trong bảng). '' nếu chưa có ảnh."""
    f = image_of(channel, pid)
    if not f:
        return ""
    key = (f, size)
    if key not in _THUMB:
        import base64
        import io
        try:
            from PIL import Image
            im = Image.open(f).convert("RGB")
            im.thumbnail((size, size))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=80)
            _THUMB[key] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        except Exception:
            _THUMB[key] = ""
    return _THUMB[key]
