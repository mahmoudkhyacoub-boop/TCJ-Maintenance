#define MyAppName "Trend Center Jordan"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "TREND CENTER JORDAN"
#define MyAppExeName "Trend_Center_Jordan.exe"

[Setup]
AppId={{A7B5C9B0-8F6D-4E0D-9A8D-4D4D8C8A2C01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Trend Center Jordan
DefaultGroupName={#MyAppName}
OutputDir=installer_output
OutputBaseFilename=Trend_Center_Jordan_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "تشغيل ترند سنتر الأردن"; Flags: nowait postinstall skipifsilent
