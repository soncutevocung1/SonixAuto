# Sonix Auto – Hướng dẫn sử dụng

Tool tự động đăng video TikTok: AI nhận diện sản phẩm trong video, tự gắn giỏ hàng, đặt tên giỏ, chọn ảnh bìa, thêm nhạc, hẹn giờ theo khung giờ vàng. Người dùng chỉ cần duyệt lại và bấm **Xác nhận đăng**.

---

## 1. Cài đặt (làm 1 lần mỗi máy)
1. Giải nén file zip ra một thư mục, ví dụ `D:\Sonix Auto`.
2. Bấm đúp **`1_CAI_DAT.bat`**. Máy chưa có Python thì tool tự cài; cài xong Python thì bấm `1_CAI_DAT.bat` lần nữa.
3. Cài xong, ngoài màn hình (và trong menu Start) có biểu tượng **Sonix Auto** . Từ giờ **bấm đúp biểu tượng là mở tool**, như mở 1 phần mềm:
   - Tool tự bật bộ đăng tự động chạy ngầm, **không hiện cửa sổ đen**.
   - Giao diện mở trong **cửa sổ riêng** (không có thanh địa chỉ như trình duyệt).
   - Đóng cửa sổ giao diện thì bộ đăng **vẫn chạy ngầm**, tới giờ vẫn đăng. Muốn tắt hẳn: bấm **Tắt hẳn tool** ở thanh bên trái.

> Máy cần có **Google Chrome** (hoặc Edge). Mac: chạy `bash cai_dat_mac.sh`, sau đó `bash mo_tool_mac.sh`.

### Cập nhật lên bản mới (máy đã cài rồi)
1. Giải nén file zip mới **đè lên** thư mục cũ (ví dụ `D:\Sonix Auto`), chọn **Thay thế tất cả**. Đăng nhập kênh, cài đặt, hàng chờ nằm trong thư mục `data` nên **không mất**.
2. Bấm đúp **`4_TAO_BIEU_TUONG_APP.bat`** để tạo biểu tượng app.
3. Nếu đang mở bản cũ: tắt các cửa sổ đen cũ đi rồi bấm biểu tượng Sonix Auto.

### Vì sao `http://localhost:8501` không vào được?
- `localhost` nghĩa là **chính máy tính đang chạy tool**. Mở link này trên điện thoại hay máy khác sẽ không được.
- Tool **chưa chạy** (máy vừa khởi động lại, hoặc đã tắt cửa sổ) → bấm biểu tượng Sonix Auto.
- Muốn tool **luôn chạy** sau khi mở máy: Cài đặt → bật **"Tự bật tool (chạy nền) mỗi khi mở máy"**.

### Mở tool trên điện thoại (cùng Wi-Fi với máy tính)
1. Trên máy tính: Cài đặt → bật **"Cho mở tool trên điện thoại"**, đặt **mã PIN** (4-6 số) → **Lưu cài đặt**.
2. Bấm **Tắt hẳn tool**, rồi mở lại biểu tượng. Lần đầu Windows hỏi cho phép mạng → chọn **Cho phép (Allow)**.
3. Thanh bên trái hiện địa chỉ dạng `http://192.168.x.x:8501` → mở địa chỉ đó trên điện thoại, nhập mã PIN.

## 2. Cài đặt ban đầu trong tool
**a) Thư mục và kênh** (tab Đăng video hiện ngay lần đầu)
- Chọn thư mục gốc, ví dụ `D:\SONIX_UP_VIDEO`.
- Nhập các kênh: **tên kênh = tên thư mục**, kèm @ tên TikTok (để tool kiểm tra đúng tài khoản).
- Tool tự tạo:
```
D:\SONIX_UP_VIDEO\
 ├─ NHẠC NỀN\                 ← nhạc .mp3 của bác (không bắt buộc)
 ├─ ẢNH BÌA\                  ← ảnh bìa có sẵn (theme) của bác (không bắt buộc)
 ├─ Sơn Phân Thuốc\
 │   ├─ CHƯA UP\              ← bỏ video chờ đăng vào đây
 │   ├─ ĐÃ UP\                ← đăng xong tool tự chuyển vào
 │   └─ VIDEO LỖI\            ← đăng lỗi tool chuyển vào + file .LOI.txt ghi lý do
 └─ Phân Bón Cà Phê\ ...
```

