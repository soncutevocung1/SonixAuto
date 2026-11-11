# SonixDangVideo.exe

File bấm mở app. Nó chỉ tìm Python đi kèm (`python\pythonw.exe` hoặc `.venv\Scripts\pythonw.exe`) rồi chạy `SonixDangVideo.pyw`.

Dựng lại (cần Go):

```bash
python3 tao_bieu_tuong.py ../../assets/sonix.ico rsrc_windows_amd64.syso
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -trimpath -ldflags "-H=windowsgui -s -w" -o ../../SonixDangVideo.exe .
```
