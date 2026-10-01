#ifndef ProjectRoot
  #error Build using build-installer.ps1 to supply ProjectRoot and StageRoot
#endif
#define AppName "Codex-Glass"
#define AppVersion "3.1.1"

[Setup]
AppId={{9F7FAF7C-7C97-44A0-A987-907701048532}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Codex-Glass Contributors
VersionInfoVersion=3.1.1.0
VersionInfoDescription=Codex-Glass 安装程序
DefaultDirName={localappdata}\Programs\Codex-Glass
DefaultGroupName=Codex-Glass
DisableProgramGroupPage=yes
DisableDirPage=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputBaseFilename=Codex-Glass-{#AppVersion}-Windows-x64-Setup
SetupIconFile={#ProjectRoot}\source\assets\Codex-Glass.ico
UninstallDisplayIcon={app}\Codex-Glass.exe
LicenseFile={#ProjectRoot}\LICENSE
InfoBeforeFile={#ProjectRoot}\source\installer\install-notes.txt
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
CloseApplicationsFilter=Codex-Glass.exe,*.dll
RestartApplications=no
Uninstallable=yes
SetupLogging=yes

[Languages]
Name: "chinesesimplified"; MessagesFile: "{#ProjectRoot}\source\installer\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; Flags: unchecked
Name: "startup"; Description: "登录 Windows 后自动守候（客户端运行时显示浮窗）"; Flags: unchecked

[Files]
Source: "{#ProjectRoot}\app\Codex-Glass\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#StageRoot}\source\*"; DestDir: "{app}\source"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ProjectRoot}\third-party-licenses\*"; DestDir: "{app}\third-party-licenses"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ProjectRoot}\dependency-sources\*"; DestDir: "{app}\dependency-sources"; Flags: ignoreversion recursesubdirs createallsubdirs nocompression
Source: "{#ProjectRoot}\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectRoot}\*.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectRoot}\preview-*.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectRoot}\reference-comparison.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#StageRoot}\*.html"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#StageRoot}\Codex-Glass-3.1.1-Source.zip"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#StageRoot}\payload-manifest.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Codex-Glass"; Filename: "{app}\Codex-Glass.exe"; WorkingDir: "{app}"
Name: "{group}\使用说明"; Filename: "{app}\使用说明.html"
Name: "{group}\卸载 Codex-Glass"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Codex-Glass"; Filename: "{app}\Codex-Glass.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Codex-Glass"; ValueData: """{app}\Codex-Glass.exe"" --watch"; Tasks: startup

[Run]
Filename: "{app}\Codex-Glass.exe"; Parameters: "--watch"; Description: "启动 Codex-Glass（客户端未运行时在托盘守候）"; Flags: nowait postinstall skipifsilent
Filename: "{app}\使用说明.html"; Description: "查看使用说明"; Flags: shellexec postinstall skipifsilent unchecked

[Code]
const
  RunKey = 'Software\Microsoft\Windows\CurrentVersion\Run';
var
  InitializedStartupTask: Boolean;

function OwnedStartup(): Boolean;
var Value: String;
begin
  Result := RegQueryStringValue(HKCU, RunKey, 'Codex-Glass', Value) and
    (CompareText(Value, '"' + ExpandConstant('{app}\Codex-Glass.exe') + '" --watch') = 0);
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if (CurPageID = wpSelectTasks) and not WizardSilent() and not InitializedStartupTask then begin
    { Preserve a startup choice changed from the app since the last install. }
    WizardForm.TasksList.Checked[1] := OwnedStartup();
    InitializedStartupTask := True;
  end;
end;

procedure StopOwnedInstance();
var ResultCode: Integer;
begin
  if FileExists(ExpandConstant('{app}\Codex-Glass.exe')) then begin
    Exec(ExpandConstant('{app}\Codex-Glass.exe'), '--quit-if-owned', '',
      SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Sleep(600);
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  StopOwnedInstance();
  Result := '';
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and (not WizardIsTaskSelected('startup')) and OwnedStartup() then
    RegDeleteValue(HKCU, RunKey, 'Codex-Glass');
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then begin
    StopOwnedInstance();
    if OwnedStartup() then
      RegDeleteValue(HKCU, RunKey, 'Codex-Glass');
  end;
end;