**b) Đăng nhập TikTok cho từng kênh** (tab Kênh & sản phẩm)
- Mỗi kênh có **1 trình duyệt riêng** (hồ sơ Chrome riêng). Không dùng được các hồ sơ Chrome bác đang có, vì từ Chrome 136 Google chặn phần mềm điều khiển hồ sơ Chrome mặc định. Chỉ cần đăng nhập lại **1 lần**.
- Bấm **Đăng nhập TikTok** → quét mã QR bằng app TikTok → bấm nút vàng **ĐĂNG NHẬP XONG**.
- Bấm **Tạo biểu tượng** để có biểu tượng mở trình duyệt của kênh đó ngoài màn hình (vào Gmail, TikTok bằng tay khi cần).

> **QUAN TRỌNG: Lúc tool đang đăng cho kênh nào thì KHÔNG mở trình duyệt (biểu tượng) của kênh đó.**
> Mở trùng thì tool báo lỗi và **dừng kênh**. Tắt trình duyệt đó đi rồi bấm **"Đã xử lý xong, chạy tiếp"** ở thanh bên trái.

**c) Đồng bộ sản phẩm**
- Bấm **Đồng bộ Trưng bày**. Tool mở trang đăng bằng một video đen 3 giây (không đăng gì) và đọc hết danh sách sản phẩm trưng bày.
- Ở mục **Ghép sản phẩm**: kiểm tra mỗi sản phẩm cần nhận diện đã được ghép đúng ID chưa. Có 2 giỏ hàng thì sẽ thấy 2 ID; để cả 2 thì tool gắn cả 2.
- Sửa **tên giỏ mẫu** (tối đa 30 ký tự) → **Lưu ghép sản phẩm**. Lần sau kênh đó tự dùng tên này.

**d) Nhạc nền: không cần chuẩn bị gì**
- Mặc định tool **tự chọn nhạc TikTok lúc đăng**:
  - video **có giỏ** → lấy bài trong mục **"Không giới hạn"** (kho nhạc thương mại TikTok cho dùng để bán hàng, ít bị tắt tiếng vì bản quyền);
  - video **không giỏ** (video kiến thức) → lấy bài trong mục **"Đề xuất"** (TikTok gợi ý, hay theo xu hướng).
- Tool chọn ngẫu nhiên 1 trong 3 bài đầu nên các video không trùng nhạc nhau. Tool bỏ qua bài "original sound" vì đó thường là giọng nói người khác.
- Nhạc được hạ xuống **-14 dB** để nghe rõ giọng bác (chỉnh ở Cài đặt → Nhạc nền TikTok).
- Muốn tìm nhạc theo từ khoá (ví dụ "nhạc quê hương"): sửa ô **Từ khoá tìm nhạc** ở , rồi chọn "Tự động: tìm nhạc ..." cho video.
- Bài nào được chọn sẽ ghi ở cột **Kết quả** (tab Hàng chờ). Thêm nhạc lỗi thì tool vẫn đăng video (không nhạc), không bị dừng.
- (Không bắt buộc) Có lưu nhạc vào mục **Yêu thích** trên app TikTok thì bấm **Đồng bộ âm thanh Yêu thích** để chọn đúng bài đó.

**e) Claude API key** (tab Cài đặt). Cần có để AI nhận diện sản phẩm và viết caption.
1. Vào **https://console.anthropic.com** → đăng nhập bằng Gmail.
2. **Billing** (thanh toán) → **Buy credits** (nạp tiền) → nạp **5 USD** (khoảng 130.000đ) bằng Visa/Mastercard. Nên đặt **Spend limit** (giới hạn chi tiêu) khoảng 10 USD/tháng.
3. **API Keys** → **Create Key** → đặt tên `SonixAuto` → **Copy**. Key bắt đầu bằng `sk-ant-` và chỉ hiện 1 lần.
4. Dán vào tab Cài đặt → **Lưu cài đặt**.
- Không gửi key cho ai, không dán vào chat.
- Không có key thì tool nhận diện theo **tên file** (ví dụ file tên có chữ `tc01`, `dam ca 5 lit`) và dùng caption mẫu.

