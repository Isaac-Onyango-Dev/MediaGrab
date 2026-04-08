; ─────────────────────────────────────────────
; MediaGrab – Windows Installer (Inno Setup)
; Requires: Inno Setup 6.x (https://jrsoftware.org/isinfo.php)
; Compile:  iscc installer_windows.iss
;
; NOTE: This script expects the following layout relative
;       to the desktop/ directory (set up by build_windows.bat):
;         dist/installer_staging/MediaGrab.exe
;         dist/installer_staging/assets/...
;         dist/installer_staging/ffmpeg/...
; ─────────────────────────────────────────────

#define MyAppName "MediaGrab"
#define MyAppVersion "1.0.6"
#define MyAppPublisher "Isaac Onyango"
#define MyAppURL "https://github.com/Isaac-Onyango-Dev/MediaGrab"
#define MyAppExeName "MediaGrab.exe"
#define MyAppId "A3F8C1D2-4E7B-4A9C-B5D6-1F2E3A4B5C6D"
#define StagingDir "dist\installer_staging"

[Setup]
AppId={{#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=MediaGrab-{#MyAppVersion}-Setup
SetupIconFile={#StagingDir}\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=100,100
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoVersion={#MyAppVersion}
VersionInfoCopyright=Copyright (C) {#MyAppPublisher}
VersionInfoDescription={#MyAppName} Installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
ChangesAssociations=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Create a &Quick Launch shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; Main application executable
Source: "{#StagingDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; FFmpeg binaries (bundled)
Source: "{#StagingDir}\ffmpeg\*"; DestDir: "{app}\ffmpeg"; Flags: ignoreversion recursesubdirs createallsubdirs

; Assets folder (icons, images, etc.)
Source: "{#StagingDir}\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu shortcut (always created)
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

; Desktop shortcut (optional task)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"; Tasks: desktopicon

; Quick Launch shortcut (optional task)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\ffmpeg"
Type: filesandordirs; Name: "{app}\assets"
Type: filesandordirs; Name: "{localappdata}\{#MyAppName}"

[Registry]
; File association for checking updates on first run
Root: HKCU; Subkey: "Software\{#MyAppName}"; ValueType: string; ValueName: "InstallDate"; ValueData: "{code:GetCurrentDate}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey

[Code]
function GetCurrentDate(Param: String): String;
begin
  Result := GetDateTimeString('yyyy-mm-dd', '-', ':');
end;

function InitializeSetup(): Boolean;
var
  PrevVersion: String;
  UninstallResult: Integer;
begin
  Result := True;

  // Check if a previous version is already installed
  if RegQueryStringValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{{#MyAppId}_is1', 'DisplayVersion', PrevVersion) or
     RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{{#MyAppId}_is1', 'DisplayVersion', PrevVersion) then
  begin
    if MsgBox('A previous version of {#MyAppName} is already installed (v' + PrevVersion + '). Do you want to uninstall it first?',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      // Run the previous uninstaller
      Exec(ExpandConstant('{uninstallexe}'), '/SILENT', '', SW_HIDE, ewWaitUntilTerminated, UninstallResult);
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Add app to PATH environment variable (user scope) so ffmpeg is accessible
    RegWriteStringValue(HKCU, 'Environment', 'MediaGrabPath', ExpandConstant('{app}'));
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // Clean up registry entries
    RegDeleteValue(HKCU, 'Environment', 'MediaGrabPath');
    RegDeleteKeyIncludingSubkeys(HKCU, 'Software\{#MyAppName}');
  end;
end;
