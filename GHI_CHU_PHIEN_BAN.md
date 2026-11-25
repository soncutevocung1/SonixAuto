# Ghi chú phiên bản Sonix Auto


## 2.12.9
- Kênh & sản phẩm > *Shop của từng sản phẩm*: bảng có **ảnh nhỏ** của từng sản phẩm, cột Shop đưa lên đầu (bấm để chọn), ô chưa chọn ghi "Chưa chọn", mã rút gọn 6 số cuối.

## 2.12.8 · Chọn đúng mã sản phẩm, chọn shop
- Bước duyệt: sản phẩm hiện thành **thẻ có ảnh** (như Trưng bày) kèm giá, tồn kho, shop, 6 số cuối mã. Bấm **Gắn mã này** để gắn / bỏ.
- **Chọn shop**: nút *Shop A / Shop B / Cả 2 shop* cho từng video, và trong *Chọn shop / giỏ* khi làm hàng loạt. Ghi shop cho từng sản phẩm 1 lần ở tab Kênh & sản phẩm > *Shop của từng sản phẩm*.
- Gắn từ 2 sản phẩm trở lên thì app nhắc: TikTok chỉ hiện 1 giỏ trên video, nên gắn 1 mã.
- Tự phát hiện khi TikTok **tạm khoá quyền gắn sản phẩm** của kênh (Account restricted): báo đỏ ở bước duyệt và tab Kênh, kèm giờ hết khoá; lúc đăng báo lỗi rõ thay vì "không thấy sản phẩm".

## 2.12.7
- Tab Edit: **Quét cảnh** (AI xem cảnh có người, chữ chèn, cảnh phun/rót/pha), **Tự lọc video theo sản phẩm** và nhận sản phẩm video xoay giờ cũng dùng **AI viết kịch bản (riêng tab Edit)**, ví dụ Claude Haiku, như trước đây. Không còn phụ thuộc Cài đặt chung của Up Video (đang Không dùng AI thì Edit vẫn chạy AI).

## 2.12.6 · Edit Video: chọn Claude viết kịch bản
- Ô mới **AI viết kịch bản (riêng tab Edit)** ở mục 1. Kịch bản: chọn **Claude Haiku 5.5** (như cũ, rẻ) hoặc **Claude Sonnet 5.5** (viết hay hơn, đắt hơn), hoặc *Theo Cài đặt chung* (Gemini / không AI). Dùng cho viết kịch bản, làm hàng loạt, phân tích kênh tham khảo, học phong cách. Đăng video (Up Video) vẫn theo Cài đặt chung.
- Chọn Claude mà máy chưa có mã thì có ô dán **Claude API key** ngay bên cạnh.

## 2.12.5
- Edit Video, **Làm hàng loạt**: nút bị mờ vì app đang ở chế độ *Không dùng AI* thì nay hiện rõ lý do và cách sửa (dán Gemini API key miễn phí ở tab Cài đặt, chọn mức AI Gemini). Thiếu lời / cảnh / khuôn cũng ghi rõ.

## 2.12.4
- Bước 1 (tab Đăng video): mỗi kênh có lựa chọn **Tất cả · Số lượng · Chọn video**: phân tích hết, chỉ N video đầu (theo tên file), hoặc tự chọn từng video. Video không chọn vẫn nằm trong CHƯA UP cho lần sau.

## 2.12.3
- Sửa lỗi **ngày đặt 6 video mà chỉ đăng 4** và **2 video trùng giờ**: bỏ / xoá video khỏi danh sách duyệt sau khi đã xếp lịch để lại chỗ trống; video "Phân tích lại" bị bỏ qua khi xếp giờ cho video mới nên trùng giờ. Nay bỏ / xoá video thì tool **dồn các video chờ duyệt còn lại lên lấp chỗ trống**, bấm Xác nhận cũng dồn lại (lấp chỗ trống, bỏ giờ trùng, giờ đã qua dời sang khung trống), không kéo sớm hơn ngày bác đã chọn bắt đầu. Video bác tự sửa giờ thì giữ nguyên.

## 2.12.2
- Nút **Mượn âm thanh của «kênh khác»** luôn hiện trong nhóm Âm thanh (trước đây bị ẩn khi đang hiện thông báo gán âm thanh). Gán không được vì kênh khác chưa cho mượn thì báo rõ "bấm nút Mượn âm thanh".

## 2.12.1
- Kênh **không có âm thanh Yêu thích riêng** (vd KTNN): ngay trong nhóm **Âm thanh** của tab Duyệt có thông báo đang mượn được bao nhiêu âm thanh và nút **Mượn N âm thanh của «kênh khác»** (cho mượn tất cả âm thanh đã gắn sản phẩm của kênh đó). Bấm xong chọn «Tự động: âm thanh Yêu thích đúng sản phẩm» → Áp dụng nhạc.

