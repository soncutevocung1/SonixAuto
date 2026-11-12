"""Giao diện Sonix Đăng Video: màu, nền, kiểu khung, sáng/tối, ảnh đại diện, ô số liệu.

Font (Montserrat cho tiêu đề, Be Vietnam Pro cho chữ thường) khai báo trong .streamlit/config.toml.
"""
import base64
import io
import json

from .config import BASE_DIR, DATA_DIR

APP_TITLE = "Sonix Auto"  # gồm 2 mục: Sonix Up Video (đăng) + Sonix Edit Video (dựng)
STATIC_DIR = BASE_DIR / "static"        # Streamlit phục vụ thư mục này ở /app/static/
BG_FILE = STATIC_DIR / "nen_rieng.jpg"  # ảnh nền riêng của bác (không đóng gói khi chia sẻ)
AVATAR = BASE_DIR / "assets" / "sonix.png"  # ảnh cố định cạnh tên app (đã bỏ chức năng đổi ảnh)

# Mẫu nền: (tên, các vệt màu (x%, y%, màu rgba) cho giao diện sáng, cho giao diện tối)
BACKGROUNDS = {
    "xanh_tim": ("Xanh dương – tím (mặc định)",
                 [(0, 0, "59,130,246,.30"), (100, 15, "139,92,246,.30"), (50, 100, "14,165,233,.18")],
                 [(0, 0, "37,99,235,.45"), (100, 15, "124,58,237,.42"), (50, 100, "14,165,233,.22")]),
    "dai_duong": ("Đại dương",
                  [(0, 0, "6,182,212,.28"), (100, 30, "59,130,246,.26"), (40, 100, "45,212,191,.22")],
                  [(0, 0, "8,145,178,.42"), (100, 30, "29,78,216,.42"), (40, 100, "13,148,136,.30")]),
    "hoang_hon": ("Hoàng hôn",
                  [(0, 0, "244,114,182,.26"), (100, 10, "251,146,60,.24"), (60, 100, "139,92,246,.24")],
                  [(0, 0, "190,24,93,.40"), (100, 10, "194,65,12,.34"), (60, 100, "109,40,217,.40")]),
    "dong_lua": ("Đồng lúa",
                 [(0, 0, "74,222,128,.26"), (100, 20, "250,204,21,.22"), (40, 100, "45,212,191,.20")],
                 [(0, 0, "21,128,61,.40"), (100, 20, "161,98,7,.32"), (40, 100, "15,118,110,.32")]),
    "dem_tim": ("Đêm tím",
                [(0, 0, "99,102,241,.32"), (100, 0, "168,85,247,.32"), (50, 100, "79,70,229,.30")],
                [(0, 0, "67,56,202,.55"), (100, 0, "126,34,206,.50"), (50, 100, "30,27,75,.70")]),
    "tron": ("Trơn (không hiệu ứng)", [], []),
    "anh_rieng": ("Ảnh của bác (tải lên bên dưới)", [], []),
}
CARDS = {"kinh": "Kính mờ", "trong": "Trong suốt", "dac": "Mặc định (nền đặc)"}

PAL = {  # bảng màu theo giao diện
    "light": {"base": "#f4f5fb", "text": "#151629", "muted": "#4a4e6c", "line": "rgba(30,30,80,.14)",
              "blue": "#1d4ed8", "purple": "#6d28d9", "cyan": "#0e7490", "danger": "#be123c", "ok": "#047857",
              "card": {"kinh": "rgba(255,255,255,.62)", "trong": "rgba(255,255,255,.20)", "dac": "#ffffff"},
              "veil": "rgba(244,245,251,.55)"},
    "dark": {"base": "#0b0b14", "text": "#eef0ff", "muted": "#aab0cf", "line": "rgba(255,255,255,.13)",
             "blue": "#7cb0ff", "purple": "#b99bff", "cyan": "#67d8ea", "danger": "#ff8aa3", "ok": "#45e0a0",
             "card": {"kinh": "rgba(22,24,44,.58)", "trong": "rgba(22,24,44,.20)", "dac": "#15162a"},
             "veil": "rgba(11,11,20,.55)"},
}


