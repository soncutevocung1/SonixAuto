# Ghi chú phiên bản Sonix Đăng Video

## 2.3.4
- Kiểm tra ảnh bìa TikTok: chờ danh sách bài tải về lâu hơn (máy bận), cuộn tới hết danh sách; ghi kết quả vào nhật ký (đúng bìa / thiếu bìa / đã xoá / chưa rõ).

## 2.3.3
- TikTok · Ảnh bìa: lưu ảnh bìa xong chờ TikTok tải ảnh lên máy chủ rồi mới làm bước tiếp; kiểm tra ô bìa trên trang (làm lại 1 lần nếu chưa giống).
- TikTok · Kiểm tra ảnh bìa sau khi hẹn giờ: lúc rảnh, tool vào TikTok Studio so ảnh bìa thật của từng bài. Thiếu bìa → video về CHƯA UP, thanh bên báo bài cần xoá trong app TikTok (web không cho xoá bài có giỏ hàng). Bác xoá xong → tool tự đăng lại kèm ảnh bìa.
- Máy nhẹ hơn: bộ đăng và phân tích chạy ở mức ưu tiên dưới bình thường (nhường máy cho việc khác của bác); AI phân tích 2 video/lần thay vì 4.
- Xếp lịch TikTok: đổi tên ô cho rõ ("Ngày đầu: bắt đầu lúc" và "Mỗi ngày chỉ đăng từ / đến"), có dòng tóm tắt và nhắc khi 2 giờ này khác nhau.

## 2.3.2
- TikTok · Ảnh bìa: mặc định vẫn là khung hình cắt từ video. Chỉ khi bấm "Tự gắn ảnh bìa theo sản phẩm" thì tool mới nhận diện và gắn ảnh trong thư mục ẢNH BÌA. Gỡ các ảnh bìa mặc định bản 2.3.1 đã tự đặt.

## 2.3.1
- TikTok · Ảnh bìa: nút "Tự gắn ảnh bìa theo sản phẩm" — mỗi video đang chọn tự lấy ảnh trong thư mục ẢNH BÌA trùng tên sản phẩm AI nhận ra (vd Kích rễ TC01.png, Đạm cá amino.png dùng cho cả can 1 lít và 5 lít).
- Sản phẩm chưa đặt ảnh bìa mặc định thì tool tự ghép theo tên ảnh (1 lần), video mới phân tích xong có bìa luôn. Đổi lại được ở mục Ảnh bìa mặc định theo sản phẩm.

## 2.3.0
- Facebook · Video của trang: xem số video trong CHƯA UP, chưa phân tích, đang phân tích, chờ duyệt, chờ đăng, đã lên Facebook, ĐÃ UP, lỗi; lịch hiện có tới ngày nào.
- Facebook · Chế độ Tự động: đọc toàn bộ video trong CHƯA UP, AI viết caption và lên lịch nối tiếp sau video có lịch muộn nhất. Chép thêm video vào lúc nào, tool tự phát hiện (1 phút/lần) và xếp vào những ngày tiếp theo. Video chỉ đăng sau khi bác bấm Xác nhận.

## 2.2.5
- Facebook: video ngoài khoảng ngày của lịch đăng ghi rõ "Chưa có giờ", không còn hiện giờ giả (hôm nay +1 tiếng), không xác nhận được.
- Nút "Trả video chưa có giờ về CHƯA UP"; xếp lại giờ thì video thiếu chỗ tự trả về CHƯA UP đợi lịch sau.
- Phân tích không quá số khung giờ còn trống trong lịch. Bộ đăng không bao giờ đăng video chưa có giờ.

## 2.2.4
- Facebook: khi AI đang phân tích / viết lại caption, màn hình tự kiểm tra 3 giây/lần và tự hiện kết quả khi xong (trước đây phải tải lại trang mới thấy, trông như bị đứng).

## 2.2.3
- Facebook · Lịch đăng: chọn từ ngày, đến ngày; khung giờ giống nhau mọi ngày hoặc riêng từng thứ trong tuần (để trống = nghỉ); xếp lại giờ cho tất cả hoặc video đang chọn; bảng xem trước lịch theo ngày.
- Facebook · Ảnh bìa: chọn 1 trong 8 khung hình của video, tự tải ảnh lên, hoặc để Facebook tự chọn.
- Sửa lỗi: sau khi Viết lại caption / xếp lại giờ, ô trên màn hình vẫn hiện nội dung cũ.

## 2.2.2
- Facebook: nút Viết lại caption (cả đợt hoặc từng video), giữ nguyên giờ đăng. Hiện số ký tự của caption.
- Giới hạn từ 160 ký tự trở xuống thì AI chỉ viết 1-2 câu ngắn; vượt giới hạn thì tự cắt gọn.
- Video duyệt trễ, giờ đăng đã qua: tự dời sang khung giờ trống kế tiếp, không đăng dồn.

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
