"""Danh mục sản phẩm của Sonix Edit Video (dùng cho viết kịch bản, quét cảnh, tự lọc video).

Mỗi sản phẩm:
  ten        tên đọc trong kịch bản
  quy_cach   quy cách (can 5 lít, chai 100ml...)
  thu_muc    tên thư mục video nguồn (các thư mục bắt đầu bằng tên này đều tính: "KÍCH RỄ", "KÍCH RỄ 13-11-2026"...)
  thong_tin  thành phần / công dụng / cách dùng để AI viết lời (anh sửa trong app)
  nhan       chữ in trên nhãn (không dấu, in hoa) để máy đọc chữ nhận ra sản phẩm
  ten_file   từ khoá trong TÊN FILE video (không phân biệt dấu, hoa thường)
  hinh       mô tả hình dáng để AI nhận ra
Phần anh sửa trong app lưu ở data/edit/san_pham.json (ghi đè lên mặc định dưới đây).
"""
import json
import unicodedata

from .config import DATA_DIR

FILE = DATA_DIR / "edit" / "san_pham.json"

MAC_DINH = {
    "dam_ca": {
        "ten": "Đạm cá Amino", "quy_cach": "can 5 lít", "thu_muc": "ĐẠM CÁ",
        "thong_tin": "Phân bón hữu cơ từ cá tươi thuỷ phân, dịch sánh mịn, đậm đặc, không tanh không hôi. "
                     "Bổ sung 17 loại axit amin, humic, trung vi lượng. 1 can pha 2.000 lít nước, tưới hoặc phun, "
                     "dùng được cho mọi loại cây. Công dụng: cây bung đọt, xanh dày lá, phục hồi cây còi cọc, "
                     "suy kiệt sau thu hoạch, cải tạo đất tơi xốp.",
        "nhan": ["DAM CA", "AMINO", "WIN GOLD", "HUU CO DAM DAC"],
        "ten_file": ["đạm cá", "dam ca", "damca", "amino"],
        "hinh": "Can nhựa trắng (1 lít hoặc 5 lít) nhãn xanh lá, chữ to ĐẠM CÁ AMINO, hình con cá và rau củ",
    },
    "tc01": {
        "ten": "Kích rễ TC01", "quy_cach": "chai 100ml", "thu_muc": "KÍCH RỄ",
        "thong_tin": "Kích rễ giâm cành TC01, chứa Atonik tác động thẳng vào bộ rễ, bổ sung NPK dễ hấp thu. "
                     "Rễ tơ bung trắng, cây bung chồi, đẻ nhánh khoẻ. 1 chai 100ml pha 100 lít nước, "
                     "5-7 ngày tưới 1 lần, cây nào cũng dùng được.",
        "nhan": ["TC01", "TC 01", "KICH RE", "GIAM CANH"],
        "ten_file": ["tc01", "tc 01", "kích rễ", "kich re", "kichre"],
        "hinh": "Chai nhựa nhỏ màu xanh lá, nắp xanh, chữ KÍCH RỄ GIÂM CÀNH TC 01",
    },
    "nano_dong": {
        "ten": "Nano Đồng", "quy_cach": "chai 500ml", "thu_muc": "NANO ĐỒNG",
        "thong_tin": "",
        "nhan": ["NANO DONG", "NANO", "TAY VUON"],
        "ten_file": ["nano đồng", "nano dong", "nanodong", "tẩy vườn", "tay vuon", "rửa vườn", "rua vuon"],
        "hinh": "Chai 500ml, chữ NANO ĐỒNG, dùng tẩy rửa vườn sau thu hoạch",
    },
    "canxi_bo": {
        "ten": "Canxi Bo", "quy_cach": "chai 500ml", "thu_muc": "CANXI BO",
        "thong_tin": "",
        "nhan": ["CANXI BO", "CANXI", "CALCI", "CA-BO", "CABO"],
        "ten_file": ["canxi bo", "canxibo", "canxi", "calci"],
        "hinh": "Chai 500ml, chữ CANXI BO",
    },
    "bam_dinh": {
        "ten": "Siêu bám dính", "quy_cach": "chai 100ml", "thu_muc": "SIÊU BÁM DÍNH",
        "thong_tin": "",
        "nhan": ["BAM DINH", "SIEU BAM"],
        "ten_file": ["bám dính", "bam dinh", "bamdinh"],
        "hinh": "Chai nhỏ 100ml, chữ SIÊU BÁM DÍNH TOÀN CẦU",
    },
    "top_one": {
        "ten": "Bọ trĩ Top One", "quy_cach": "chai 200ml", "thu_muc": "BỌ TRĨ TOP ONE",
        "thong_tin": "",
        "nhan": ["TOP ONE", "TOPONE", "BO TRI", "TRI ONE"],
        "ten_file": ["top one", "topone", "bọ trĩ", "bo tri", "botri", "tri one"],
        "hinh": "Chai 200ml, chữ TOP ONE / BỌ TRĨ",
    },
}

SAN_PHAM = {}


def khong_dau(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").upper()


def nap() -> dict:
    """Đọc lại danh mục (mặc định + phần đã sửa), cập nhật tại chỗ dict SAN_PHAM."""
    data = json.loads(json.dumps(MAC_DINH))
    if FILE.exists():
        try:
            for k, v in json.loads(FILE.read_text(encoding="utf-8")).items():
                data.setdefault(k, {}).update(v)
        except Exception:
            pass
    SAN_PHAM.clear()
    SAN_PHAM.update(data)
    return SAN_PHAM


def luu(key: str, **fields):
    FILE.parent.mkdir(parents=True, exist_ok=True)
    cur = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}
    cur.setdefault(key, {}).update(fields)
    FILE.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")
    nap()


def theo_ten_file(name: str) -> list:
    """Các sản phẩm có từ khoá trong tên file (không dấu)."""
    t = khong_dau(name).replace("_", " ").replace("-", " ")
    return [k for k, sp in SAN_PHAM.items() if any(khong_dau(w) in t for w in sp.get("ten_file", []))]


nap()