def mode(settings) -> str:
    return "dark" if settings.get("ui_theme") == "dark" else "light"


def _blobs(spots):
    return ", ".join(f"radial-gradient(900px 640px at {x}% {y}%, rgba({c}), transparent 62%)" for x, y, c in spots)


def css(settings, actual=None) -> str:
    m = actual if actual in ("light", "dark") else mode(settings)  # theo giao diện ĐANG HIỆN
    p = PAL[m]
    bg = settings.get("ui_bg") or "xanh_tim"
    card = settings.get("ui_card") or "kinh"
    blur = 16 if card == "kinh" else 0
    layer = ""
    if bg == "anh_rieng" and BG_FILE.exists():
        v = int(BG_FILE.stat().st_mtime)
        bb = int(settings.get("ui_bg_blur", 8))
        layer = (f".stApp::before{{content:'';position:fixed;inset:-{bb * 3}px;z-index:0;pointer-events:none;"
                 f"background:linear-gradient({p['veil']},{p['veil']}),url('/app/static/{BG_FILE.name}?v={v}') "
                 f"center/cover no-repeat;filter:blur({bb}px)}}")
    elif bg in BACKGROUNDS and BACKGROUNDS[bg][1]:
        spots = BACKGROUNDS[bg][1 if m == "light" else 2]
        anim = "animation:sxdrift 26s ease-in-out infinite alternate;" if settings.get("ui_motion", True) else ""
        layer = (f".stApp::before{{content:'';position:fixed;inset:-10%;z-index:0;pointer-events:none;"
                 f"background:{_blobs(spots)};{anim}}}"
                 "@keyframes sxdrift{0%{transform:translate(0,0) scale(1)}100%{transform:translate(4%,-3%) scale(1.08)}}")
    glass = (f"background:var(--sx-card)!important;border:1px solid var(--sx-line)!important;"
             f"backdrop-filter:blur({blur}px) saturate(140%);-webkit-backdrop-filter:blur({blur}px) saturate(140%);")
    return f"""<style>
:root{{--sx-base:{p['base']};--sx-text:{p['text']};--sx-muted:{p['muted']};--sx-line:{p['line']};
--sx-card:{p['card'][card]};--sx-blue:{p['blue']};--sx-purple:{p['purple']};--sx-cyan:{p['cyan']};
--sx-danger:{p['danger']};--sx-ok:{p['ok']};--sx-grad:linear-gradient(135deg,#2563eb,#7c3aed)}}
.stApp{{background:var(--sx-base)!important}}
{layer}
[data-testid="stAppViewContainer"],[data-testid="stMain"],[data-testid="stHeader"]{{background:transparent!important}}
[data-testid="stAppViewContainer"]{{position:relative;z-index:1}}
[data-testid="stMainBlockContainer"]{{padding-top:2.2rem;max-width:1500px}}
section[data-testid="stSidebar"]{{{glass}border-width:0 1px 0 0!important}}
section[data-testid="stSidebar"] > div{{background:transparent!important}}
h1,h2,h3{{letter-spacing:-.02em}}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{{font-style:italic;font-weight:300}}
/* thanh mục */
[data-testid="stTabs"] [role="tablist"]{{{glass}border-radius:18px;padding:6px;gap:4px;flex-wrap:wrap;
  box-shadow:0 8px 28px rgba(40,40,110,.10)}}
[data-testid="stTab"]{{border-radius:12px;padding:7px 12px;margin:0!important;transition:background .2s}}
[data-testid="stTab"] p{{font-weight:600;font-size:14px;white-space:nowrap}}
[data-testid="stTab"]:hover{{background:rgba(99,102,241,.10)}}
[data-testid="stTab"][aria-selected="true"]{{background:var(--sx-grad)!important}}
[data-testid="stTab"][aria-selected="true"] p{{color:#fff!important}}
[data-testid="stTabs"] [role="tablist"]::after,[data-testid="stTabs"] [role="tablist"]::before{{display:none!important}}
[data-testid="stTab"]{{box-shadow:none!important;border-bottom:0!important}}
[data-testid="stTabs"] [role="tablist"] > div:not([data-testid="stTab"]){{display:none!important}}
[data-testid="stTab"]::after,[data-testid="stTab"]::before{{display:none!important}}
/* thẻ, khung, hộp mở rộng, bảng nổi */
[class*="st-key-card_"],[data-testid="stExpander"] details,[data-testid="stPopoverBody"]{{{glass}border-radius:20px!important;
  box-shadow:0 10px 30px rgba(40,40,110,.08)}}
[class*="st-key-card_"]{{padding:18px!important}}
/* nút */
[data-testid="stBaseButton-primary"]{{background:var(--sx-grad)!important;border:0!important;color:#fff!important;
  box-shadow:0 8px 22px rgba(124,58,237,.30);transition:filter .2s,transform .2s}}
[data-testid="stBaseButton-primary"]:hover{{filter:brightness(1.1);transform:translateY(-1px)}}
[data-testid="stBaseButton-secondary"],[data-testid="stPopoverButton"]{{{glass}}}
[data-testid="stBaseButton-secondary"]:hover,[data-testid="stPopoverButton"]:hover{{border-color:var(--sx-purple)!important;color:var(--sx-purple)!important}}
/* các khối riêng của app */
.sx-brand{{display:flex;align-items:center;gap:12px;margin:-6px 0 4px}}
.sx-brand img{{width:58px;height:58px;border-radius:50%;object-fit:cover;box-shadow:0 0 0 2px #7c3aed,0 0 0 5px rgba(37,99,235,.30)}}
.sx-name{{font-family:Montserrat,sans-serif;font-weight:800;font-size:21px;line-height:1.12;color:var(--sx-text)}}
.sx-note{{font-style:italic;font-weight:300;color:var(--sx-muted);font-size:12.5px;margin-top:3px}}
.sx-pill{{display:flex;align-items:center;gap:10px;border-radius:999px;padding:8px 14px;font-size:13.5px;font-weight:600;
  border:1px solid var(--sx-line);background:var(--sx-card)}}
.sx-dot{{width:9px;height:9px;border-radius:50%;flex:0 0 9px}}
.sx-ok .sx-dot{{background:var(--sx-ok);animation:sxpulse 1.8s ease-in-out infinite}}
.sx-bad{{color:var(--sx-danger)}} .sx-bad .sx-dot{{background:var(--sx-danger)}}
@keyframes sxpulse{{0%,100%{{box-shadow:0 0 0 0 rgba(69,224,160,.55)}}50%{{box-shadow:0 0 0 7px rgba(69,224,160,0)}}}}
.sx-day{{display:flex;justify-content:space-between;align-items:flex-end;margin-top:6px}}
.sx-day b{{font-family:Montserrat,sans-serif;font-weight:800;font-size:16px}}
.sx-tiles{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:8px 0 6px}}
.sx-tile{{border-radius:16px;padding:12px 14px;border:1px solid var(--sx-line);background:var(--sx-card)}}
.sx-tile .l{{font-size:12.5px;font-weight:600;color:var(--sx-muted)}}
.sx-tile .v{{font-family:Montserrat,sans-serif;font-size:30px;font-weight:800;line-height:1.15}}
.sx-tbl{{width:100%;border-collapse:collapse;font-size:13.5px}}
.sx-tbl td{{padding:6px 2px;border-top:1px solid var(--sx-line)}} .sx-tbl td.n{{text-align:right;font-weight:800;font-family:Montserrat,sans-serif}}
.sx-tbl th{{text-align:left;font-size:12px;color:var(--sx-muted);font-weight:600;padding:8px 2px 2px}}
[data-testid="stButtonGroup"] button{{padding:2px 12px;min-height:30px}}
[data-testid="stButtonGroup"] p{{font-size:13px}}
.gold{{background:rgba(124,58,237,.12);color:var(--sx-purple);border-radius:8px;padding:1px 8px;font-weight:700}}
.conf-g{{color:var(--sx-ok);font-weight:700}}.conf-y{{color:#b45309;font-weight:700}}.conf-r{{color:var(--sx-danger);font-weight:700}}
.sx-cdot{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:baseline}}
.sx-cdot.g{{background:#10b981}}.sx-cdot.y{{background:#f59e0b}}.sx-cdot.r{{background:#e11d48}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>"""