## 2.12.0
- **Giao diện gọn và nhiều màu hơn**: bỏ mục Giao diện trong Cài đặt (mẫu nền, kiểu khung, ảnh nền, sáng/tối). Sáng/tối bấm ở thanh bên trái; "Mở tool bằng" (cửa sổ app / Chrome) chuyển ra nút **Mở** cạnh nút sáng/tối. Nền cố định nhiều màu nhẹ; **mỗi tab một màu riêng** (tab đang mở tô màu, tab khác có gạch màu).
- **Thao tác hàng loạt** (tab Duyệt) xếp lại theo nhóm có màu: Thứ tự đăng · Sản phẩm & giỏ · Âm thanh · Người xem · Ảnh bìa · AI. Gộp nút trùng: 3 nút giữ giỏ gom vào **Giỏ trùng 2 sản phẩm**, thêm/bỏ ảnh theme gom vào **Thư viện ảnh bìa**, Tắt/Giữ âm gốc và Người xem thành nút chọn bấm là áp dụng ngay.
- **Lựa chọn đang dùng được tô màu** (thứ tự đăng, âm gốc, người xem của các video đang chọn, Chọn tất cả khi đã chọn hết); nút chưa bấm được (chưa chọn video) mờ đi.

## 2.11.1
- Sửa lỗi **Gemini "không trả lời (có thể bị chặn nội dung)"** làm caption video nào cũng giống nhau (dùng caption mẫu): Google đổi cách trả kết quả, tool đọc theo cách mới.
- **Bỏ Claude Haiku**: chỉ còn Gemini (miễn phí) và Không dùng AI. Máy đang chọn Haiku tự chuyển sang Gemini (có Gemini key) hoặc Không dùng AI.
- **Caption ngắn, không lặp**: 2-3 dòng ngắn; mỗi video được giao 1 "góc viết" khác nhau (hỏi nỗi lo, kể cảnh vườn, mẹo nhanh, cảnh báo sai lầm, thời điểm dùng...) và AI được xem các caption gần đây của kênh để không lặp câu mở đầu / ý.

## 2.11.0
- **Bỏ Opus và Sonnet** (tốn tiền). Mức AI còn: **Gemini Flash-Lite / Flash (miễn phí, khuyên dùng)**, Claude Haiku (trả phí rẻ), Không dùng AI. Máy đang chọn Opus/Sonnet tự chuyển sang Gemini (nếu có Gemini key) hoặc Haiku.
- **Nhận diện sản phẩm miễn phí, không cần mạng**: tool **đọc chữ trên nhãn** trong video (TC01, Kích rễ, Top One, Đạm cá Amino, 1 lít / 5 lít...) bằng máy đọc chữ có sẵn trên máy, chọn luôn khung thấy nhãn rõ nhất làm ảnh bìa. Chế độ "Không dùng AI" giờ nhận được sản phẩm theo nhãn chứ không chỉ theo tên file. Khi dùng Gemini/Haiku: nhãn đọc rõ thì sản phẩm được chốt theo nhãn, AI chỉ còn viết caption (chính xác hơn).
- **Caption hay hơn**: AI được đưa thêm **Thông tin sản phẩm** (thành phần, công dụng, cách pha, điền ở Sonix Edit Video) để viết đúng, kể theo kiểu vấn đề → sản phẩm giúp gì → cách dùng, mỗi video viết khác nhau. Caption mẫu (không AI) cũng lấy câu công dụng từ thông tin sản phẩm.

## 2.10.14 · Lọc kỹ cảnh phun / rót / pha + Xoay minh họa chèn đẹp hơn
- **Lọc lại cảnh phun, tưới, rót, pha**: AI xem kỹ từng cảnh (3 khung đầu - giữa - cuối). Cảnh không thật sự đang rót / pha / phun / tưới (chỉ cầm chai, cận nhãn, kệ hàng...) thì đổi loại; cảnh có người hoặc sản phẩm khác thì bỏ. Quét cảnh video mới cũng tự soát bước này.
- **Xoay minh họa**: đoạn chèn vẫn tua nhanh 2x, tắt tiếng; nay **ưu tiên cảnh sử dụng** (phun, tưới, rót, pha), **không chèn lẻ cảnh có người**; đủ 4 video có người thì ghép **1 khung chia 4 ô nhiều người dùng**. Chỉ lấy cảnh AI đã xem (tránh lọt người, khung bình luận chèn chữ).

## 2.10.13 · Reup Aff: nhiều cảnh phun, tưới, rót, pha hơn
- Khi chọn cảnh, tool ưu tiên cảnh **phun, tưới, rót sản phẩm ra, pha vào bình / thùng**: khoảng 45% số cảnh mỗi video (trước đây chỉ 0-3 cảnh / video). Vẫn xen cảnh sản phẩm và kết quả trên cây, không để toàn cảnh pha liền nhau.

