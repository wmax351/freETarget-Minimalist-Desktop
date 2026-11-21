# freETarget Minimalist

An independent live scoring application for freETarget Minimalist electronic targets, with a customizable scoring dashboard, shooter profiles, session history, and competition-style practice. The ready-to-install Windows, macOS, and Android downloads are linked below. Source code and Arduino firmware files are also available for developers.

## Download freETarget Minimalist — ready to install

**Just want to use the program? Choose your device below.** These links download the actual application files directly. You do **not** need to understand GitHub, click the green **Code** button, or download a **Source code** ZIP.

### [Download Windows 64-bit (x64) installer — .exe](https://github.com/DaveStruve/freETarget-Minimalist-Desktop/releases/download/v0.3.11-beta.1/freETargetMinimalist-0.3.12-beta.1-Windows-x64-Setup.exe)

**Windows 10 / 11 (64-bit) · v0.3.12-beta.1** — Download the installer and run it.

### [Download Windows 32-bit (x86) installer — .exe](https://github.com/DaveStruve/freETarget-Minimalist-Desktop/releases/download/v0.3.11-beta.1/freETargetMinimalist-0.3.12-beta.1-Windows-x86-Setup.exe)

**Windows 10 (32-bit) · v0.3.12-beta.1** — Download the installer and run it.

### [Download Mac (Intel or Apple Silicon) — Signed & Notarized ZIP](https://github.com/DaveStruve/freETarget-Minimalist-Desktop/releases/download/v0.3.11-beta.1/freETarget-Minimalist-0.3.11-beta.1-macOS-Notarized.zip)

**macOS 13 Ventura or later · v0.3.11-beta.1** — Download the ZIP, extract it, and drag freETarget Minimalist into Applications. Signed by STRUVEDESIGNS LLC and notarized by Apple, with the ticket stapled. The clean build passed Gatekeeper and all pre-distribution checks.

### [Download Android (phone or tablet) — APK](https://github.com/DaveStruve/freETarget-Minimalist-Desktop/releases/download/v0.3.11-beta.1/freETarget-Minimalist-Android-0.2.3-beta.1.apk)

**Android 11 or later · v0.2.3-beta.1 (build 5)** — Download the APK on your device and follow Android's installation prompts. Android may ask you to allow installation from your browser or file manager. **The previous version was tested in an emulator; this update still needs physical-device, connectivity and voice testing.**

**After installing:** See the **[Wi-Fi setup guide for Windows, Mac, and Android](docs/WIFI_SETUP.md)** to connect to your freETarget in Access Point or Station Mode.