def theme_script(settings) -> str:
    """Giữ đúng sáng/tối bác chọn (mặc định SÁNG kể cả khi Windows để chế độ tối)."""
    want = json.dumps("Dark" if mode(settings) == "dark" else "Light")
    return f"""<script>
(function(){{try{{
 var P = window.parent, k = 'stActiveTheme-' + P.location.pathname + '-v2', want = {json.dumps(want)};
 if (P.localStorage.getItem(k) === want) return;
 var rk = 'sx_theme_reload_' + want, last = +(P.sessionStorage.getItem(rk) || 0);
 if (Date.now() - last < 4000) return;   // chống tải lại liên tục
 P.sessionStorage.setItem(rk, Date.now());
 P.localStorage.setItem(k, want); P.location.reload();
}}catch(e){{}}}})();
</script>"""


def avatar_uri(size=116) -> str:
    try:
        from PIL import Image
        im = Image.open(AVATAR)
        im.thumbnail((size, size))
        buf = io.BytesIO()
        im.save(buf, "PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


def brand_html(uri: str) -> str:
    img = f'<img src="{uri}" alt="Ảnh đại diện">' if uri else ""
    return (f'<div class="sx-brand">{img}<div><div class="sx-name">{APP_TITLE}</div>'
            f'<div class="sx-note">Đăng TikTok tự động · dựng video CapCut</div></div></div>')


def pill_html(ok: bool) -> str:
    return (f'<div class="sx-pill {"sx-ok" if ok else "sx-bad"}"><span class="sx-dot"></span>'
            f'Bộ đăng tự động: {"đang chạy" if ok else "chưa chạy"}</div>')


def tiles_html(tiles, cols=2) -> str:
    """tiles: [(nhãn, số, màu css)]"""
    return f'<div class="sx-tiles" style="grid-template-columns:repeat({cols},minmax(0,1fr))">' + "".join(
        f'<div class="sx-tile"><div class="l">{lb}</div><div class="v" style="color:{c}">{v}</div></div>'
        for lb, v, c in tiles) + "</div>"


def table_html(title_a, rows) -> str:
    """rows: [(tên, số)] -> bảng nhỏ 2 cột."""
    body = "".join(f'<tr><td>{a}</td><td class="n">{n}</td></tr>' for a, n in rows) or \
        '<tr><td colspan="2"><i>Chưa có</i></td></tr>'
    return f'<table class="sx-tbl"><tr><th>{title_a}</th><th style="text-align:right">Số video</th></tr>{body}</table>'


def save_bg(data: bytes):
    """Lưu ảnh nền riêng (thu nhỏ còn tối đa 1920px cho nhẹ)."""
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    im.thumbnail((1920, 1920))
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    im.save(BG_FILE, "JPEG", quality=85)


def preview_html(key) -> str:
    """Ô màu xem trước 1 mẫu nền (cho phần Cài đặt)."""
    light = BACKGROUNDS[key][1]
    cols = ", ".join("rgba(" + c.rsplit(",", 1)[0] + ",.75)" for _x, _y, c in light) if light else "#eceefa, #eceefa"
    return (f'<div style="height:54px;border-radius:12px;border:1px solid rgba(30,30,80,.14);'
            f'background:linear-gradient(135deg, {cols})"></div>')


def matrix_html(first, heads, rows) -> str:
    """Bảng: cột đầu là tên (kênh/sản phẩm), các cột sau là số theo từng loại việc."""
    th = "".join(f'<th style="text-align:right">{h}</th>' for h in heads)
    body = "".join("<tr><td>" + a + "</td>" + "".join(f'<td class="n">{v or "–"}</td>' for v in vals) + "</tr>"
                   for a, vals in rows) or f'<tr><td colspan="{len(heads) + 1}"><i>Chưa có việc nào</i></td></tr>'
    return f'<table class="sx-tbl"><tr><th>{first}</th>{th}</tr>{body}</table>'
