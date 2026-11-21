#define AppVersion "0.3.12-beta.1"
[Setup]
AppId={{6A39882A-0E84-499D-8F75-82921E55F7A2}
AppName=freETarget Minimalist
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\freETargetDesktopBeta
DefaultGroupName=freETarget Minimalist
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\release\installer
OutputBaseFilename=freETargetMinimalist-{#AppVersion}-Windows-x64-Setup
SetupIconFile=..\app\assets\freetarget.ico
UninstallDisplayIcon={app}\freETargetMinimalist.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
[InstallDelete]
Type: files; Name: "{app}\freETargetDesktop.exe"
Type: files; Name: "{userprograms}\freETarget Desktop Beta\freETarget Desktop Beta.lnk"
Type: files; Name: "{userdesktop}\freETarget Desktop Beta.lnk"
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked
[Files]
Source: "..\release\freETargetMinimalist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\freETarget Minimalist"; Filename: "{app}\freETargetMinimalist.exe"
Name: "{autodesktop}\freETarget Minimalist"; Filename: "{app}\freETargetMinimalist.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\freETargetMinimalist.exe"; Description: "Launch freETarget Minimalist"; Flags: nowait postinstall skipifsilent
; App data is deliberately outside {app}; uninstall does not remove profiles or History.
