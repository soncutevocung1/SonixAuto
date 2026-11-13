# Ghi chú phiên bản Sonix Auto

## 2.6.0
- Máy chưa có thư mục nguồn của Edit Video: tool tự tạo **`SONIX_EDIT_VIDEO`** cùng ổ với `SONIX_UP_VIDEO`, có sẵn thư mục `CHƯA LỌC` (bỏ video lẫn lộn vào để tự lọc) và `TÀI NGUYÊN` (nhạc nền, khung, người dẫn).
- Sonix Edit Video có **6 sản phẩm**: Đạm cá Amino, Kích rễ TC01, Nano Đồng, Canxi Bo, Siêu bám dính, Bọ trĩ Top One. Mục **Thông tin sản phẩm** để điền thành phần, công dụng, cách pha (AI viết lời dựa vào đây), chữ trên nhãn và từ khoá tên file.
- **Tự lọc video theo sản phẩm**: chọn thư mục video lẫn lộn, tool nhận ra sản phẩm theo tên file → chữ trên nhãn → AI xem hình, rồi chép (hoặc chuyển) vào thư mục MỚI theo sản phẩm, tên kèm tên đợt (vd `KÍCH RỄ 13-11-2026`); thư mục có sẵn giữ nguyên, trùng tên thì phải đặt tên đợt khác. Không rõ / nhiều sản phẩm → `CẦN XEM`. Edit Video tự dùng cả thư mục cũ và các đợt mới.
- Lọc cảnh kỹ hơn: bỏ cảnh có sản phẩm khác (vd cảnh Nano Đồng lẫn trong thư mục Đạm cá), bắt cả phụ đề nhỏ; AI xem ảnh to hơn; không lặp 1 video trong 4 cảnh liền, không quá 3 cảnh cùng loại liền nhau.
- Giọng **ElevenLabs** (dán API Key, chọn giọng trong tài khoản, mẫu Eleven v3 / Flash v2.5, tốc độ).

## 2.5.2
- Đổi tên thư mục video cho dễ nhận biết (tool tự đổi lúc mở lại sau cập nhật, trước khi bộ đăng chạy):
  - `VIDEO_TIKTOK` → **`SONIX_UP_VIDEO`** (thư mục gốc của Sonix Up Video; Cài đặt tự trỏ sang tên mới).
  - `VIDEO_INPUT` → **`SONIX_EDIT_VIDEO`** (thư mục nguồn của Sonix Edit Video; cảnh đã quét và dự án CapCut do tool tạo tự sửa đường dẫn).
  - Chỉ đổi khi thư mục đang đúng tên cũ. Đang mở thư mục đó trong File Explorer thì có thể chưa đổi được, mở lại tool lần sau sẽ tự thử lại.


## 2.5.2
- Sửa lỗi mất ảnh bìa trong Hàng chờ / Duyệt sau khi lên bản 2.5: bản 2.5.0 đổi tên thư mục SonixDangVideo -> Sonix Auto nhưng hàng chờ vẫn ghi đường dẫn thư mục cũ. Tool tự sửa đường dẫn cũ trong hàng chờ và dữ liệu (ảnh bìa, khung hình, âm thanh Yêu thích, âm thanh mượn) khi mở tool / bật bộ đăng.

## 2.5.1
- Sửa lỗi cửa sổ app hiện "Internal Server Error", không vào được app sau một lúc chạy (máy chủ giao diện mất dấu vòng sự kiện). Nay tool tự sửa ngay khi gặp, không cần tắt mở lại.