**f) (Không bắt buộc) Gemini API key — AI miễn phí của Google** (tab Cài đặt)
- Gói Gemini trong app chat **không dùng được cho tool**. Cần lấy **Gemini API key** riêng, miễn phí, không cần thẻ:
  vào **https://aistudio.google.com/apikey** → đăng nhập Gmail → **Create API key** → Copy (bắt đầu bằng `AIza`) → dán vào ô **Gemini API key** → **Lưu cài đặt** → Mức AI mặc định chọn **Gemini 3.5 Flash-Lite**.
- Lưu ý gói miễn phí: Google giới hạn **số lượt mỗi phút/mỗi ngày** (hết lượt thì có lại sau khoảng 14-15 giờ chiều giờ VN), và **Google được dùng ảnh khung hình gửi lên để cải thiện sản phẩm của họ**.

**g) Âm thanh Yêu thích đúng sản phẩm (video tắt tiếng gốc + giọng aff khác)**
- Trên app TikTok, bấm lưu (Yêu thích) các âm thanh hay nói về sản phẩm của bác.
- Tab **Nhạc nền** → kênh đó → **Đồng bộ Yêu thích**. Tool tải **trọn bài** về để nghe thử, rồi **nghe lời nói** (bộ nghe Whisper chạy trên máy, miễn phí) và **tự gắn sản phẩm** khi nghe thấy tên sản phẩm. Đoạn nào không nghe rõ tên thì AI (mức AI mặc định) đọc đoạn chữ để đoán.
- Bác **nghe thử từng âm thanh**, sửa ô *Âm thanh này nói về* nếu sai, tick *Không dùng* với âm thanh không liên quan.
- **Tool tự gắn sẵn** ở tab Duyệt: video nào có sản phẩm đã có âm thanh Yêu thích nói về nó thì tool gắn luôn âm thanh đó và **tắt âm gốc** (xoay vòng cho các video đỡ trùng). Đổi sản phẩm thì âm thanh đổi theo.
- Bác nghe thử ở từng video. Không ưng thì bấm **Bài khác**, hoặc chọn bài khác ở ô *Nhạc nền*: bài bác tự chọn thì tool để nguyên, không tự đổi nữa.
- Không muốn tự gắn: Cài đặt → Nhạc nền TikTok → tắt **Tự gắn âm thanh Yêu thích đúng sản phẩm khi duyệt**.

**h) Hướng dẫn AI viết caption** (tab Cài đặt → )
- Ghi phong cách bác muốn (số dòng, câu mở đầu, có emoji không, cách kêu gọi...) và **độ dài tối đa** (mặc định 150 ký tự).
- Có thể ghi thêm hướng dẫn riêng cho từng kênh. AI ưu tiên làm theo hướng dẫn này.

## 3. Đăng video hằng ngày
1. Chép video vào `CHƯA UP` của từng kênh.
2. Tab **Đăng video**:
   - Tick các kênh.
   - **Chọn mức AI**:
     - Opus: tốt nhất, khoảng 1.300đ/video.
     - Sonnet: khoảng 650đ/video.
     - Haiku: khoảng 50đ/video. **Khuyên dùng**: đọc rõ chữ trên nhãn chai/can, đủ để tự gắn giỏ.
     - Gemini 3.5 Flash-Lite / 3.8 Flash: **miễn phí** (cần Gemini API key, xem mục f), giới hạn lượt mỗi ngày.
     - Không dùng AI.
   - Bấm **Phân tích**. Tool cắt 10 khung hình mỗi video, AI tìm khung thấy rõ sản phẩm nhất (ưu tiên khung có người cầm sản phẩm) làm ảnh bìa, nhận diện sản phẩm, viết caption, hashtag, rồi tự xếp lịch theo giờ vàng.
   - Phân tích **chạy ngầm**: tiến độ hiện ở thanh bên trái ("Đang phân tích ngầm: còn X video"). Bác cứ làm việc khác, bấm 2 lần hay tắt cửa sổ cũng không sao, mở lại tool sẽ phân tích tiếp. Video đang phân tích **không tính** vào "video mới trong CHƯA UP".
