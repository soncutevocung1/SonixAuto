"""Tự xuất video từ CapCut (1080p) rồi đưa vào CHƯA UP\\<dd.mm.yyyy>\\01.mp4... của kênh.

CapCut không có lệnh xuất từ bên ngoài và giao diện (Qt/QML) không cho phần mềm khác đọc nút bấm, nên tool
điều khiển như người: chụp màn hình CapCut, đọc chữ (RapidOCR) để tìm vị trí, rồi bấm chuột / gõ phím.
Trong lúc tool xuất (khoảng 1 phút / video) KHÔNG đụng chuột, bàn phím.

Mỗi video:
  1. CapCut tắt -> đưa dự án lên đầu danh sách (sửa giờ chỉnh sửa trong danh sách dự án)
  2. Mở CapCut -> bấm thẻ dự án đầu tiên -> Esc (hộp "Liên kết tệp phương tiện" nếu có)
  3. Ctrl+E -> chọn Độ phân giải 1080P -> đặt tên file tạm -> bấm Xuất -> chờ file xong
  4. Tắt CapCut -> chuyển file vào thư mục kênh
"""
import glob
import json
import os
import shutil
import subprocess
import time
import unicodedata
from pathlib import Path

from .capcut_draft import CAPCUT_DRAFTS, _fwd, capcut_dang_mo

CAPCUT_EXE = Path(os.path.expandvars(r"%LOCALAPPDATA%\CapCut\Apps\CapCut.exe"))
_OCR = None
GOC_KENH = ""  # thư mục Sonix Up Video (đặt trong xuat_va_dua) để tìm file vừa xuất


class XuatError(Exception):
    pass