## 2.10.12 · Lịch đăng không còn ngày dư / ngày thiếu
- Sửa lỗi lịch có ngày **dư 1 video, ngày khác thiếu 1 video**: xảy ra khi bác bấm xếp lại lịch đúng lúc bộ đăng đang đẩy 1 video lên TikTok với giờ cũ (vd 11:30 giờ vàng của cài đặt cũ). Nay mỗi lần hẹn giờ xong 1 video, tool tự kiểm tra: ngày nào dư so với số video/ngày đã đặt thì dời video dư (chưa lên TikTok) sang khung giờ trống kế tiếp. Video đã hẹn trên TikTok giữ nguyên.

## 2.10.11 · Sửa lỗi AI không nhận được sản phẩm
- Sửa lỗi **"AI lỗi (NameError: name 'sys' is not defined) → dùng cách dự phòng"** làm video không gắn được sản phẩm / giỏ hàng. Nguyên nhân: mỗi khi có file trong thư mục app thay đổi (cập nhật tự động, sửa code), giao diện tự nạp lại code và gỡ nhầm cả phần lõi của Python đi kèm, nên lần AI phân tích sau bị hỏng. Nay tắt việc tự nạp lại này (cập nhật xong app vẫn tự khởi động lại như cũ).
- Video đã bị lỗi này: bấm **Phân tích lại** (hoặc chọn sản phẩm tay) sau khi app khởi động lại.

## 2.10.10 · Edit Video: 1 kênh chung, bỏ file đếm số
- **Kênh nhận video** ở Edit Video (Reup Aff) giờ là **1 kênh chung cho mọi sản phẩm**. Trước đây app nhớ kênh riêng từng sản phẩm, nên đổi từ Kích rễ sang Đạm cá là lặng lẽ đổi sang kênh khác (vd đang Sơn Phân Thuốc nhảy sang Mai Vàng Farm).
- Video làm trong cùng ngày luôn vào chung `CHƯA UP\<ngày>` của kênh, đánh số nối tiếp (01, 02... rồi 06, 07...), dù làm nhiều lần, nhiều sản phẩm.
- Bỏ file đếm số `.sonix_so_thu_tu` trong thư mục ngày. Số tiếp theo tính từ video đang có trong thư mục + lịch sử đăng (video đã đăng chuyển sang ĐÃ UP vẫn không bị trùng số).

## 2.10.8
- **Thứ tự đăng** (theo thư mục / xen kẽ sản phẩm / ngẫu nhiên) chuyển vào khung **Thao tác hàng loạt** cho dễ thấy. Đổi là tool **xếp lại ngay** các video chờ duyệt (giữ nguyên các khung giờ, chỉ đổi video nào đăng giờ nào), không cần bấm Xếp lịch. Chế độ ngẫu nhiên có nút **Xáo lại**.
- Sửa chế độ ngẫu nhiên đôi khi để 2 video cùng sản phẩm liền nhau ở cuối lịch: nay không bao giờ liền nhau (trừ khi 1 sản phẩm chiếm quá nửa số video, không thể xen kẽ hết).

## 2.10.7
- Bảng **Xếp lịch tự động** hiện thêm số video **đã hẹn sẵn** trong từng ngày (và giờ của chúng), cột **Tổng / ngày** so với số video/ngày đã đặt. Trước đây bảng chỉ hiện video mới nên nhìn tưởng tool tách sai ngày (số video/ngày luôn tính cả video đã hẹn sẵn trên TikTok).