3. Tab **Duyệt & xác nhận**:
   - ≥80% · 60-79% · dưới 60%. Video phải tick **"Tôi đã kiểm tra"** mới được đăng.
   - Sửa từng video: sản phẩm, ID gắn (2 giỏ trùng thì gắn cả 2), tên giỏ, caption, giờ đăng, nhạc nền (tự động / Yêu thích / nhạc trên máy), người xem, **Đổi ảnh bìa**.
   - **Thao tác hàng loạt**: tick nhiều video rồi:
     - gắn cùng một sản phẩm;
     - chỉ giữ giỏ 1 hoặc giỏ 2, hay gắn đủ cả 2 giỏ;
     - đổi nhạc hoặc người xem;
     - **Tắt âm gốc / Giữ âm gốc** (tắt trên bản sao lúc đăng, video trong máy giữ nguyên; mặc định video mới tắt âm gốc, đổi ở Cài đặt);
     - **Gán âm thanh Yêu thích đúng sản phẩm**;
     - **Viết lại caption** theo *Hướng dẫn AI viết caption* (Cài đặt), giữ nguyên sản phẩm, ảnh bìa, giờ đăng;
     - đánh dấu đã kiểm tra.
   - **Ảnh bìa có sẵn (theme)**: bỏ ảnh bìa bác làm sẵn (jpg, png, webp; nên làm khung dọc 9:16, ví dụ trên Canva) vào thư mục `ẢNH BÌA`, hoặc tải lên ngay trong tab Duyệt:
     - từng video: **Đổi ảnh bìa** → chọn ảnh trong thư viện → **Dùng ảnh này**, hoặc tải ảnh lên là dùng luôn cho video đó;
     - hàng loạt: tick các video → chọn ảnh ở ô **Ảnh bìa có sẵn** → **Áp dụng ảnh bìa**.
     Ảnh lệch khung video thì tool đặt nguyên ảnh ở giữa trên nền mờ, không cắt mất chữ. Lúc đăng tool tự tải ảnh này lên làm bìa TikTok.
   - **Xếp lịch tự động**: số video/ngày, khoảng cách tối thiểu, khung giờ đăng (**lưu riêng cho từng kênh**, lần sau tự điền sẵn; giờ vàng nằm ngoài khung 'Đăng từ - Đến' sẽ không dùng). Ưu tiên giờ vàng, và có thể tăng "số video mỗi khung giờ vàng" để dồn nhiều video vào giờ vàng.
   - Bấm **Xác nhận đăng**.
4. Bộ đăng tự động mở đúng trình duyệt của kênh, kiểm tra đúng tài khoản @, rồi:
   - tải video lên → gõ mô tả → đặt ảnh bìa → gắn giỏ hàng (Thêm liên kết → Sản phẩm → Trưng bày → đặt tên → Thêm) → chọn nhạc → người xem → **Khai báo nội dung bài đăng: tự tick "Thương hiệu của bạn"** (đổi mặc định ở Cài đặt) → **Lên lịch** đúng giờ;
   - xong thì chuyển file sang `ĐÃ UP`.
   - TikTok giữ lịch hẹn nên **tắt máy sau đó cũng được** (hẹn trước được hơn 3 tuần; giờ hẹn đi theo bước 5 phút).

