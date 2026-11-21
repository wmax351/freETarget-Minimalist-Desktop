# freETarget Minimalist 0.3.12-beta.1 — Windows x64 and x86 source

This is a clean **source** distribution, not precompiled installers. Build on Windows 11 x64.

## Prerequisites
- Python 3.12 64-bit and Python 3.12 32-bit (both registered with the Python launcher `py`)
- Inno Setup 6 for Setup.exe generation
- Internet access for Python package installation

## One-click builds
- `BUILD_AND_INSTALL_X64.bat`: builds x64 app and installer
- `BUILD_AND_INSTALL_X86.bat`: builds x86 app and installer
- `BUILD_AND_INSTALL_BOTH.bat`: builds both sequentially

## Outputs
- x64 portable: `release/freETargetMinimalist/` and `release/*-Windows-x64.zip`
- x64 installer: `release/installer/`
- x86 portable: `release-x86/freETargetMinimalist/` and `release-x86/*-Windows-x86.zip`
- x86 installer: `release-x86/installer/`

The two architectures are built separately. The x86 build checks that its EXE and WebView2 loader are 32-bit. If this check fails, the installer will not be generated. The x64 installer restricts installation to compatible 64-bit Windows; the x86 installer supports 32-bit Windows.

**This source refresh has not yet been compiled or tested on Windows.** Test on Windows 10 32-bit before publishing compatibility claims. Keep each installer in its own release asset.

## Current refresh

Updated logo/icons, circular color swatches and spacing, stacked Wi-Fi mode text,
Korean/Turkish/Vietnamese/Arabic language options and Brazilian Portuguese speech
locale handling. The live target supports touchscreen pinch/pan, precision-touchpad
pinch and mouse drag when zoomed. Reset zoom to return to center. Demo Mode remains
optional and keeps sample results separate. USB and Wi-Fi are retained.

App data directories and installer IDs are unchanged. This update does not add
iCloud or a Windows cloud-sync service. Back up shooter data before upgrading.

Build on your Windows 11 machine (including Parallels): open this extracted folder
and run BUILD_AND_INSTALL_BOTH.bat. Reuse the installed Python 3.12 x64/x86 and
Inno Setup 6. Outputs are versioned 0.3.12-beta.1 with separate Windows-x64-Setup.exe
and Windows-x86-Setup.exe names. Upload the tested installers before replacing
GitHub's existing public downloads.
