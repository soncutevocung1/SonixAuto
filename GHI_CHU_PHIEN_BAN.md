# Ghi chú phiên bản Sonix Đăng Video

## 2.2.1
- Mỗi trang Facebook phải có thư mục video riêng, tránh đăng nhầm video sang trang khác.
- Thêm quyền read_insights (không bắt buộc) để sau này xem lượt xem từng video.

## 2.2.0
- Làm lại tab Facebook để đăng Reels lên Trang tự động:
  - Kết nối trang bằng mã chính thức của Meta, tool tự đổi sang mã trang không hết hạn.
  - Lấy video từ thư mục CHƯA UP của trang, AI xem video và đọc phụ đề để viết caption (giống TikTok), bác duyệt rồi xác nhận.
  - Tự xếp giờ theo khung giờ bác đặt (vd 11:30, 19:30), đẩy lên Facebook hẹn giờ trước 2 ngày, đăng xong chuyển video sang ĐÃ UP.
  - Tuỳ chọn đăng kèm vào Tin (Story).
- Nhiệm vụ tuần của trang: số Reels / bài viết / Tin đã đăng so với chỉ tiêu, việc còn phải làm, bình luận chưa trả lời và trả lời ngay trong tool.

## 2.1.0
- Cửa sổ app riêng (giống Kid TE), không còn mượn Chrome. Có màn hình chờ lúc khởi động, hết màn hình đen.
- Tool khởi động lại (sau cập nhật) thì cửa sổ tự kết nối lại.
- Có file SonixDangVideo.exe để bấm mở; biểu tượng ngoài màn hình tự đổi sang file này.
- Bấm mở lần nữa thì đưa cửa sổ đang mở lên trước, không mở thêm cửa sổ mới.
- Tắt cửa sổ: bộ đăng vẫn chạy nền, tới giờ hẹn vẫn đăng.
- Cần thêm 1 thư viện nhỏ (pywebview), tool tự cài khi cập nhật.

## 2.0.4
- Có bộ cài SonixDangVideo_Setup.exe: mang sẵn Python và thư viện, cài trên máy mới chỉ cần bấm Tiếp.
- Cài đè bản cũ không mất dữ liệu (đăng nhập kênh, hàng chờ, khoá AI).

## 2.0.2
- Sửa lỗi: cập nhật xong tool tắt nhưng không tự bật lại.

## 2.0.1
- Hiện số phiên bản ở thanh bên dưới tên app.
- Bản thử nút Cập nhật.

## 2.0.0
- Tự cập nhật trong app: Cài đặt → Cập nhật (tải từ GitHub, kiểm tra mã từng file, tự chờ hết video đang đăng, quay lại bản trước được).
- Giao diện mới: sáng/tối, 7 mẫu nền, kiểu khung kính mờ/trong suốt/mặc định.
- Tổng hợp theo ngày theo kênh và sản phẩm.
- Ảnh bìa đúng màu cho video iPhone, ảnh bìa mặc định theo sản phẩm.
