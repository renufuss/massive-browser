; Inno Setup script -> dist\MultiBrowserLauncher-Setup.exe
; Wraps the PyInstaller onedir build into a per-user installer. (c) 2026 Renufus.
; Build:  iscc packaging\installer.iss   (after pyinstaller)

#define AppName "Multi Browser Launcher"
#define AppVersion "1.1.0"
#define AppExe "MultiBrowserLauncher.exe"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Renufus
AppCopyright=© 2026 Renufus
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=MultiBrowserLauncher-Setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "..\dist\MultiBrowserLauncher\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