## 2.5.0
- App đổi tên chung thành **Sonix Auto**, gồm 2 mục chọn ở trên cùng: **Sonix Up Video** (đăng video như cũ) và **Sonix Edit Video**.
- Cập nhật lên bản này: tool tự đổi tên thư mục `SonixDangVideo` thành `Sonix Auto`, file mở app thành `Sonix Auto.exe`, làm lại biểu tượng ngoài màn hình / menu Start / tự chạy khi mở máy (dữ liệu, đăng nhập, hàng chờ giữ nguyên). Bộ cài mới tên `SonixAuto_Setup_x.y.z.exe`.
- Biểu tượng app, file exe, bộ cài và ảnh cạnh tên app dùng hình mới cố định. Bỏ chức năng tự đổi hình biểu tượng; chức năng đổi ảnh nền trong app giữ nguyên.
- Mục mới **Sonix Edit Video**: viết kịch bản → lồng tiếng → tự chọn cảnh → tạo sẵn dự án CapCut (mở CapCut sửa và xuất 1080p).
  - Kịch bản: AI học cách viết của kênh TikTok tham khảo (dán link video, tool tự tải tiếng và chép lời trên máy), viết lại cho Đạm cá Amino / Kích rễ TC01. Không có AI thì viết theo công thức. Bác sửa lời trước khi lồng tiếng.
  - Lồng tiếng: Vbee (App ID + Token; mặc định Ngọc Huyền 2.0, tốc độ 1.05, thêm giọng theo mã) hoặc giọng miễn phí Microsoft.
  - Cảnh quay: quét thư mục nguồn (D:\VIDEO_INPUT), tự bỏ cảnh có người, chữ/sticker chèn, outro, ảnh tĩnh, sản phẩm khác hãng; AI xếp cảnh sản phẩm / cách dùng / kết quả theo từng câu thoại; mỗi đoạn tự đẩy lên vừa đủ để dải xanh không che sản phẩm; khung 4 ô người dùng.
  - Dự án CapCut chép từ dự án mẫu "mẫu" (khung, chữ, người dẫn, màu, mũi tên); phải tắt CapCut khi tạo.

## 2.4.12
- Duyệt & xác nhận: mục "Thứ tự đăng" cho từng kênh: Theo thứ tự trong thư mục / Xen kẽ sản phẩm / Ngẫu nhiên (không để 2 video cùng sản phẩm liền nhau). Áp dụng khi tool tự xếp lịch, khi bấm Xếp lịch, và khi Xác nhận tất cả ở chế độ đăng ngay.

## 2.4.11
- Mượn âm thanh giữa các kênh: kênh không có âm thanh Yêu thích riêng (vd tài khoản doanh nghiệp Kỹ Thuật Nông Nghiệp Toàn Cầu) tự mượn âm thanh đúng sản phẩm từ kênh khác, ghép sẵn vào video và tắt hẳn âm gốc trước khi đăng.
- Tab Nhạc nền: ô "Cho phép kênh khác dùng" cho từng âm thanh. Mặc định chỉ tick âm thanh của mình / người quen (Toàn Cầu, Nông Dược, Phân Bón Cà Phê, Sơn Phân Thuốc, Nguyên nông dân 81); nhạc, bài hát của người khác không tick.
- Tab Duyệt: ô Nhạc nền có thêm các âm thanh "Mượn · ... (từ kênh ...)" để chọn tay.

## 2.4.10
- Đồng bộ âm thanh Yêu thích: khi mục Yêu thích trong TikTok Studio trống, báo rõ lý do thường gặp (tài khoản doanh nghiệp / gian hàng chỉ hiện nhạc thương mại, âm thanh gốc đã lưu bị ẩn) và cách khắc phục.

## 2.4.9
- Duyệt & xác nhận: công tắc "Đăng ngay khi bấm Xác nhận" cho từng kênh. Bật lên thì video không hẹn giờ: bấm Xác nhận video nào là bộ đăng đăng thẳng video đó lên TikTok, lần lượt từng video. Video phân tích xong của kênh này cũng không tự xếp giờ vàng.

## 2.4.8
- Sửa lỗi "Không tạo được thư mục ... D:\" trên máy không có ổ D: tool gợi ý thư mục gốc theo ổ có thật (ổ D, hoặc ổ đang cài tool), và báo rõ "Máy này không có ổ D:, các ổ đang có: ..." khi nhập sai ổ (cả thư mục trang Facebook).

