# freETarget Minimalist Android 0.2.3-beta.1 (version code 5)

The signed 0.2.3-beta.1 APK is published. It retains package designs.struve.freetarget.android and the signing certificate from 0.2.2-beta.1, with version code increased from 4 to 5. Physical-device, real-target and voice testing remain pending.

## Source refresh

- Updated logo and launcher icon.
- Circular color swatches with spacing; stacked Wi-Fi mode names/descriptions.
- Restored optional Demo Mode with separate demo history.
- Added Korean, Turkish, Vietnamese and Arabic UI/score-language options, plus Brazilian Portuguese speech locale handling. Native/device voice availability still needs hardware testing.
- Retained phone portrait lock, fixed navigation/theme backgrounds, target-only pinch/pan and tablet widget layout. USB host and Wi-Fi/TCP remain supported.
- Build configuration uses AGP 8.7.3, Gradle 8.9 and JDK 17; removed the generated Java 25 daemon override.

For a test build, open this directory in Android Studio, choose Gradle JDK **17**, install Android SDK Platform **35**, and run the app. For distribution, choose Build → Generate Signed App Bundle or APK → APK, and reuse your existing Android release keystore and key alias. Do not create a different key for an update.

Command-line checks: `./gradlew testDebugUnitTest lintDebug assembleDebug`. Release lint: `./gradlew lintVitalRelease`. Produce the signed release APK in Android Studio.

Android remains device-local; this update does not add iCloud or cross-platform cloud sync.


The Android app connects directly to the target via Wi-Fi/TCP or USB serial and stores profiles, guns, history and settings on the device.

## Download and install the Android app

