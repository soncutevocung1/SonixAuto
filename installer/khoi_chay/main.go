// SonixDangVideo.exe: bấm là mở app. Tìm Python đi kèm (python\ hoặc .venv\) rồi chạy SonixDangVideo.pyw.
package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
	"unsafe"
)

func msg(text string) {
	t, _ := syscall.UTF16PtrFromString(text)
	c, _ := syscall.UTF16PtrFromString("Sonix Đăng Video")
	syscall.NewLazyDLL("user32.dll").NewProc("MessageBoxW").Call(0, uintptr(unsafe.Pointer(t)), uintptr(unsafe.Pointer(c)), 0x10)
}

func main() {
	exe, _ := os.Executable()
	dir := filepath.Dir(exe)
	py := ""
	for _, c := range []string{
		filepath.Join(dir, "python", "pythonw.exe"),
		filepath.Join(dir, ".venv", "Scripts", "pythonw.exe"),
	} {
		if _, err := os.Stat(c); err == nil {
			py = c
			break
		}
	}
	if py == "" {
		if p, err := exec.LookPath("pythonw.exe"); err == nil {
			py = p
		}
	}
	if py == "" {
		msg("Không tìm thấy Python của tool. Bác cài lại bằng bộ cài SonixDangVideo_Setup.exe.")
		return
	}
	args := append([]string{filepath.Join(dir, "SonixDangVideo.pyw")}, os.Args[1:]...)
	cmd := exec.Command(py, args...)
	cmd.Dir = dir
	cmd.Env = append(os.Environ(), "PYTHONUTF8=1", "PYTHONIOENCODING=utf-8")
	// pythonw không có cửa sổ đen nên không cần ẩn; ẩn ở đây sẽ làm cửa sổ app bị ẩn theo
	cmd.SysProcAttr = &syscall.SysProcAttr{}
	if err := cmd.Start(); err != nil {
		msg("Không mở được tool: " + err.Error())
	}
}