[See the current v0.3.11 release and all its assets](https://github.com/DaveStruve/freETarget-Minimalist-Desktop/releases/tag/v0.3.11-beta.1) · [View all releases](https://github.com/DaveStruve/freETarget-Minimalist-Desktop/releases) · [Optional Arduino firmware source](firmware/arduino-mega/)

> **For developers:** GitHub's automatic **Source code** ZIP/TAR downloads contain source code, **not installers**. Build instructions are farther down this page. Windows x64/x86 v0.3.12-beta.1 and macOS v0.3.11-beta.1 downloads are published.

## Connect to your target over Wi-Fi (Windows, macOS, Android)

freETarget Minimalist supports **two Wi-Fi connection modes on Windows, macOS, and Android**:

| | Access Point Mode | Station Mode |
| --- | --- | --- |
| **Network** | The **target creates its own Wi-Fi network**; connect your computer/phone directly to it. No router needed. | The **target joins your home or club Wi-Fi network**; your computer/phone must be on the same reachable network. |
| **Target IP** | **`192.168.10.9`** with the included firmware | **Assigned by your router**; find the target's current IP |
| **TCP port** | **`1090`** | **`1090`** |

**Access Point — quick setup:** Turn on the target in AP Mode, join its **`FET-` Wi-Fi network** from your Windows/Mac/Android system Wi-Fi settings, then open **Settings → Connection → Wi-Fi / TCP → Access Point Mode** in freETarget Minimalist. Save and select **Connect Target**. The included firmware's AP network has no password; your device may warn that it has no internet.

**Station — quick setup:** First configure the **target itself** with your existing Wi-Fi SSID and password. Restart the target, find its **router-assigned IP address**, and connect your Windows/Mac/Android device to the same local network. In freETarget Minimalist, open **Settings → Connection → Wi-Fi / TCP → Station Mode**, enter the target's IP and port **1090**, save, and select **Connect Target**.

**Important:** Choosing AP or Station in the **app does not change the target's Wi-Fi mode or credentials**. You must configure the target separately when switching modes. Windows/macOS provide an **Arduino Terminal** for target commands; the Android beta requires target configuration from a computer or compatible serial terminal.

**[Read the full cross-platform Wi-Fi setup guide](docs/WIFI_SETUP.md)** for target configuration commands, finding the Station IP, switching modes, and troubleshooting. The guide covers **Windows, macOS, and Android**, with platform-specific notes.

## What's new in the committed source

**Windows 0.3.12-beta.1 / Android 0.2.3-beta.1 source refresh — November 21, 2026:** Updated branding, circular color swatches, stacked Wi-Fi mode text and additional languages including Arabic. Windows gains target pinch/pan controls; Android restores optional Demo Mode and corrects its Gradle/JDK configuration. USB and Wi-Fi remain supported. See the [Windows build guide](desktop/windows/README_WINDOWS_BUILDS.md) and [Android build guide](android/README.md). Windows x64 and x86 0.3.12-beta.1 installers are now published at the download links above, including the automatic-backup filename collision fix. The signed Android 0.2.3-beta.1 APK is also published. Its package ID and signing certificate match 0.2.2-beta.1, and its version code increases to 5; device testing remains pending.


**Windows and macOS — 0.3.11-beta.1**

Mac source refresh (November 21, 2026): updated logo, iCloud profile/session sync code, and dedicated signed-build/notarization scripts. The maintainer's clean build passed Gatekeeper and all pre-distribution checks. See the [Mac source and signing instructions](desktop/macos/README.md).

- All six dashboard widgets offer **Small** and **Large** sizes. Large is the default, and existing layouts retain their saved sizes.
- An idle shot can prompt you to start a session. Accepting carries the shot into the session; the opening stage determines whether it is scored. The prompt can be disabled in **Settings → General**.
- macOS adds pinch-to-zoom and drag-to-pan on the live target, with a zoom percentage control to reset the view.
- Windows includes separate x64 and x86 application and Inno Setup installer build scripts.

**Android — 0.2.2-beta.1**

- Android source for phones and tablets, with layouts adapted to each screen.
- Wi-Fi/TCP and USB serial connection code.
- On-device profiles, guns, history, and settings.
- Live target zoom and pan, session controls, and connection diagnostics.

**Arduino Mega 2560 firmware — source now included**

- The complete published Wi-Fi-fix / LED Pin 13 firmware source is available in [`firmware/arduino-mega/`](firmware/arduino-mega/), including the Arduino sketch, headers, and original package notes.
- Includes ESP-01 Station Mode connectivity fixes, Access Point Mode support, and LED PWM set to **pin 13** rather than pin 5.
- This is an **optional firmware update**. No compiled firmware image or new hardware-test result is included.

The Android APK has been **tested successfully in an Android emulator** by the project maintainer. Testing on a physical Android phone or tablet—including real-target Wi-Fi and USB connectivity—is still pending. Desktop feature parity is not assumed. The Windows x64/x86 v0.3.12-beta.1 installers and macOS v0.3.11-beta.1 application have been published; additional hardware testing may still be needed. Android features and limitations are documented in the [Android README](android/README.md).

## Application features

- Live target display, shot scores, and recent-shot direction indicators.
- Shot-density heatmaps for live targets, saved-session reviews, and statistics. Add the live Heatmap widget through **Edit Widgets**, or enable the target overlay. The live target overlay looks back across the current session (10 shots by default); **Heatmap settings** lets you select 1–100 shots or all shots. Recorded misses count toward the lookback, synthetic shots do not, and sighting and record shots are separate. The history overlay shows the displayed series; the live widget shows all record shots (or all sighting shots during sighting). History also offers a whole-session heatmap. The Statistics heatmap combines available shots from all sessions selected by its filters; summary-only sessions cannot contribute shots. **Heatmap settings** also adjusts resolution and hotspot peakiness across all views. Colors are relative to each view; misses and synthetic shots are excluded from the density.
- Editable dashboard widgets, customizable appearance, and optional spoken scores.
- Shooter profiles with multiple guns and session tracking by gun.
- Saved sessions, statistics, and performance comparisons.
- Competition-style practice sessions using live target data.
- Desktop Wi-Fi/TCP and USB connectivity.

Feature availability varies by platform and version. Android is developed separately; desktop feature parity is not assumed.

## Source code and building

The application and Arduino Mega firmware source imports are complete.

| Project | Committed source version | Build documentation |
| --- | --- | --- |
| [Windows x64 and x86](desktop/windows/) | 0.3.12-beta.1 (x64 and x86 installers published) | [Windows build and installer instructions](desktop/windows/README_WINDOWS_BUILDS.md) |
| [macOS Universal](desktop/macos/) | 0.3.11-beta.1 | [Mac Universal build instructions](desktop/macos/BUILD_UNIVERSAL_MAC.md) |
| [Android](android/) | 0.2.3-beta.1 — versionCode 5 (signed APK published) | [Android build and connection instructions](android/README.md) |
| [Arduino Mega firmware](firmware/arduino-mega/) | Wi-Fi fixes / LED PWM pin 13 | [Firmware build and flashing instructions](firmware/arduino-mega/README.md) |

Build from each platform's directory to preserve the relative paths expected by its scripts. Windows and macOS retain separate source snapshots with platform-specific changes. Experimental iOS preview files are preserved inside the Mac source; no iOS release is published here.

See [source provenance](docs/SOURCE_IMPORT.md), the [changelog](CHANGELOG.md), and [release instructions](docs/RELEASING.md). Committed source does not establish that a new installer has been compiled or tested.

## For developers: installer build files

These links go directly to the **installer configuration or platform build folders in this repository**. They contain source and build scripts, **not ready-to-install programs**. Use the download links above for currently published installers.

| Platform | Installer / build folder | Build script or configuration | Installer output after a local build |
| --- | --- | --- | --- |
| Windows 64-bit (x64) | [Windows installer folder](desktop/windows/installer/) | [Build x64 installer](desktop/windows/BUILD_AND_INSTALL_X64.bat) · [x64 Inno Setup file](desktop/windows/installer/freETargetDesktop.iss) | `desktop/windows/release/installer/` |
| Windows 32-bit (x86) | [Windows installer folder](desktop/windows/installer/) | [Build x86 installer](desktop/windows/BUILD_AND_INSTALL_X86.bat) · [x86 Inno Setup file](desktop/windows/installer/freETargetDesktop-x86.iss) | `desktop/windows/release-x86/installer/` |
| macOS Universal | [Mac application/build folder](desktop/macos/) | [Build Mac application](desktop/macos/BUILD_MAC.command) | `desktop/macos/release/mac/` |
| Android | [Android Studio project folder](android/) | [Android app module](android/app/) · [Gradle build configuration](android/app/build.gradle) | `android/app/build/outputs/apk/` |

The output directories shown in the last column are created **on your computer after building**; they are not uploaded GitHub folders. For both Windows architectures in one run, use [BUILD_AND_INSTALL_BOTH.bat](desktop/windows/BUILD_AND_INSTALL_BOTH.bat). For installation-ready downloads, see [GitHub Releases](https://github.com/DaveStruve/freETarget-Minimalist-Desktop/releases).

## Arduino Mega 2560 firmware (optional)

The **firmware source is now part of this repository**, not just a ZIP attached to a release. Browse the [firmware project folder](firmware/arduino-mega/), open the [main Arduino sketch](firmware/arduino-mega/freETarget/freETarget.ino), or read the [firmware build and flashing guide](firmware/arduino-mega/README.md). The published [firmware source ZIP](https://github.com/DaveStruve/freETarget-Minimalist-Desktop/releases/download/v0.3.11-beta.1/freETarget-Minimalist-Arduino-Mega-WiFi-Fix-LED-Pin13-Source.zip) remains available for download.

This version addresses a Wi-Fi issue that **prevented Station Mode from connecting reliably** to an existing wireless network. It also includes related Wi-Fi communication and connection-handling fixes:

- Improved Station Mode initialization and DHCP/IP-address handling, including waiting for complete ESP responses and verifying that a valid, nonzero IP address is assigned before starting the TCP server.
- Corrected dropped incoming data during sends, receive-buffer overreads, incomplete ESP response/IP parsing, and Wi-Fi credential-buffer handling. The firmware retains its 16-character password limit and rejects longer passwords.
- Preserved Access Point Mode and TCP communication on port **1090**.

The package also configures **LED PWM on pin 13**, matching the hardware wiring used for this build (rather than the original pin 5). This LED pin change is separate from the Wi-Fi fixes. A [wiring diagram](https://github.com/DaveStruve/freETarget-Minimalist-Desktop/releases/download/v0.3.11-beta.1/freETarget-Minimalist-Arduino-Mega-WiFi-LED-Wiring-Diagram.jpeg) is included in the [published release](https://github.com/DaveStruve/freETarget-Minimalist-Desktop/releases/tag/v0.3.11-beta.1).

**Firmware installation is optional.** To compile it yourself, open `firmware/arduino-mega/freETarget/freETarget.ino` in Arduino IDE and select **Arduino Mega 2560**. Verify your target's wiring, especially LED PWM pin 13, before uploading. If your target already connects and operates reliably, you can continue using your existing firmware. No precompiled HEX file is provided.

## Reporting issues

[Open a GitHub issue](https://github.com/DaveStruve/freETarget-Minimalist-Desktop/issues/new/choose) with the application version, operating system, connection method, steps to reproduce, and relevant diagnostics. Remove personal information from attachments.

## Credits

The [original freETarget project](https://github.com/ten-point-nine/freETarget) by ten-point-nine and its contributors provided the original firmware and PC application. The [freETarget Minimalist hardware and Arduino adaptation](https://free-e-target.com/freeetarget-minimalist/) was published by [stoeckli](https://github.com/stoeckli/freETarget). Preserve the existing [LICENSE](LICENSE) and all platform-specific third-party notices and licenses.