def _kd(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()


def _ocr():
    global _OCR
    if _OCR is None:
        from rapidocr_onnxruntime import RapidOCR
        _OCR = RapidOCR()
    return _OCR


def _cua_so():
    import uiautomation as auto
    for w in auto.GetRootControl().GetChildren():
        if (w.Name or "") == "CapCut" and "QMLTYPE" in (w.ClassName or ""):
            return w
    return None


def _doc(w, luu: str = ""):
    """Chụp cửa sổ CapCut, đọc chữ -> [(x, y, chữ)] theo toạ độ màn hình."""
    import numpy as np
    from PIL import ImageGrab
    r = w.BoundingRectangle
    bb = (r.left, r.top, r.right, r.bottom)
    img = ImageGrab.grab(bbox=bb, all_screens=True)
    if luu:
        img.save(luu)
    res, _ = _ocr()(np.array(img)[:, :, ::-1])
    return [(int(sum(p[0] for p in b) / 4) + bb[0], int(sum(p[1] for p in b) / 4) + bb[1], t) for b, t, sc in res or []]


def _tim(items, *chu, chua=False):
    for x, y, t in items:
        tt = _kd(t)
        for c in chu:
            if (c in tt) if chua else (tt == c):
                return x, y
    return None


def _bam(w, x, y):
    """Đưa CapCut lên trước rồi mới bấm (người dùng có thể vừa bấm sang cửa sổ khác)."""
    import uiautomation as auto
    try:
        w.SetActive()
    except Exception:
        pass
    time.sleep(0.2)
    auto.Click(int(x), int(y))


def _cho(dk, giay, buoc=1.0):
    end = time.time() + giay
    while time.time() < end:
        v = dk()
        if v:
            return v
        time.sleep(buoc)
    return None


def dua_len_dau(ten: str):
    """Cho dự án `ten` thành mới chỉnh sửa nhất (CapCut xếp lên đầu trang chủ). CapCut phải đang tắt."""
    now = int(time.time() * 1_000_000)
    rp = CAPCUT_DRAFTS / "root_meta_info.json"
    root = json.loads(rp.read_text(encoding="utf-8"))
    ok = False
    for e in root.get("all_draft_store", []):
        if e.get("draft_name") == ten:
            e["tm_draft_modified"] = now
            ok = True
    if not ok:
        raise XuatError(f"Không thấy dự án '{ten}' trong CapCut")
    t = rp.with_suffix(".json.sonix_tmp")
    t.write_text(json.dumps(root, ensure_ascii=False), encoding="utf-8")
    os.replace(t, rp)
    mp = CAPCUT_DRAFTS / ten / "draft_meta_info.json"
    if mp.exists():
        m = json.loads(mp.read_text(encoding="utf-8"))
        m["tm_draft_modified"] = now
        mp.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")


def tat_capcut(giay=20):
    w = _cua_so()
    if w:
        try:
            w.GetWindowPattern().Close()
        except Exception:
            import uiautomation as auto
            w.SetActive()
            auto.SendKeys("{Alt}{F4}")
    if not _cho(lambda: not capcut_dang_mo(), giay):
        subprocess.run(["taskkill", "/IM", "CapCut.exe", "/F"], capture_output=True, creationflags=0x08000000)
        _cho(lambda: not capcut_dang_mo(), 10)


def _thu_muc_tim(ocr_path: str) -> list:
    """Nơi có thể chứa file vừa xuất."""
    """Nơi có thể chứa file vừa xuất: [(thư mục, tìm cả thư mục con?)]."""
    home = Path.home()
    out = []
    if ocr_path and ":" in ocr_path:
        p = ocr_path.split("...")[0].split("…")[0]
        p = p[:p.rfind("/") + 1] or p
        if os.path.isdir(p):
            out.append((Path(p), True))
    if GOC_KENH and os.path.isdir(GOC_KENH):
        out.append((Path(GOC_KENH), True))
    out += [(Path(f"{d}:\\"), False) for d in "CDEFGH" if os.path.exists(f"{d}:\\")]
    out += [(home / "Videos", True), (home / "Desktop", False), (home / "Documents", False)]
    return out


def xuat_mot(ten: str, log=print, anh_dir: Path = None) -> Path:
    """Xuất dự án `ten` ra file mp4 1080p. Trả về đường dẫn file."""
    import uiautomation as auto
    if capcut_dang_mo():
        raise XuatError("CapCut đang mở: tắt CapCut trước")
    if not CAPCUT_EXE.exists():
        raise XuatError(f"Không thấy CapCut ở {CAPCUT_EXE}")
    dua_len_dau(ten)
    log(f"Mở CapCut: {ten}")
    subprocess.Popen([str(CAPCUT_EXE)])
    w = _cho(_cua_so, 90, 2)
    if not w:
        raise XuatError("CapCut không mở lên")
    time.sleep(6)
    anh = (lambda n: str(anh_dir / f"{n}.png")) if anh_dir else (lambda n: "")
    try:
        w.SetActive()
        auto.SendKeys("{Esc}")  # tắt thông báo / quảng cáo nếu có
        time.sleep(1)
        DU_AN = ("du an", "dy an", "du án", "dv an", "projects")
        # Hàng "Dự án": [Dự án] ........ [kính lúp] [lưới] [Thùng rác] [Đồng bộ dự án]. Chữ nhỏ trên nút hay bị
        # OCR đọc sai ("Thùng rác" -> "gu buqu"), nên chỉ cần thấy chữ "Dự án" ở nửa trái; kính lúp tính theo nút
        # đọc được, không có thì theo mép phải cửa sổ (luôn cách mép phải ~339 px).
        r0 = w.BoundingRectangle

        def trang_chu():
            x = _doc(w, anh("1_trangchu"))
            for xx, yy, t in x:
                if _kd(t) in DU_AN and xx < r0.left + (r0.right - r0.left) / 2:
                    return x, (xx, yy)
            return None
        kq = _cho(trang_chu, 40, 2)
        if not kq:
            raise XuatError("Không thấy mục Dự án ở trang chủ CapCut")
        it, (hx, hy) = kq
        tr = _tim([q for q in it if abs(q[1] - hy) < 15], "thung rac", "trash", chua=True)
        db = _tim([q for q in it if abs(q[1] - hy) < 15], "dong b", "sync", chua=True)
        kx = tr[0] - 115 if tr else db[0] - 223 if db else w.BoundingRectangle.right - 339
        _bam(w, kx, hy)  # kính lúp tìm dự án
        time.sleep(1)
        auto.SendKeys("{Ctrl}a")
        auto.SendKeys(ten)
        time.sleep(2.5)
        it = _doc(w, anh("1b_tim"))
        so_khop = [t for x, y, t in it if y > hy + 60 and _kd(ten)[-6:].replace(" ", "") in _kd(t).replace(" ", "")]
        if not so_khop:
            log("   (không đọc được tên dưới thẻ, vẫn mở thẻ đầu tiên của kết quả tìm)")
        _bam(w, hx + 48, hy + 90)  # thẻ dự án đầu tiên trong kết quả tìm
        # chờ vào màn hình chỉnh sửa (có chữ "Tệp phương tiện" / "Media")
        def vao():
            ww = _cua_so()
            if not ww:
                return None
            x = _doc(ww)
            return (ww, x) if _tim(x, "nhap", "import", "dong thoi gian", "timeline", chua=True) else None
        r = _cho(vao, 60, 3)
        if not r:
            raise XuatError("Không mở được dự án")
        w = r[0]
        time.sleep(3)
        for _ in range(2):  # hộp "Liên kết tệp phương tiện" (file cũ của khuôn) -> bỏ qua
            w.SetActive()
            auto.SendKeys("{Esc}")
            time.sleep(1)
        w.SetActive()
        auto.SendKeys("{Ctrl}e")
        it = _cho(lambda: (lambda x: x if _tim(x, "xuat sang", "export to", chua=True) else None)(_doc(w, anh("2_xuat"))),
                  20, 1.5)
        if not it:
            raise XuatError("Không mở được hộp Xuất (Ctrl+E)")
        # độ phân giải 1080P
        lab = _tim(it, "phan gia", "resolution", chua=True)
        cur = [t for x, y, t in it if lab and abs(y - lab[1]) < 12 and x > lab[0] + 40]
        if lab and not any("1080" in t for t in cur):
            _bam(w, lab[0] + 180, lab[1])
            time.sleep(1.5)
            it2 = _doc(w)
            o = _tim(it2, "1080p")
            if not o:
                raise XuatError("Không chọn được 1080P")
            _bam(w, *o)
            time.sleep(1)
            log("Chọn độ phân giải 1080P")
        # tên file tạm
        token = "SONIXXUAT" + time.strftime("%y%m%d%H%M%S")
        tl = _tim(it, "ten", "name")
        if not tl:
            raise XuatError("Không thấy ô Tên trong hộp Xuất")
        _bam(w, tl[0] + 230, tl[1])
        time.sleep(0.4)
        auto.SendKeys("{Ctrl}a")
        auto.SendKeys(token)
        time.sleep(0.8)
        it = _doc(w, anh("3_ten"))
        duong = next((t for x, y, t in it if token.lower() in t.lower()), "")
        xs = _tim(it, "xuat sang", "export to", chua=True)
        kt = _tim(it, "khoang thoi gian", "kich thuoc", "duration", "size", chua=True)
        nut = [(x, y) for x, y, t in it if _kd(t) in ("xuat", "export")]
        p = max(nut, key=lambda q: q[1]) if nut else ((xs[0] + 202, kt[1]) if xs and kt else None)
        if not p:
            raise XuatError("Không thấy nút Xuất")
        noi = _thu_muc_tim(duong)

        def thay():
            for d, sau in noi:
                h = glob.glob(os.path.join(glob.escape(str(d)), f"{token}*.mp4"))
                if not h and sau:  # ô "Xuất sang" bị cắt "...": tìm cả thư mục con
                    h = glob.glob(os.path.join(glob.escape(str(d)), "**", f"{token}*.mp4"), recursive=True)
                if h:
                    return h[0]
            return None

        def dang_xuat():  # hộp Xuất đã chuyển sang thanh tiến độ / xong
            x = _doc(w)
            return thay() or ("%" in "".join(t for _, _, t in x)) or _tim(x, "dong", "close", "done") \
                or _tim(x, "dang xuat", "exporting", chua=True)
        for lan in (1, 2, 3):
            _bam(w, *p)
            if _cho(dang_xuat, 12, 2):
                break
            log(f"   chưa thấy bắt đầu xuất, bấm lại nút Xuất (lần {lan + 1})")
        _doc(w, anh("3b_dang_xuat"))
        t0 = time.time()
        log("Đang xuất...")
        f = _cho(thay, 300, 3)
        if not f:
            raise XuatError("Không thấy file xuất ra (quá 5 phút)")
        last, same = -1, 0
        while same < 4 and time.time() - t0 < 900:  # chờ file thôi lớn lên
            s = os.path.getsize(f)
            same = same + 1 if s == last and s > 0 else 0
            last = s
            time.sleep(2)
        log(f"Xuất xong {time.time() - t0:.0f} giây, {last / 1e6:.0f} MB")
        it = _doc(w, anh("4_xong"))
        d = _tim(it, "dong", "close", "done")
        if d:
            _bam(w, *d)
        return Path(f)
    finally:
        time.sleep(1)
        tat_capcut()


def dua_vao_kenh(f: Path, root: str, kenh: str) -> Path:
    """Chuyển video vào CHƯA UP\\<hôm nay>\\NN.mp4 của kênh."""
    from . import channels
    d = channels.thu_muc_ngay(root, kenh)
    dst = d / f"{channels.so_tiep(d)}{f.suffix.lower()}"
    shutil.move(str(f), str(dst))
    return dst


def xuat_va_dua(ten_du_an: list, S: dict, kenh: str, log=print) -> list:
    """Xuất lần lượt các dự án rồi đưa vào kênh. Trả về [đường dẫn video]."""
    root = S.get("root_folder") or ""
    if not root or not kenh:
        raise XuatError("Chưa chọn kênh / thư mục Sonix Up Video")
    from .config import DATA_DIR
    global GOC_KENH
    GOC_KENH = root
    anh_dir = DATA_DIR / "edit" / "xuat_anh"
    anh_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for i, ten in enumerate(ten_du_an, 1):
        log(f"[{i}/{len(ten_du_an)}] Xuất {ten}")
        for lan in (1, 2):
            try:
                f = xuat_mot(ten, log=log, anh_dir=anh_dir)
                dst = dua_vao_kenh(f, root, kenh)
                log(f"   -> {dst}")
                out.append(dst)
                break
            except Exception as e:
                log(f"   lỗi (lần {lan}): {e}")
                tat_capcut()
                time.sleep(3)
    return out