## 2.10.6
- Kênh **không đồng bộ được âm thanh Yêu thích** (báo lỗi #1119093737, kênh Trinh đạm cá): TikTok Studio trên web chỉ hiện nhạc thương mại với tài khoản doanh nghiệp **và cả tài khoản cá nhân có bán hàng / trưng bày sản phẩm**, âm thanh gốc đã lưu bị ẩn. Câu báo lỗi giờ nói đúng và chỉ cách dùng. Tab Nhạc nền có nút **Cho kênh khác mượn tất cả** (bấm 1 lần cho cả kênh có âm thanh), kênh trống được mượn âm thanh đúng sản phẩm, ghép vào video và tắt âm gốc.

## 2.10.5
- **Chrome của kênh chạy ẩn khi đăng**: tới lượt đăng mà cửa sổ Chrome của kênh chưa mở, tool mở Chrome **chạy ẩn** (không hiện lên màn hình, không giành chuột/bàn phím), đăng xong vẫn để chạy ẩn cho lần sau nhanh. Bấm **Mở Chrome của kênh** hoặc **Đăng nhập TikTok** thì tool tắt bản ẩn và mở cửa sổ hiện lên để bác thao tác. Muốn xem tool đăng thì bật **Hiện trình duyệt khi đăng** ở tab Hàng chờ. Cửa sổ bác đang mở sẵn thì tool vẫn dùng cửa sổ đó.

## 2.10.4
- Sửa lỗi **đăng bằng Chrome của kênh báo "Locator.set_input_files: Timeout"**: video lớn bị gửi cả nội dung qua đường điều khiển nên treo. Nay Chrome tự đọc file video / ảnh bìa thẳng từ ổ đĩa (200 MB chưa tới 1 giây). Video đã lỗi vì chuyện này: vào Hàng chờ → Lỗi, chọn rồi bấm Chạy lại.

## 2.10.3
- Sửa lỗi **phân tích AI chạy trùng 2 lần cùng lúc** (tốn tiền AI gấp đôi, có lúc báo lỗi "name 'sys' is not defined" / "module 'anthropic' has no attribute" khiến video không nhận ra sản phẩm và không gắn giỏ): nay chỉ 1 luồng phân tích được chạy.

## 2.10.2 · Xoay minh họa: làm theo sản phẩm
- Phong cách **Xoay minh họa** làm video **theo sản phẩm bác chọn**, không làm lần lượt theo thứ tự nữa (tránh ra toàn video Đạm cá hoặc toàn Kích rễ).
- Trong `SOURCE THÔ\Xoay` tool tạo sẵn 1 thư mục cho mỗi sản phẩm (ĐẠM CÁ, KÍCH RỄ, NANO ĐỒNG, CANXI BO, SIÊU BÁM DÍNH, BỌ TRĨ TOP ONE). Bác bỏ video xoay vào đúng thư mục sản phẩm; tên thư mục kiểu `Dam_Ca`, `Kich_Re` cũng nhận được.
- Chọn sản phẩm sẽ thấy số video gốc **chưa làm / tổng**. Hết video gốc thì app báo **quay thêm và bỏ vào thư mục** của sản phẩm đó (có nút Mở thư mục này), hoặc tick *Làm lại video đã làm*.
- Video để ngoài, chưa vào thư mục sản phẩm nào: app báo để bác kéo vào đúng thư mục.

## 2.10.1 · Tự xuất video vào CHƯA UP chạy được lại
- Sửa hẳn lỗi **tự xuất từ CapCut không ra video trong CHƯA UP** (đã chạy thử trọn vẹn: mở dự án, xuất 1080p, đưa vào `CHƯA UP\<ngày>\01.mp4`):
  - Chữ "Xuất" trên nút xanh của hộp Xuất không đọc được, tool bấm nhầm nút "Xuất" ở thanh trên cùng nên CapCut không xuất. Nay bấm đúng nút trong hộp.
  - CapCut hiện thêm thông báo nhỏ ("Chức năng chỉnh sửa đang chậm...") cùng tên cửa sổ, tool từng lấy nhầm thông báo đó làm cửa sổ chính. Nay luôn lấy cửa sổ chính.
  - Tìm file vừa xuất theo đúng ô "Xuất sang" của CapCut (kể cả khi chữ đọc được bị mất dấu, sai vài ký tự hoặc bị cắt "...").

## 2.10.0
- **Đăng bằng Chrome của kênh**: mỗi kênh 1 cửa sổ **Chrome thật** (hồ sơ riêng của kênh, đã có sẵn đăng nhập), mở 1 lần rồi để đó. Bộ đăng gắn vào cửa sổ đang mở, mỗi video mở 1 tab rồi đóng tab, **không mở/tắt trình duyệt mới liên tục** nữa. Bác đăng nhập, xác minh, xem bài ngay trong cửa sổ đó. Cửa sổ chưa mở thì tool tự mở. Tab **Kênh & sản phẩm** có công tắc bật/tắt (tắt = cách cũ) và nút **Mở Chrome của kênh** cho từng kênh. Bấm **Tạo biểu tượng** lại 1 lần để biểu tượng ngoài màn hình mở đúng cửa sổ tool gắn vào được.

## 2.9.3 · Nhãn chữ tuỳ chỉnh + tự xuất chắc hơn
- Ô **Nhãn chữ nhỏ nền vàng** (dưới ô Tiêu đề, Edit Video): khuôn đang ghi "phân bón chính hãng". Xoá trống để **bỏ hẳn nhãn**, hoặc gõ chữ khác. Chọn áp dụng cho **mọi video mới về sau** (cả làm hàng loạt) hoặc **chỉ video này** (AI viết kịch bản mới thì quay về mặc định).
- Tự xuất CapCut: tool **chờ bác rời chuột / bàn phím 20 giây** rồi mới bắt đầu xuất từng video (đang dùng máy thì tool bấm nhầm cửa sổ), và ép cửa sổ CapCut lên trên cùng trước mỗi lần chụp / bấm.

## 2.9.2
- Sửa lỗi **không đồng bộ được Trưng bày sản phẩm / âm thanh / đăng video ở tài khoản mới** (kênh Mai Vàng Farm): sau khi tải video, TikTok hiện hộp "Bật kiểm tra nội dung tự động?" che hết các nút. Nay tool tự bấm **Bật** hộp này rồi làm tiếp.

## 2.9.1 · Sửa tự xuất video + tham khảo content kênh khác
- Sửa lỗi **không tự xuất video vào CHƯA UP**: CapCut bản mới làm tool đọc sai chữ nút "Thùng rác" nên không tìm được ô tìm dự án. Nay tool tìm theo chữ "Dự án" + vị trí cố định. Tool cũng tìm file vừa xuất trong cả thư mục con (ô "Xuất sang" của CapCut hay bị cắt "..."), tự bấm lại nút Xuất nếu chưa thấy bắt đầu, và luôn đưa CapCut lên trước khi bấm.
- Mục **Tham khảo content kênh khác** (ở bước viết kịch bản): dán link kênh TikTok hoặc link từng video. App tải tiếng, chép lời rồi cho AI **phân tích dạng content** (cách giật tít, dẫn dắt, chốt, kiểu tiêu đề). Tick kênh nào thì AI học theo kênh đó khi viết (cả làm hàng loạt), có nút Phân tích lại và xem kết quả phân tích.
- Ô **Tiêu đề mẫu**: gõ vài tiêu đề bác thích, AI đặt tiêu đề theo kiểu đó (vẫn 3 dòng, dòng 1 tô vàng).
- Reup Aff **ghép nhiều cảnh hơn**: thêm thanh **Độ dài mỗi cảnh** (mặc định 1,2 giây thay cho 1,8 giây, video ~35 giây từ ~27 lên ~34 cảnh; kéo xuống 0,8 giây được ~49 cảnh).

## 2.9.0
- Sửa lỗi **ảnh bìa và âm thanh sai sản phẩm** (báo lỗi #1116095332): đổi giỏ hàng của video (vd sang Kích rễ TC01) trước đây không đổi "sản phẩm của video", nên ảnh bìa theme và âm thanh Yêu thích vẫn theo sản phẩm cũ (Bọ trĩ). Nay đổi giỏ là sản phẩm đổi theo; tab Duyệt và bộ đăng (ngay trước khi đăng) tự kiểm: ảnh bìa theme của sản phẩm khác → đổi sang ảnh đúng sản phẩm (không có thì về bìa AI chọn); âm thanh Yêu thích của sản phẩm khác → đổi âm thanh đúng sản phẩm (không có thì nhạc mặc định). Video đang chờ đăng cũng được sửa trước khi lên TikTok.
- Sửa lỗi **đồng bộ Trưng bày / tải video báo TimeoutError "input[type=file]"**: tool tìm ô chọn video cả trong khung con, tự tắt hộp thông báo và bấm nút Chọn video; vẫn không được thì báo rõ lý do (chưa đăng nhập, TikTok đòi xác minh...) kèm chữ trên trang, thay vì lỗi kỹ thuật.
- Gói báo lỗi không còn che nhầm mã sản phẩm và từ khoá (chỉ che token, khoá AI, mật khẩu).

## 2.8.9
- **Dời video trễ lịch về hôm nay**: video TikTok chưa đăng mà giờ hẹn đã qua (tạm dừng, chờ đăng, chờ duyệt) hiện khung cảnh báo trên đầu app, bấm **Dời về lịch từ hôm nay** để xếp lại vào khung giờ trống từ bây giờ (giữ đúng số video/ngày). Tab Hàng chờ cũng có nút này cho video đang chọn. Video tạm dừng vẫn tạm dừng, bấm Chạy lại khi muốn đăng.
- Lỗi "Đã bấm đăng nhưng chưa thấy TikTok xác nhận": tool ghi lại **đúng câu TikTok báo** (thông báo nhanh trên màn hình + phản hồi máy chủ) vào kết quả video và nhật ký, để biết chính xác vì sao TikTok không nhận.

## 2.8.8
- Sửa lỗi video báo **"Đã bấm đăng nhưng chưa thấy TikTok xác nhận"** (gặp ở kênh KTNN 14/11, cứ 1 video được 1 video lỗi): TikTok đôi khi không nhận cú bấm Lên lịch, trước đây tool chờ 2 phút rồi bỏ. Nay tool **bấm lại** tối đa 2 lần.
- Video đã lỡ rơi vào trạng thái này: lúc rảnh tool **tự vào TikTok Studio kiểm tra**. Có bài trên TikTok thì chuyển "Đã hẹn giờ"; không có thì đưa video về CHƯA UP và **tự đăng lại**. Bác không cần làm gì.

## 2.8.7
- Tab Hàng chờ: thẻ video **Cần kiểm tra / Lỗi / Lỡ giờ** hiện luôn **lý do** (chữ đỏ) ngay trên thẻ, không phải bấm ⋯ mới thấy.

## 2.8.6
- **Lấp ngày thiếu chỉ bằng video mới**: ngày cuối của lịch còn thiếu (vd 15/11 mới 4/6) thì lần sau bác thêm video vào CHƯA UP, tool xếp video mới vào ngày đó trước cho đủ, rồi mới sang ngày sau. Bỏ việc tự kéo video có sẵn trong lịch và nút "Lấp ngày thiếu ngay".
- **Âm thanh Yêu thích gộp vào 1 chỗ**: chọn «Tự động: âm thanh Yêu thích đúng sản phẩm» ở ô Nhạc nền rồi bấm **Áp dụng nhạc** (bỏ nút riêng bị trùng). Kênh mình không có âm thanh đúng sản phẩm thì **mượn âm thanh của kênh khác** (tắt hẳn âm gốc). Sửa lỗi mượn không được vì kênh cho mượn chưa gắn sản phẩm cho âm thanh: nay tool tự gắn trước khi mượn. Video nào không gán được thì ghi rõ lý do.
- **Telegram báo cáo theo phiên**: mỗi phiên đăng gửi 1 tin tổng hợp (bao nhiêu video, thành công theo kênh, video có vấn đề kèm lý do, ảnh lỗi, video quay màn hình, video lỡ giờ). Không còn báo từng video.

## 2.8.5 · 2 phong cách có sẵn trên mọi máy
- Máy nào cập nhật cũng có sẵn 2 phong cách **Reup Aff** và **Xoay minh họa** ở mục 0 (tự tạo `MẪU/Reup Aff`, `MẪU/Xoay minh họa`, `SOURCE THÔ/Video Aff`, `SOURCE THÔ/Xoay`), đã gắn đúng source thô + quy trình dựng.
- Reup Aff dùng luôn phần đã học từ 7 video mẫu (nhịp ~1.8 giây/cảnh, ~35 giây, cách viết lời) đi kèm app, không cần bỏ video mẫu và bấm Học. Bỏ video mẫu riêng vào rồi bấm Học thì app dùng bản bác tự học.
- Bác chỉ cần bỏ video vào `SOURCE THÔ/Video Aff` (chia thư mục theo sản phẩm) và `SOURCE THÔ/Xoay`.

## 2.8.4
- Sửa lỗi cập nhật báo **"GitHub tạm chặn"**: GitHub chỉ cho mỗi máy (không có mã đọc) hỏi 60 lần/giờ, bản cập nhật nhiều file là vượt. Nay tool tải file qua đường không bị giới hạn này, đường cũ chỉ dùng dự phòng.

## 2.8.3
- Sửa lỗi **cập nhật không được khi mạng chập chờn** (báo IncompleteRead): bộ cập nhật tự tải lại từng file tối đa 4 lần, đổi sang đường tải dự phòng; mạng đứt hẳn thì giữ file đã tải được, bấm cập nhật lại sẽ tải tiếp phần còn thiếu. Lỗi mạng hiện thông báo dễ hiểu thay vì bảng lỗi đỏ.
- Ảnh logo nhẹ hơn (508 KB → 145 KB) cho máy mạng yếu cập nhật dễ hơn.

## 2.8.2 · Phong cách mới: Xoay + minh hoạ
- Phong cách **Xoay minh họa** (quy trình mới, chọn ở mục 0): video tự quay xoay sản phẩm trong `SOURCE THÔ/Xoay` được chèn thêm 4-5 đoạn x 2 giây cắt từ video aff **cùng sản phẩm** (tua nhanh 2x, tắt tiếng), khoảng 2/3 che hết khung, 1/3 hiện khung nhỏ góc trên. Giữ tiếng gốc (Sonix Up Video tự thêm âm thanh yêu thích khi đăng).
- Tool tự nhận sản phẩm của từng video xoay (tên file → chữ trên nhãn → AI), dựng thẳng mp4 1080p bằng ffmpeg (khoảng 15 giây / video, không cần mở CapCut), rồi đưa vào `<kênh>\CHƯA UP\<ngày>.mp4...`. Nhớ video nào đã làm; có tuỳ chọn làm lại ra bản mới với cảnh chèn khác.
- Đọc được cả video .MP4 (DJI) và .MOV (iPhone 4K).

## 2.8.1
- Edit Video tự nhận **thư mục sản phẩm bên trong source thô** của phong cách đang chọn theo tên thư mục (vd `SOURCE THÔ/Video Aff/Dam_Ca`, `TC01_Kich_Re`, `Bo_Tri_Top_One`, `Canxi_Bo`, `ĐẠM CÁ`, `KÍCH RỄ`...). Thư mục không rõ sản phẩm (vd `Khong_Chac_Chan`, `Video_AI`) bỏ qua. Bấm **Quét cảnh** để dùng video mới.

## 2.8.0 · Phong cách = Mẫu + Source thô + Tài nguyên + Quy trình
- Thư mục **`CHƯA LỌC` đổi tên thành `SOURCE THÔ`** (máy cập nhật tự đổi). Bên trong là các thư mục con bác tự đặt tên, vd `SOURCE THÔ/Video Aff` = video affiliate có sẵn.
- Sonix Edit Video có mục **0. Phong cách** ở đầu trang: chọn phong cách (thư mục con trong `MẪU`, vd `Reup Aff`), app hiện đủ bộ của phong cách đó để xem qua trước khi edit:
  - **Mẫu**: `MẪU/<tên>`, số video, đã học chưa, nhịp cắt cảnh, phong cách AI rút ra.
  - **Source thô** đi kèm: chọn thư mục con trong `SOURCE THÔ` (app nhớ cho từng phong cách); mục Tự lọc tự điền sẵn thư mục này.
  - **Tài nguyên**: nhạc, ảnh trong `TÀI NGUYÊN`, khuôn CapCut có / chưa.
  - **Quy trình dựng**: hiện có Reup Aff; các quy trình khác (quay thô tự cắt, không lồng tiếng, hiệu ứng) sẽ thêm sau, phong cách mới chỉ cần đưa video mẫu cho app học.

## 2.8.0
- **Tự lấp ngày thiếu video**: đặt 10 video/ngày mà có ngày mới 5 video (hết video, video lỗi, video bị bỏ) thì khi bác thêm video mới vào CHƯA UP, tool xếp video mới vào ngày còn thiếu trước cho đủ 10, rồi mới sang ngày sau. Video lỗi / bị bỏ để lại chỗ trống thì bộ đăng tự kéo video ở cuối lịch (chưa lên TikTok) về lấp, 30 phút kiểm 1 lần. Tab Duyệt có mục **Số video từng ngày** (ngày thiếu tô đỏ) và nút **Lấp ngày thiếu ngay**.
- **Video lỡ giờ đăng** (máy tắt, bộ đăng dừng quá 20 phút so với giờ hẹn): tool KHÔNG tự đăng dồn nữa mà giữ lại, hiện thông báo trên đầu app (và nhắn Telegram) để bác chọn: **dời sang khung giờ trống tiếp theo** (giữ đúng số video/ngày) hoặc **đăng bù ngay, dồn 1-4 video mỗi lần**, các lần cách nhau 10-60 phút.

## 2.7.5
- Dán mã bị lặp 2 lần, dính khoảng trắng / xuống dòng: tool tự lấy đúng 1 mã.
- Dán nhầm **mã báo lỗi** (SONIXBL-) vào ô mã nhận thông báo: tool vẫn lưu đúng chỗ và báo cho bác biết. Dán mã nhận thông báo (SONIX-) vào tab Báo lỗi cũng dùng được.

## 2.7.4
- **Mã báo lỗi** (bắt đầu bằng SONIXBL-): Admin lấy ở Cài đặt → Nhận thông báo về Telegram → Admin, gửi riêng cho từng người dùng qua Zalo. Người dùng dán 1 lần vào tab **Báo lỗi Admin** là báo lỗi tự về Telegram Admin, **không cần Telegram**. Mã chỉ gửi được báo lỗi (dùng bot báo lỗi riêng), không đụng tới bot thông báo.

## 2.7.3
- **Báo lỗi Admin không cần Telegram**: người dùng chỉ ghi mô tả, chụp / tải ảnh lỗi, bấm Gửi. App gửi kèm **ảnh đoạn nhật ký trên app** (đọc được ngay trên điện thoại) và gói nhật ký đầy đủ về Telegram Admin. Có ô xem trước đoạn nhật ký sẽ gửi.
- Tách riêng **Nhận thông báo về Telegram** (tuỳ chọn, cho ai muốn nhận tin). Mục Admin chỉ hiện trên máy Admin.
- Admin tạo thêm **bot báo lỗi** để gắn sẵn vào app cho mọi máy.

## 2.7.2
- Nối Telegram bằng **điện thoại** dễ hơn: app hiện **mã QR**, quét bằng camera / Zalo, bấm Start trong Telegram là app **tự nhận** (không cần bấm "Đã bấm Start"). Người nhận đầu tiên tự thành Admin (nhận Báo lỗi).
- Hướng dẫn tạo bot với BotFather từng bước trên điện thoại, cách chuyển mã bot sang máy tính qua Zalo Cloud của tôi.

## 2.7.1 · Chốt quy trình Reup Aff
- **Tự xuất video**: chọn **Kênh nhận video** ở bước 4 → tạo dự án xong tool tự mở CapCut, xuất **1080p**, rồi đưa vào `<kênh>\CHƯA UP\<ngày>\01.mp4, 02.mp4...` (mỗi ngày 1 thư mục, số thứ tự không trùng kể cả khi video đã đăng). Lúc xuất tool điều khiển CapCut như người, khoảng 1,5 phút / video: **đừng đụng chuột, bàn phím**. App nhớ kênh đã chọn cho từng sản phẩm.
- Mục **Xuất dự án có sẵn vào kênh**: chọn các dự án SONIX (vd đã sửa tay trong CapCut) để xuất vào kênh.
- **Sonix Up Video đọc thêm thư mục ngày** trong CHƯA UP (ngày cũ trước, trong ngày theo 01, 02, 03...).
- Làm hàng loạt: lưu lời từng video (data\edit\hang_loat) để xem lại; AI soát thêm chính tả tiêu đề.
- Mục **Quy trình Reup Aff (các bước)** ở đầu Sonix Edit Video: tóm tắt cả quy trình từ chuẩn bị tới đăng.
- Nhật ký các việc chạy nền tự ẩn sau 1 giờ cho gọn.

## 2.7.0
- **Thông báo Telegram** (Cài đặt → Thông báo Telegram): tool nhắn về Telegram khi có **sự cố** (kèm ảnh chụp lỗi + video quay màn hình lúc đăng), khi **làm xong** (đã hẹn giờ / đã đăng, việc Edit Video xong), khi **có bản cập nhật**. Tin có nhãn [Sonix Up Video] / [Sonix Edit Video]. Thêm nhiều người nhận, mỗi người chọn loại tin muốn nhận. Admin gửi **Mã kết nối Sonix** cho người dùng khác để dùng chung bot.
- **Tab Báo lỗi Admin** (cả trong Sonix Edit Video): ghi mô tả lỗi, chụp cửa sổ app hoặc tải ảnh lên, bấm Gửi → tool gửi ảnh + gói nhật ký về Telegram Admin, tin tên «Sự cố người dùng» (không gửi mật khẩu, token, khoá AI). Có nút **Nhờ AI xem nhanh** gợi ý cách tự xử lý.
- **Ảnh bìa**: nút **Trả về ảnh bìa AI chọn** (từng video và hàng loạt) khi lỡ đổi / tải ảnh khác; nút **Bỏ khỏi thư viện** cho ảnh lỡ tải lên (cất vào ẢNH BÌA\_DA_BO, không xoá hẳn).
- **Dừng viết lại caption** ngay lập tức: video đã viết xong giữ caption mới, video chưa viết giữ caption cũ. Nút "Dừng phân tích" không còn xoá nhầm video đang viết lại caption.
- Sửa lỗi **âm thanh đã đồng bộ không tự gắn sản phẩm**: nhãn bị ghi nhầm thành "bác tự sửa = trống" nên tool bỏ qua. Nay tool tự dò lại theo lời nói đã nghe (không tốn AI), kênh mượn âm thanh (KTNN) cũng có âm thanh để mượn.
- **Nhẹ máy hơn**: chỉ dựng tab đang mở (trước đây bấm nút nào cũng dựng lại cả 9 tab), ảnh bìa ở tab Duyệt dùng ảnh nhỏ, Nhạc nền chia trang 12 âm thanh, bộ nghe giọng nói dùng ít nhân CPU hơn.

## 2.6.4
- Sửa lỗi đăng video báo lỗi "không tìm thấy file video" sau khi thư mục VIDEO_TIKTOK được đổi tên thành SONIX_UP_VIDEO: hàng chờ vẫn ghi đường dẫn cũ. Nay tool tự sửa đường dẫn video, nhạc nền, âm thanh trong hàng chờ và dữ liệu (cả máy đã đổi tên từ trước). Video đã lỗi vì chuyện này: vào Hàng chờ, chọn, bấm "Chạy lại".

## 2.6.3
- Sửa lỗi dự án CapCut mất người dẫn ("Media Not Found" ở clip ghép người dẫn): dự án tạo ra giờ tự chứa đủ file người dẫn (liên kết cứng, không tốn thêm ổ), không còn phụ thuộc vào dự án mẫu.

## 2.6.2
- **Chạy được trên máy khác**: máy chưa có dự án mẫu trong CapCut hoặc chưa có nhạc nền thì Edit Video hiện nút **Tải và cài khuôn Reup Aff** (khoảng 210 MB, gồm khung, người dẫn, nền theme, 2 nhạc kịch tính). Tool tự cài vào CapCut, tự sửa đường dẫn, không cần chép tay.
- **Xem trước cảnh**: bấm **Chọn cảnh** để xem ảnh từng cảnh theo từng câu (loại cảnh, câu số mấy); cảnh nào không ưng bấm **Đổi** (đổi sang cảnh khác cùng loại), khung 4 ô có **Đổi 4 người**. Tạo dự án sẽ dùng đúng các cảnh đã duyệt.
- **Bấm 1 nút ra video**: nút **Lồng tiếng + chọn cảnh + tạo dự án** chạy nền, hiện tiến độ; CapCut đang mở thì tool chờ bác tắt rồi mới ghi.
- **Làm hàng loạt**: chọn số video (1-10), AI viết lời mới cho từng video (không trùng câu mở), lồng tiếng, chọn cảnh, tạo dự án CapCut liền.

## 2.6.1
- **Phong cách mẫu**: thư mục `SONIX_EDIT_VIDEO\MẪU`, mỗi thư mục con là 1 phong cách edit (tự đặt tên, vd `Reup Aff`), bỏ vài video mẫu vào. Trong app chọn **Làm theo phong cách mẫu** → **Học phong cách này**: tool nghe chép lời các video mẫu, đo nhịp cắt cảnh, AI tóm tắt cách làm (mở đầu, giọng, chữ, nhịp, cách chốt). Sau đó AI viết lời theo đúng phong cách đó và dự án CapCut cắt cảnh theo nhịp của mẫu.
- Máy chưa có thư mục `MẪU` / `CHƯA LỌC` trong `SONIX_EDIT_VIDEO`: tool tự tạo.

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