## 4. Lần đầu dùng: chạy thử an toàn
- Trong Duyệt, chọn **Người xem = Chỉ mình tôi (đăng thử)** cho 1-2 video. Lưu ý: TikTok **không cho hẹn giờ video "Chỉ mình tôi"**, nên video riêng tư sẽ được đăng ngay khi tới lượt.
- Mặc định **duyệt trong tab là đủ**: tool tự bấm Đăng/Lên lịch, không hỏi lại. Muốn xem lại từng video trên TikTok trước khi đăng thì bật **"Dừng trên TikTok cho tôi xem lại trước khi bấm Đăng"** (tab ), tool sẽ chờ bác bấm nút vàng **ĐĂNG LUÔN**.
- **Đăng nhanh** (tab , bật sẵn): mỗi video khoảng 1 phút, nghỉ 10-25 giây giữa 2 video (chỉnh được). Thấy tool hay bấm hụt thì tắt Đăng nhanh.
- Bước nào tool chưa tự làm được (TikTok đổi giao diện), trang hiện **thanh xanh** nhờ bác làm tay bước đó rồi bấm **TIẾP TỤC**. Tool không bỏ dở.

## 5. Khi có lỗi
- Video lỗi nằm trong `VIDEO LỖI` kèm file `.LOI.txt`. Sửa xong, vào tab Hàng chờ → tick → **Cho chạy lại** (tool tự chuyển video về `CHƯA UP`).
- TikTok đổi giao diện làm tool bấm sai:
  1. Tab → **Chụp giao diện**.
  2. Tab Nhật ký → **Tải gói báo cáo lỗi**.
  3. Gửi file đó cho người hỗ trợ. Gói này không chứa mật khẩu, token hay key.

## 6. Chia sẻ cho người khác
- Bấm **`3_DONG_GOI_CHIA_SE.bat`** → ra file `SonixAuto_ngày.zip`.
- Gói này **không chứa thư mục `data`** (đăng nhập TikTok, API key, token Facebook).
- Người nhận giải nén → `1_CAI_DAT.bat` → tự nhập kênh của họ.
- Tuyệt đối không gửi thư mục `data` cho ai.

## 7. Facebook
Giữ nguyên như bản cũ (tab Facebook): đăng lên Trang qua API chính thức, Facebook tự hẹn giờ. Cần Page ID + Page Access Token, lấy như sau:
1. Vào developers.facebook.com → tạo app loại Business.
2. Mở Graph API Explorer → Get User Access Token, tick các quyền `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `publish_video`.
3. Gõ truy vấn `me/accounts` → lấy `id` (Page ID) và `access_token` (token của Trang).
4. Muốn token dùng lâu: gia hạn token ở Access Token Debugger trước khi làm bước 3.

## 8. Giao diện, tổng hợp theo ngày, ảnh bìa mặc định
- **Sáng / tối**: nút *Chuyển giao diện tối/sáng* ở thanh bên trái. Mở app lên mặc định là **sáng**.
- **Mẫu nền và kiểu khung**: tab Cài đặt → **Giao diện**. Có 7 mẫu nền (Xanh dương – tím, Đại dương, Hoàng hôn, Đồng lúa, Đêm tím, Trơn, Ảnh của bác) và 3 kiểu khung (Kính mờ, Trong suốt, Mặc định). Chọn *Ảnh của bác* thì tải 1 ảnh lên và kéo *Độ mờ ảnh nền*. Đổi là thấy ngay.
- **Hôm nay** (thanh bên trái): Chờ duyệt, Chờ đăng (số đang có) và Đã hẹn giờ, Lỗi (tính từ 0:00 hôm nay, sang ngày mới tự về 0). Bấm *Chờ duyệt / Chờ đăng / Đã hẹn giờ / Lỗi* để xem từng kênh hoặc từng sản phẩm.
- **Tab Tổng hợp**: chọn ngày bất kỳ để xem lại số video đã phân tích, đã xác nhận, đã hẹn giờ/đăng, lỗi theo từng kênh và từng sản phẩm, kèm biểu đồ 7 ngày.
- **Ảnh bìa mặc định theo sản phẩm**: tab Duyệt & xác nhận → mục *Ảnh bìa mặc định theo sản phẩm* → chọn 1 ảnh cho mỗi sản phẩm. Video của sản phẩm đó (bác chưa tự chọn bìa) tự dùng ảnh này; đổi sản phẩm thì bìa đổi theo.
- **Ảnh bìa đúng màu**: video iPhone (HDR) được chuyển màu chuẩn khi cắt ảnh bìa, không còn bị nhạt, bệt.
