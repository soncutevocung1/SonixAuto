# Quy định cho Claude khi làm việc trên repo này

## Key API tính phí — PHẢI HỎI TRƯỚC
- Key Anthropic API trong cài đặt app Sonix Auto là của anh Sơn và **trả tiền theo lượt dùng** (khác gói Pro).
  Key này chỉ dành cho app: viết caption, nhận diện sản phẩm khi up video (Haiku).
- **Trước khi chạy bất kỳ việc gì gọi key API** (gắn nhãn thư viện, xem hình bằng AI, lên kế hoạch dựng, chấm điểm...)
  phải hỏi anh Sơn trước, nói rõ: việc gì, mô hình nào, số lượt gọi ước tính, chi phí ước tính. Chỉ chạy khi anh đồng ý.
- Việc cần "suy nghĩ" với ít lượt (chọn lần nói, kế hoạch phụ đề/zoom/minh họa, góp ý bản dựng): Claude tự làm
  trực tiếp trong cuộc trò chuyện (gói Pro), ghi kết quả ra file — KHÔNG gọi API.
- Việc lặp lại số lượng lớn (gắn nhãn hàng nghìn cảnh): chỉ dùng **Haiku** qua API, và chỉ khi anh đã đồng ý.
- Không dùng Opus/Sonnet qua API cho công cụ Sơn 01.
- Code đã có chốt chặn: các công cụ trong `core/son01/tools/` chỉ gọi API khi đặt biến môi trường
  `SONIX_CHO_PHEP_API=1`. Chỉ đặt biến này sau khi anh Sơn đồng ý cho lần chạy đó.

## Dựng video phong cách Sơn 01
- **Trước mỗi lần dựng / sửa video Sơn 01 phải đọc `core/son01/PHONG_CACH_SON01.md`** (mọi điểm anh Sơn đã sửa)
  và `core/son01/LUAT_CAT_ANH_SON.md` (luật cắt source thô). Khi anh góp ý điểm mới → ghi thêm vào file đó.

## Cách trả lời anh Sơn
- Tiếng Việt, dễ hiểu, từ tiếng Anh phải dịch nghĩa. Nói thẳng, có lý do.
