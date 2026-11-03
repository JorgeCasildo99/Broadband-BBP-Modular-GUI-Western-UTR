; BBP-GUI.iss - Inno Setup script (needs Inno Setup 6.3 or newer)
; Place this file in the project root, next to main.py. Build order:
;   1. Build the app:   python -m PyInstaller ... main.py   (creates dist\BBP-GUI)
;   2. Open this file in Inno Setup and press Ctrl+F9 (Build > Compile).
; The installer is written to installer_output\.

#define MyAppName      "BBP-GUI"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "Jorge Casildo"
#define MyAppURL       "https://github.com/JorgeCasildo99/Broadband-BBP-Modular-GUI-Western-UTR"
#define MyAppExe       "BBP-GUI.exe"

[Setup]
; AppId identifies this program for upgrades and uninstall. Never change it.
AppId={{F3EAE98A-65E9-4045-8468-60C61F066E4C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
; Per-user install by default (no administrator prompt); the user can still
; choose "for all users" in the dialog.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; WSL 2 needs Windows 10 version 2004 (build 19041) or newer.
MinVersion=10.0.19041
OutputDir=installer_output
OutputBaseFilename=BBP-GUI-Setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
InfoBeforeFile=installer_assets\Prerequisites.txt
UninstallDisplayIcon={app}\{#MyAppExe}
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\BBP-GUI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "Launch {#MyAppName}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Settings and log file written by the app (not the user's BBP data in WSL).
Type: filesandordirs; Name: "{userappdata}\BBP-GUI"

[Code]
{ Runs wsl.exe with the given arguments; True only if it exits with code 0. }
function WslSucceeds(const Params: String): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec(ExpandConstant('{sys}\wsl.exe'), Params, '', SW_HIDE,
                 ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

{ Pre-flight check on the "Ready to Install" page. It only warns: the app
  repeats the same checks at startup and explains any problem in detail. }
function NextButtonClick(CurPageID: Integer): Boolean;
var
  Problem, NL, Msg: String;
begin
  Result := True;
  NL := Chr(13) + Chr(10);
  if CurPageID <> wpReady then
    Exit;

  Problem := '';
  if not WslSucceeds('--exec echo ok') then
    Problem := 'WSL 2 with a Linux distribution (Ubuntu) could not be reached.'
  else if not WslSucceeds('--exec bash -ic "command -v run_bbp.py"') then
    Problem := 'WSL works, but the SCEC Broadband Platform (run_bbp.py) was not found inside it.';

  if Problem <> '' then
  begin
    Msg := Problem + NL + NL;
    Msg := Msg + 'BBP-GUI can still be installed now, but it will not run simulations until this is set up (see Part 1 and Part 2 of the prerequisites page shown at the start of this installer).';
    Msg := Msg + NL + NL + 'Continue with the installation?';
    Result := MsgBox(Msg, mbConfirmation, MB_YESNO) = IDYES;
  end;
end;