## 2.4.7
- Cài đặt → Giao diện: chọn "Mở tool bằng: Cửa sổ app riêng / Chrome". Máy nào gõ tiếng Việt có dấu bị lỗi (Unikey/EVKey trong cửa sổ app) thì chọn Chrome.
- Kênh & sản phẩm: trình duyệt kênh đăng nhập tên khác với ô @ tên TikTok (vd gõ thiếu chữ) → hiện cảnh báo + nút "Dùng @tên đang đăng nhập" sửa 1 chạm, rồi Đồng bộ Trưng bày lại.

## 2.4.6
- Tự cập nhật không cần mã đọc GitHub nữa (kho công khai): máy nào cài cũng tự thấy bản mới và cập nhật được.

## 2.4.5
- Sửa lỗi: cập nhật xong đôi khi bộ đăng không tự bật lại (tool tưởng bộ đăng cũ còn chạy).

## 2.4.4
- Cập nhật / Tắt hẳn tool: bộ đăng dừng ngay sau video đang đăng (trước: đăng hết cả hàng chờ rồi mới dừng, cập nhật phải chờ lâu).
- Khởi động lại sau cập nhật chạy ẩn, không hiện cửa sổ đen python.exe nữa.

## 2.4.3
- Sửa lỗi đỏ "st.session_state has no key it_…" ở tab Duyệt: video vừa xác nhận / bỏ mà ô chọn sản phẩm, giờ, nhạc… vẫn gửi lệnh lưu. Nay bỏ qua lặng lẽ.

## 2.4.2
- Sửa lỗi: mở tool bằng biểu tượng (SonixDangVideo.exe) thì cửa sổ app bị ẩn, không thấy gì. Nay cửa sổ luôn hiện ra; bấm biểu tượng lần nữa cũng đưa cửa sổ lên trước.

## 2.4.1
- Đăng video · Bước 1: mỗi kênh là 1 nút bấm (tên + số video mới), bấm để chọn/bỏ chọn; tự chọn sẵn kênh có video mới.
- Nút "Quản lý kênh": thêm kênh mới (tự tạo thư mục), tạm ẩn kênh, xoá kênh khỏi app (thư mục video và đăng nhập vẫn giữ).

## 2.4.0
- Hàng chờ làm mới: chọn theo kênh TikTok / trang Facebook; lọc Sắp đăng / Đã hẹn giờ / Đã đăng / Lỗi; lọc thời gian, tìm theo caption hoặc tên file.
- Video hiện dạng lưới thẻ (5 video/hàng) chia theo ngày: ảnh bìa, trạng thái, giờ, kênh, tên file gốc, caption, sản phẩm; nút ⋯ xem đủ thông tin.
- Khung "Đang đăng": video đang đăng, thanh tiến độ từng bước, thời gian đã chạy, các bước vừa làm (tự cập nhật 2 giây/lần).
- Đăng chạy ẩn (không bật cửa sổ trình duyệt). Công tắc "Hiện trình duyệt khi đăng" ở tab Hàng chờ để bật khi cần xem lỗi.

## 2.3.7
- Sửa lỗi bản 2.3.6: đoạn kiểm tra ảnh bìa cũ bị chép trùng nên tool vẫn chạy cách cũ. Nay chỉ còn cách mới (đọc thẳng file ảnh bìa, bìa không lên thì không đăng).
- Bước đóng gói tự chặn phát hành nếu có hàm trùng tên.

## 2.3.6
- TikTok · Ảnh bìa: kiểm tra bằng cách đọc thẳng file ảnh trong ô bìa (trước: chụp màn hình bị lệch, điểm sai). Đúng bìa ~99 điểm, khung video ~30-55.
- Ảnh bìa không lên → KHÔNG đăng; video giữ ở CHƯA UP, 10 phút sau thử lại; 3 lần vẫn lỗi → 'Cần kiểm tra'.

## 2.3.5
- Kiểm tra ảnh bìa TikTok: không thấy bài đúng giờ hẹn thì tìm tiếp theo mô tả. Bài còn trên TikTok (chỉ khác giờ, hoặc đã đăng) thì sửa lại giờ trong tool, KHÔNG coi là đã xoá → tránh đăng trùng.

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
