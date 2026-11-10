; Bộ cài Sonix Đăng Video. GitHub Actions dựng tự động (.github/workflows/bo_cai.yml).
; Cần 2 thư mục do workflow chuẩn bị sẵn: build\app (mã nguồn) và build\python (Python + thư viện).
; Dựng tay: iscc /DMyVersion=2.0.2 installer\SonixDangVideo.iss

#ifndef MyVersion
  #define MyVersion "0.0.0"
#endif
#define MyName "Sonix Đăng Video"
#define MyLnk "SonixDangVideo"

[Setup]
AppId={{6B1F3C2A-5D7E-4A8B-9C0D-50A1DA06E0F1}
AppName={#MyName}
AppVersion={#MyVersion}
AppVerName={#MyName} {#MyVersion}
AppPublisher=Sonix
DefaultDirName={localappdata}\Programs\SonixDangVideo
DisableDirPage=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=SonixDangVideo_Setup_{#MyVersion}
SetupIconFile=..\build\app\assets\sonix.ico
UninstallDisplayIcon={app}\assets\sonix.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=no

[Languages]
Name: "vi"; MessagesFile: "Vietnamese.isl"

[Tasks]
Name: "desktopicon"; Description: "Tạo biểu tượng ngoài màn hình"; GroupDescription: "Biểu tượng:"
Name: "autostart"; Description: "Tự chạy nền khi mở máy (tới giờ hẹn vẫn đăng)"; GroupDescription: "Khởi động:"; Flags: unchecked

[Files]
; Mã nguồn: ghi đè bản cũ, KHÔNG có thư mục data nên dữ liệu cũ (đăng nhập, hàng chờ, khoá AI) giữ nguyên
Source: "..\build\app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\build\python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\build\app\manifest.json"; DestDir: "{app}\data\capnhat"; DestName: "manifest_dang_dung.json"; Flags: ignoreversion

[Dirs]
Name: "{app}\data"; Flags: uninsneveruninstall

[Icons]
Name: "{userprograms}\{#MyLnk}"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\SonixDangVideo.pyw"""; WorkingDir: "{app}"; IconFilename: "{app}\assets\sonix.ico"; Comment: "{#MyName}"
Name: "{userdesktop}\{#MyLnk}"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\SonixDangVideo.pyw"""; WorkingDir: "{app}"; IconFilename: "{app}\assets\sonix.ico"; Comment: "{#MyName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyLnk} (chạy nền)"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\SonixDangVideo.pyw"" --nen"; WorkingDir: "{app}"; IconFilename: "{app}\assets\sonix.ico"; Comment: "{#MyName} chạy nền"; Tasks: autostart

[Run]
; Máy chưa có Chrome: tải trình duyệt dự phòng để đăng TikTok (cần mạng, ~150 MB)
Filename: "{app}\python\python.exe"; Parameters: "-m playwright install chromium"; WorkingDir: "{app}"; StatusMsg: "Đang tải trình duyệt dự phòng (máy chưa có Chrome)..."; Flags: runhidden; Check: NoChrome
Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\SonixDangVideo.pyw"""; WorkingDir: "{app}"; Description: "Mở {#MyName} ngay"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Chỉ xoá chương trình + thư viện; thư mục data (dữ liệu của bác) được giữ lại
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\core\__pycache__"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\static"

[Code]
function NoChrome: Boolean;
begin
  Result := not (FileExists(ExpandConstant('{commonpf64}\Google\Chrome\Application\chrome.exe'))
    or FileExists(ExpandConstant('{commonpf32}\Google\Chrome\Application\chrome.exe'))
    or FileExists(ExpandConstant('{localappdata}\Google\Chrome\Application\chrome.exe')));
end;

{ Tắt tool đang chạy (bộ đăng + giao diện) trước khi cài đè / gỡ, để không bị khoá file }
procedure StopApp(Dir: String);
var
  Code: Integer;
  Cmd: String;
begin
  Cmd := '-NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like ''python*'' -and ($_.CommandLine -like ''*' + Dir + '*'' -or $_.ExecutablePath -like ''' + Dir + '*'') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"';
  Exec('powershell.exe', Cmd, '', SW_HIDE, ewWaitUntilTerminated, Code);
  Sleep(1500);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  if DirExists(ExpandConstant('{app}')) then
    StopApp(ExpandConstant('{app}'));
  Result := '';
end;

function InitializeUninstall: Boolean;
begin
  StopApp(ExpandConstant('{app}'));
  Result := True;
end;
