# Changelog

## Windows 0.3.12-beta.1 / Android 0.2.3-beta.1 — source refresh, 2026-11-21

- Updated default logos/icons, circular color swatches and spacing, and stacked Wi-Fi mode descriptions.
- Added Korean, Turkish, Vietnamese and Arabic UI/score-language options, and Brazilian Portuguese speech locale handling. Voice availability requires device testing.
- Windows: main-target touchscreen/precision-touchpad pinch and bounded mouse/touch pan; x64/x86 app, installer and executable version metadata updated. Installation IDs and app-data paths retained.
- Android: versionCode 5; optional Demo Mode restored with separate demo history. Disabled whole-WebView zoom while preserving main-target pinch/pan, portrait phone and tablet layouts.
- Android: Gradle 8.9 for AGP 8.7.3; removed generated Java 25 daemon and unused resolver configuration. Use JDK 17 in Android Studio.
- Wi-Fi/TCP and USB retained on both platforms. iCloud sync remains Apple-only.
- New Windows installers and signed Android APK require native builds and verification; existing public downloads remain available.

## macOS source refresh — 2026-11-21

- Updated Mac branding and added iCloud Documents profile/session sync code with manual sync and optional automatic sync while idle.
- Added signed-build and notarization commands. Signing identifiers are resolved from the embedded provisioning profile; Mac App ID and shared container are checked before packaging.
- Excluded dependency test fixtures and debug symbols from bundled license notices.
- Added signing-profile tests; 91 portable Python tests passed.
- The maintainer's clean Mac build passed notarization, stapler, Gatekeeper and system-policy checks, and was reported working in testing. The verified [signed and notarized Mac ZIP](https://github.com/DaveStruve/freETarget-Minimalist-Desktop/releases/download/v0.3.11-beta.1/freETarget-Minimalist-0.3.11-beta.1-macOS-Notarized.zip) is now published on the v0.3.11-beta.1 release; README and release download links point to it.

## Unreleased — source imported, 2026-11-16

- Imported the published Arduino Mega Wi-Fi/LED Pin 13 firmware source into [`firmware/arduino-mega/`](firmware/arduino-mega/), including all original `.ino` and `.h` files and the original package notes. The firmware remains optional; no new HEX or hardware-test result was produced.

- Committed Windows x64/x86 and macOS Universal source v0.3.11-beta.1, with build scripts, installer configurations, tests, and assets.
- Committed Android source v0.2.2-beta.1 (versionCode 4), including Wi-Fi/TCP and USB serial connection code.
- Updated the project and platform documentation to reflect completed source import.
- Added direct links to the published Windows installer and macOS Universal ZIP.
- Documented the newer desktop source changes: Small/Large widget sizes, the idle-shot session prompt, and Mac target zoom/pan.

Published desktop downloads remain v0.3.10-beta.1. No new installer, APK, release tag, or device-testing result is implied by this documentation update.

## Unreleased — repository setup

- Expanded the project README to cover Windows x64, Windows x86, macOS, and Android.
- Added desktop and Android source destinations with explicit import status.
- Added source import instructions, release guidance, and a beta release note template.
- Added ignore rules for generated output, local configuration, signing material, and common data files.
- Added bug report and pull request templates.

The repository setup was followed by the application source import recorded above. New builds, hardware testing, and release assets remain pending.

## Desktop 0.3.10-beta.1

Existing published beta: [release and downloads](https://github.com/DaveStruve/freETarget-Minimalist-Desktop/releases/tag/v0.3.10-beta.1).

The original release contains the Windows installer, macOS Universal ZIP, and optional firmware source and wiring diagram. Its tag and assets are retained.
