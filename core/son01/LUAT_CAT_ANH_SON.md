# Luật cắt source thô của anh Sơn (học từ dự án mẫu DAMBOTC01_SONIX)

Nguồn đối chiếu: timeline "Đạm shop Bọ" (C3420, 12 đoạn, 38,2 s), "Bọ2" (C3421 + C3422, 9 đoạn),
"bọ 3" (C3432, 6 đoạn), so với lời Whisper từng chữ và khung hình từng giây của C3420.

## Cách anh quay
- Ngồi trước máy, **cầm điện thoại đọc kịch bản** (cúi đầu, nón che mặt, tay cầm máy) → đọc thầm/nhẩm
  → **ngẩng lên, cất điện thoại, nói thuộc lòng** với ống kính. Mỗi câu nói lại 2–5 lần.
- Đoạn đọc kịch bản có tiếng nhưng **luôn bỏ**. Đoạn nói thuộc lòng nhìn ống kính mới **lấy**.

## Luật giữ / bỏ
1. **Bỏ mọi đoạn có điện thoại trong tay hoặc mặt cúi xuống** (khung C3420 ở giây 20, 30, 50, 62, 85, 100,
   135, 150, 165, 240, 265, 325 đều là đọc điện thoại → không đoạn nào được giữ).
2. **Mỗi ý chỉ giữ 1 lần nói** – thường là **lần cuối cùng nói trọn câu, không vấp**
   (vd câu mở đầu nói 3 lần 18,8 s / 22,2 s / 26,4 s → anh lấy lần 43,4 s; "Đạm cá là một dòng đạm dễ hấp thu"
   nói 3 lần → lấy lần 74,0 s; "Giai đoạn cây con…" 4 lần → lấy lần 202,2 s).
   Các lần nói lại có thể cách nhau rất xa, không chỉ liền kề.
3. **Không cắt giữa câu**: đoạn giữ phải bắt đầu ở đầu câu và kết thúc sau chữ cuối của câu (có hơi thở ngắn).
   Một ý dài có thể ghép 2 lần nói (vd 122,7–126,5 rồi 128,7–130,0 rồi 141,8–143,6).
4. Bỏ câu nói dở ("Thứ ba, các bác cứ đông đồng…"), câu sai từ, câu dừng giữa chừng.
5. Đoạn giữ dài 1,3–5,3 s (trung bình ~3 s), tổng 30–40 s; thứ tự giữ đúng mạch kịch bản
   (riêng "bọ 3" có đảo thứ tự 1 đoạn để ý liền mạch hơn).
6. Kêu gọi cuối: lấy lần nói trọn "Các bác đã sử dụng … chưa, bình luận lại ở dưới video này để … tham khảo ý kiến nhé".
7. **Ý liệt kê phải đủ mục** (3 giai đoạn: cây con / nuôi hoa dưỡng quả / sau thu hoạch). Lần nói có lặp chữ ở đầu
   thì **cắt theo chữ** từ chỗ nói lại trọn (anh lấy 232,73–235,10 s, bỏ "Và giai đoạn…" lần đầu trong cùng hơi nói).
8. Câu chỉ chỗ mua ("đạm cá em để dưới giỏ hàng, góc trái màn hình") **không lấy** khi đã có lời kêu gọi bình luận.

## Kết quả kiểm tra bộ cắt v2 trên C3420 (so với "Đạm shop Bọ")
- Lần 1 (cắt theo câu): độ phủ 92 %, thừa 13 % – sót ý "sau thu hoạch", thừa câu giỏ hàng → thêm luật 7, 8
  và cho AI cắt theo chỉ số chữ.
- Lần 2 (cắt theo chữ + luật 7, 8): **độ phủ 98 %, thừa 5 %**, đúng 12 đoạn anh chọn (lệch mốc ≤ 0,3 s).

## Vì sao bản tự động trước sai
- Whisper (VAD) **bỏ sót lời** (vd 185,7–193,8 s không có chữ nhưng anh giữ 188,7–190,5 s) và **gộp đoạn đọc
  điện thoại vào câu** (79,3–95,8 s; 129,9–143,6 s) → mốc thời gian lệch, cắt hụt đầu/đuôi câu.
- Bộ cắt chỉ so lặp với 3 câu kế tiếp → sót lần nói lặp ở xa (đoạn "thứ ba" bị 2 lần).
- Không nhìn hình → giữ cả đoạn đang đọc điện thoại.

## Cách làm mới (đã thống nhất hướng)
- Nghe lại không bỏ VAD + căn mốc chữ chính xác (WhisperX/wav2vec2 tiếng Việt hoặc tinh chỉnh theo năng lượng âm).
- Nhìn hình mỗi 0,2 s: điện thoại trong tay (YOLO lớp "cell phone") + mặt cúi/khuất (MediaPipe Face Landmarker).
- Gom các lần nói cùng ý trên **toàn video**, AI (Claude) chọn lần tốt nhất theo: trọn câu, không vấp, nhìn ống kính,
  lần cuối được ưu tiên.
- Kiểm tra bằng chính 3 timeline mẫu: đoạn tool chọn phải trùng ≥ 80 % thời lượng với đoạn anh Sơn chọn.
