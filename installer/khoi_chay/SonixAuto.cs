// Sonix Auto.exe: bấm là mở app. Tìm Python đi kèm (python\ hoặc .venv\) rồi chạy SonixDangVideo.pyw.
// Dựng lại (không cần cài gì, dùng trình dịch C# có sẵn trong Windows):
//   C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /nologo /target:winexe /optimize+
//     /win32icon:assets\sonix.ico /out:"Sonix Auto.exe" installer\khoi_chay\SonixAuto.cs
using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Windows.Forms;

[assembly: System.Reflection.AssemblyTitle("Sonix Auto")]
[assembly: System.Reflection.AssemblyProduct("Sonix Auto")]

static class SonixAuto
{
    [STAThread]
    static void Main(string[] args)
    {
        string dir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\');
        string py = new[] {
            Path.Combine(dir, "python", "pythonw.exe"),
            Path.Combine(dir, ".venv", "Scripts", "pythonw.exe"),
        }.FirstOrDefault(File.Exists);
        if (py == null)
        {
            MessageBox.Show("Không tìm thấy Python của tool. Bác cài lại bằng bộ cài SonixAuto_Setup.exe.",
                            "Sonix Auto", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }
        string pyw = Path.Combine(dir, "SonixDangVideo.pyw");
        string rest = string.Join(" ", args.Select(a => "\"" + a.Replace("\"", "\\\"") + "\""));
        var psi = new ProcessStartInfo(py, "\"" + pyw + "\" " + rest)
        {
            WorkingDirectory = dir,
            UseShellExecute = false,
        };
        psi.EnvironmentVariables["PYTHONUTF8"] = "1";
        psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
        try { Process.Start(psi); }
        catch (Exception e)
        {
            MessageBox.Show("Không mở được tool: " + e.Message, "Sonix Auto", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}
