# Quy trình anh Sơn gửi video gốc để Claude dựng phong cách Sơn 01

## Phần anh Sơn làm (khoảng 2 phút)
1. Chép video gốc (quay thô) vào máy công ty DESKTOP-N1VK96B, trong `E:\SOURCE THÔ\` (thư mục con nào cũng được,
   ví dụ `E:\SOURCE THÔ\25.11.2026\C3501.MP4`). Không đổi tên file máy quay.
2. Nếu là sản phẩm mới (vd bọ trĩ Top One): chép thêm video minh họa vào
   `D:\SONIX_EDIT_VIDEO\SOURCE THÔ\Video Aff\<tên sản phẩm>\` (vd `Bo_Tri_Top_One`).
3. Bật máy công ty + Desktop Commander, mở phiên Claude Code trên repo SonixAuto (nhánh son01).
4. Nhắn 1 tin, ví dụ:
   > Dựng video Sơn 01: file C3501.MP4, sản phẩm bọ trĩ Top One. Ghi chú: đoạn xịt thuốc ở phút 2 là đoạn đáng xem.
   Cần có: **tên file**, **sản phẩm**, ghi chú riêng nếu có (đoạn nào giữ hình gốc, ý nào quan trọng, giá/khuyến mãi).
5. Khi Claude báo "tắt CapCut" thì tắt (Claude không tự tắt). Dựng xong mở CapCut xem, chụp màn hình chỗ chưa ưng gửi lại.

## Phần Claude làm (theo thứ tự, KHÔNG gọi key API nếu anh chưa đồng ý)
0. Đọc `CLAUDE.md`, `PHONG_CACH_SON01.md`, `LUAT_CAT_ANH_SON.md`, kế hoạch mẫu trong `mau/`.
1. Nghe + nhìn source thô trên máy công ty: `v2/chay_c3420.py <TÊN>` (MediaPipe + Whisper chạy trên máy, miễn phí).
   Bước Claude-xem-hình-qua-API bị chốt chặn → Claude tự xem khung hình (xuất bảng ảnh rồi đọc trong cuộc trò chuyện)
   để biết đoạn nào cầm điện thoại đọc kịch bản, đoạn nào rót/cầm sản phẩm (giữ hình gốc).
2. Claude đọc lời từng câu (`v2/xem_chu.py`), tự chọn lần nói tốt nhất, viết `v2/<TÊN>/ke_hoach_tay.json`
   theo khuôn `mau/*.json` (phụ đề xếp lớp, ý chính, zoom, minh họa + goi_y, THỨ/số nếu có liệt kê).
3. `tools/ghep_ke_hoach.py v2/<TÊN>` → `v2/dung_v2.py <TÊN> "<nhãn>" --sp=<sp_...> --tv=D:\SonixRender\thu_vien3\da_gan.json`
   (chờ CapCut tắt) → `tools/kiem_chong.py "<tên dự án>"` phải sạch (chỉ còn 2 dòng chữ mở đầu của khuôn).
4. Kiểm tra cảnh minh họa (`v2/xem_mh.py`): đúng chủ thể lời nói, cảnh thật, 2x, không lộ chai sản phẩm khác.
5. Báo anh tên dự án + tóm tắt; sửa theo góp ý; ghi điểm mới vào `PHONG_CACH_SON01.md`; lưu kế hoạch vào `mau/`.

## Sản phẩm mới (bọ trĩ Top One…)
- Thư viện minh họa cần gắn nhãn cảnh mới → việc số lượng lớn dùng Haiku qua key API: PHẢI HỎI anh trước
  (báo số cảnh, số lượt, chi phí ước tính — vd ~150 cảnh ≈ 13 lượt ≈ vài trăm đồng). Không đồng ý thì Claude tự
  xem bảng ảnh cảnh trong cuộc trò chuyện (chậm hơn).
- Màu ý chính bọ trĩ Top One: **xanh dương** (`MAU_SP["sp_top_one"]`). Thêm từ khóa sản phẩm khác vào luật loại cảnh
  (`hop_le` trong `capcut_son01.py`) nếu cần.