**[Download freETarget Minimalist Android v0.2.3-beta.1 (.apk)](https://github.com/DaveStruve/freETarget-Minimalist-Desktop/releases/download/v0.3.11-beta.1/freETarget-Minimalist-Android-0.2.3-beta.1.apk)**

This is the **ready-to-install Android APK**. You do **not** need Android Studio or the repository source code. On your Android 11+ phone or tablet, open the downloaded APK and follow the installation prompts. Android may ask you to allow installation from the browser or file manager. The previous APK passed emulator testing; this update still requires physical-device, connectivity and audio testing.

To connect to a target, follow the [Wi-Fi setup guide for all platforms](../docs/WIFI_SETUP.md).

## Build from source (developers only)

1. Clone or download this repository and open its `android/` folder in Android Studio.
2. The build declares JDK 17, Android SDK Platform 35, Android Gradle Plugin 8.7.3, and Android 11 or later (minSdk 30). The wrapper is set to Gradle 8.9. Select JDK 17 in Android Studio's Gradle settings; the old Java 25 daemon override is removed.
3. Select a connected Android 11 or later phone or tablet and click **Run**. For a sideloadable debug APK, use **Build APK(s)** or run `./gradlew :app:assembleDebug` from the project directory with Gradle 8.9 installed. The file is written to `app/build/outputs/apk/debug/app-debug.apk`.

## Mobile layout

Phones request portrait and use the top Dashboard and bottom icon navigation. Tablets use a left sidebar, may rotate, and remember widget sizes separately in portrait and landscape. On phones the top bar includes Play/Pause, Next Stage and Log. Pinch on the main target to zoom, then drag with one finger to pan. The target overlays fade after shots if enabled in Settings → Appearance. Tablets fit Previous Target to its content in landscape. The target connection settings offer Station and Access Point modes USB serial, and connection diagnostics. The optional prompt to start a session after a detected shot is under **Settings → General**. Accepting the prompt carries that shot to the target and scores it only if the opening stage accepts shots.

## Wi-Fi connection guides

The **[shared Wi-Fi setup guide for Windows, macOS, and Android](../docs/WIFI_SETUP.md)** is the main reference for Access Point vs Station Mode, target-side Wi-Fi configuration, and troubleshooting. The steps below focus on the **Android-specific controls**.

## Wi-Fi connection setup (first connection)

The Android app connects **to the target**, not to the router on the target's behalf. Selecting **Station Mode** or **Access Point Mode** in the app changes the address the app connects to; **it does not change the target's firmware Wi-Fi mode or network credentials**. The target must already be operating in the matching mode.

Both modes use **Settings → Connection → Connection method: Wi-Fi / TCP** in the Android app.

### Option A — Access Point Mode (direct connection, no router)

Use this when you want your phone or tablet to connect directly to the freETarget, including where no home/club Wi-Fi is available.

1. Power on the freETarget and wait for its Wi-Fi module to initialize. On the Arduino Mega firmware included in this repository, an **empty** `WIFI_SSID` setting enables Access Point Mode. If the target was previously configured for Station Mode, see **Changing the target's Wi-Fi configuration** below.
2. On your Android device, open **Android Settings → Wi-Fi** and join the target's network. With the included firmware its name is **`FET-<target name>`** (for example, `FET-TARGET`). The included firmware configures this as an **open network (no Wi-Fi password)**; other firmware builds may differ.
3. Android may warn that this Wi-Fi network **has no internet access**. Choose to stay connected / use the network anyway if prompted. The target's Wi-Fi is for scoring, not internet browsing.
4. Open freETarget Minimalist → **Settings → Connection**. Choose **Wi-Fi / TCP**, then **Access Point Mode**. The app automatically sets and locks **Target IP: `192.168.10.9`** and **TCP port: `1090`**.
5. Tap **Save connection**, return to the dashboard, and tap **Connect Target**. Confirm that the app reports a connection and receives live shots.

### Option B — Station Mode (existing home or club Wi-Fi)

Use this when the target and your Android device should share an existing wireless network.

1. **First configure the target itself** to join your router's Wi-Fi (see below). With the included ESP-01 firmware, use a compatible **2.4 GHz** network. Power-cycle the target after saving its network credentials.
2. Connect the Android device to the **same local network** as the target. Avoid guest networks or router settings that isolate wireless devices from one another.
3. Find the target's **assigned IP address**. It comes from your router's DHCP server and is **not necessarily `192.168.10.9`**. Check the router's connected-device/DHCP list, or view the target's USB serial startup output; the included firmware reports `[WIFI] STA IP <address>:1090` when it joins successfully.
4. Open freETarget Minimalist → **Settings → Connection**. Choose **Wi-Fi / TCP**, then **Station Mode**. Enter the target's assigned **IP address** and **TCP port `1090`**.
5. Tap **Save connection**, then **Connect Target** on the dashboard. Confirm that the connection succeeds and shots appear.

### Changing the target's Wi-Fi configuration

**These steps apply to the Arduino Mega / ESP-01 firmware source included in this repository**, not necessarily to other freETarget firmware variants. The current Android beta does **not** provide target-side Wi-Fi credential editing. Use a computer connected to the target's USB serial interface and a compatible serial terminal (115200 baud), or another tool that can send configuration JSON to the target.

To make the target join an existing Wi-Fi network (**Station Mode**), send a JSON configuration command, replacing the example values:

```json
{"WIFI_SSID":"YourNetworkName","WIFI_PWD":"YourWiFiPassword"}
```

The included firmware stores these settings and uses them when Wi-Fi initializes. **SSID is limited to 32 characters and the Wi-Fi password to 16 characters** in this firmware; unsupported characters/escapes are rejected. If your normal network password is longer, use a separate compatible 2.4 GHz network rather than assuming it will work.

To return the target to its own Wi-Fi network (**Access Point Mode**), clear its saved SSID:

```json
{"WIFI_SSID":""}
```

**Power-cycle the target after either change.** Clearing the SSID selects Access Point Mode; it does not erase the previously stored password. The app's mode selection alone will not switch the target.

### Connection troubleshooting

- **Access Point:** Verify Android is actually connected to the `FET-` network, and choose **stay connected** if Android flags it as having no internet. Use `192.168.10.9:1090`.
- **Station:** Verify the target joined the router, check its **current** DHCP IP, and confirm both devices are on the same reachable local network. Use the target's assigned IP, not the Access Point default.
- **Either mode:** Check target power and Wi-Fi startup, TCP port **1090**, and the app's **Settings → Connection → Enable Wi-Fi / USB Diagnostics** option. Try **Use last successful connection** if you previously connected successfully.
- After connecting, log a session under a shooter and reopen **History** to confirm it was saved. Disconnect or power off the target to verify the app reports disconnection.

**Testing note:** The Android APK has been tested in an emulator. Wi-Fi communication with a physical freETarget and behavior on a real Android phone/tablet have not yet been validated.

## USB serial

1. Connect the target with a data-capable USB cable. Use a USB OTG adapter if needed. The Android phone or tablet must support USB host mode.
2. Choose **Settings → Connection → USB / Serial**, refresh the list, select the target, and save. The baud rate defaults to **115200**, with 8 data bits, no parity, and one stop bit.
3. Tap **Connect Target** and approve Android’s USB permission prompt if shown. After unplugging or reconnecting the cable, refresh the list if the previously saved port is unavailable.

The build uses [usb-serial-for-android](https://github.com/mik3y/usb-serial-for-android) and resolves it from JitPack on the first Gradle sync.

## Beta scope

- The app disconnects when it leaves the foreground. Reconnect when you return.
- The preview focuses on receiving live scores over Wi-Fi and USB. Target settings editing, the Arduino terminal, custom logo uploads, and Files backup import/export are outside this preview.
- Profiles and logged results stay on the installed device. Uninstalling or clearing app data removes them.
- **Testing status:** The project maintainer previously tested 0.2.2-beta.1 in an Android emulator. The 0.2.3-beta.1 build has not been run in this validation environment. Testing on a physical Android phone or tablet is still pending; real-target Wi-Fi/TCP and USB serial connectivity, permissions, audio, and device-specific behavior should be checked on hardware. Keep Android System WebView up to date. The APK is published under [GitHub Releases](https://github.com/DaveStruve/freETarget-Minimalist-Desktop/releases/download/v0.3.11-beta.1/freETarget-Minimalist-Android-0.2.3-beta.1.apk) as **freETarget-Minimalist-Android-0.2.3-beta.1.apk**. The APK contains a v2 signature and its signing certificate matches the previous published version.

## Credits

Based on the original [freETarget project](https://github.com/ten-point-nine/freETarget), the [freETarget Minimalist adaptation](https://free-e-target.com/freeetarget-minimalist/), and freETarget Minimalist Desktop. Upstream and third-party notices are included.
