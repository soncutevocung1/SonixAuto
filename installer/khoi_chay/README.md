# Sonix Auto.exe

File bấm mở app. Nó chỉ tìm Python đi kèm (`python\pythonw.exe` hoặc `.venv\Scripts\pythonw.exe`) rồi chạy `SonixDangVideo.pyw`.
Biểu tượng lấy từ `assets\sonix.ico`.

Dựng lại (không cần cài gì, dùng trình dịch C# có sẵn trong Windows), chạy ở thư mục gốc của tool:

```bat
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /nologo /target:winexe /optimize+ /codepage:65001 /win32icon:assets\sonix.ico "/out:Sonix Auto.exe" installer\khoi_chay\SonixAuto.cs
```
