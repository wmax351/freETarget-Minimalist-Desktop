#define AppVersion "0.3.12-beta.1"
[Setup]
AppId={{C8C3D90F-EBE2-4B6B-9D78-1BC0F1A6D3E1}
AppName=freETarget Minimalist (32-bit)
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\freETargetMinimalist-x86
DefaultGroupName=freETarget Minimalist
PrivilegesRequired=lowest
ArchitecturesAllowed=x86compatible
OutputDir=..\release-x86\installer
OutputBaseFilename=freETargetMinimalist-{#AppVersion}-Windows-x86-Setup
SetupIconFile=..\app\assets\freetarget.ico
UninstallDisplayIcon={app}\freETargetMinimalist.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked
[Files]
Source: "..\release-x86\freETargetMinimalist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\freETarget Minimalist"; Filename: "{app}\freETargetMinimalist.exe"
Name: "{autodesktop}\freETarget Minimalist"; Filename: "{app}\freETargetMinimalist.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\freETargetMinimalist.exe"; Description: "Launch freETarget Minimalist"; Flags: nowait postinstall skipifsilent
; User profiles and history are not deleted by the uninstaller.
