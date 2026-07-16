; Inno Setup script for CigarBrokerCRM — Whoastra Labs LLC
; Build:  ISCC.exe installer.iss   (after `pyinstaller cigarbrokercrm.spec`)
; Output: installer\CigarBrokerCRM-Setup.exe
;
; Installs the app to Program Files. All user data (database, config, logo,
; reports) is created by the app itself in Documents\CigarBrokerCRM, so the
; uninstaller never touches it.

#define MyAppName "CigarBrokerCRM"
#define MyAppVersion "1.3.0"
#define MyAppPublisher "Whoastra Labs LLC"
#define MyAppExeName "CigarBrokerCRM.exe"

[Setup]
AppId={{B7C3E5D1-4A2F-4E8B-9C6D-1F0A83B2E947}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=CigarBrokerCRM-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
