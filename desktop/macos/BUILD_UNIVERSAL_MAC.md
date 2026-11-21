# freETarget Minimalist 0.3.11 — Universal Mac build

This source package prepares **one macOS application** that contains both **arm64 (Apple Silicon)** and **x86_64 (Intel)** executable slices. The app and compressed ZIP contain the same program; the ZIP is for sharing or backup.

## Build on your Mac

1. Clone or download this repository and locate `desktop/macos/`.
2. Install the official [macOS 64-bit universal2 Python 3.13 installer](https://www.python.org/downloads/macos/) if not already installed. The script rejects Apple Silicon-only Homebrew Python rather than silently producing a non-universal app. If prompted, install Apple's Command Line Tools with `xcode-select --install`.
3. In Terminal, change to the Mac source directory. Replace the checkout path below with the location where you saved the repository:

   ```bash
   cd "$HOME/Downloads/freETarget-Minimalist-Desktop/desktop/macos"
   bash BUILD_MAC.command
   ```

   You can also open `BUILD_MAC.command` from Finder if permitted by macOS. The first build downloads dependencies and may take several minutes. The script runs the Python unit tests, builds with PyInstaller's `universal2` target, and validates the app's collected Mach-O binaries.

## Output

The successful build creates:

```text
release/mac/
  freETarget Minimalist.app
  freETarget-Minimalist-0.3.11-beta.1-universal2.zip
  BUILD_INFO.json
```

The `.app` is the program to copy into `/Applications`. The `.zip` is a distribution/backup archive of that same `.app`; you do **not** need separate Intel and Apple Silicon downloads.

Open the output folder:

```bash
open "$HOME/Downloads/freETarget-Minimalist-Desktop/desktop/macos/release/mac"
```

## Verify the main executable

Run this in Terminal after a successful build:

```bash
lipo -archs "$HOME/Downloads/freETarget-Minimalist-Desktop/desktop/macos/release/mac/freETarget Minimalist.app/Contents/MacOS/freETargetMinimalist"
```

It should print **`x86_64 arm64`** (order may differ). The build script additionally verifies all collected Mach-O files, not just the main executable. If a dependency lacks either slice, the build fails rather than claiming universal compatibility.

## Testing and distribution

- Test the app on Apple Silicon and an Intel Mac, including USB/Wi-Fi connection, a live shot, logging a session, and reopening saved data.
- For a signed iCloud-enabled distribution build, use `bash BUILD_SIGNED_MAC.command`, then `bash NOTARIZE_MAC.command`. Set your own signing identity/profile through the documented environment variables. The notarization script stops if any acceptance check fails.
- Saved shooter/gun/session data remains under `~/Library/Application Support/freETarget/DesktopBeta`. Back up records before upgrading.
- To build only for your current Mac's CPU instead, use `bash BUILD_MAC_NATIVE.command`. That build's ZIP ends in `-arm64.zip` or `-x86_64.zip`.

**Important:** This source directory does not contain a compiled `.app`. The build must be run on macOS. The maintainer's clean rebuild passed notarization, stapler, Gatekeeper and system-policy checks on November 21, 2026. Every rebuild still requires its own verification and device testing.

## Interpreter override (optional)

By default, the build selects an installed Python with both CPU slices. To explicitly select one, set `FT_UNIVERSAL_PYTHON` to its path before running the build. The override must still pass the universal2 architecture check.

```bash
FT_UNIVERSAL_PYTHON=/Library/Frameworks/Python.framework/Versions/3.15/bin/python3.15 bash BUILD_MAC.command
```

The override is also used by the isolated selector unit test so an installed Python 3.15 cannot override its fake Python 3.13 fixture.

## Signed iCloud build

See [START_CLEAN_MAC.md](START_CLEAN_MAC.md) for the signing and notarization walkthrough. When working from this repository, use `desktop/macos/` as the source folder instead of the standalone ZIP folder shown there.
