# Wi-Fi setup — Windows, macOS, and Android

This guide applies to **freETarget Minimalist for Windows, macOS, and Android** when connecting to a compatible freETarget target over **Wi-Fi / TCP**. The network details below describe the **Arduino Mega 2560 + ESP-01 firmware included in this repository**. Other firmware versions may use different network names, addresses, or configuration methods.

The **Windows and macOS desktop source** also supports the regular freETarget **ESP32 firmware 6.4.2** over TCP. That firmware uses the same AP address (`192.168.10.9`) and TCP port (`1090`), and the desktop app understands its shot packets and settings response. Android compatibility with the 6.4.2 packet format has not been verified.

## Choose a connection mode

| | Access Point (AP) Mode | Station (STA) Mode |
| --- | --- | --- |
| How it works | **The target creates its own Wi-Fi network.** Your computer/phone joins it directly. | **The target joins an existing Wi-Fi network.** Your computer/phone uses that same local network. |
| Router required | No | Yes (or another compatible Wi-Fi access point) |
| Wi-Fi network your device joins | The target's `FET-<target name>` network | Your home/club Wi-Fi |
| Target IP address | **`192.168.10.9`** with the included firmware | **Assigned by your router (DHCP)**; check the actual address |
| TCP port | **`1090`** | **`1090`** |

**Important:** Choosing **Access Point** or **Station** in the freETarget Minimalist *app* only selects how the app connects. It **does not reconfigure the target**. The target's firmware Wi-Fi settings must already match the selected mode.

## Regular freETarget ESP32 firmware 6.4.2

For the regular ESP32 target, the desktop app uses the same TCP endpoint as the included Minimalist firmware:

- **Access Point mode:** connect your computer to the target's `FET-<target name>` Wi-Fi network and select **Access Point Mode** in the app. The target listens at **`192.168.10.9:1090`**.
- **Station mode:** connect the target and computer to the same network, select **Station Mode**, and enter the target's current IP address with port **`1090`**.

The app's **Get Settings** action sends the firmware's `ECHO` request. Target-side Wi-Fi settings still need to be configured on the target; selecting a mode in the app does not change them. The updated response handling is based on the 6.4.2 source and a captured target log; it still needs to be retested against a physical target.

If an ECHO response omits or corrupts a setting, the target settings window lists it as unavailable instead of guessing its value. Motor controls remain disabled until all motor settings are present; other available settings can still be edited and verified.

## Access Point Mode — connect directly to the target

Best for portable use, ranges without a router, or initial setup.

1. **Set the target to AP Mode.** In the included Arduino firmware, AP Mode is selected when the stored `WIFI_SSID` value is empty. If the target was previously set to join your home Wi-Fi, see [Change the target's Wi-Fi mode](#change-the-targets-wi-fi-mode) below.
2. Power on the target and allow its ESP-01 Wi-Fi module to start.
3. On **Windows, macOS, or Android**, open the device's **system Wi-Fi settings** and join the network beginning with **`FET-`** (for example, `FET-TARGET`). In the included firmware, this is an **open Wi-Fi network without a password**. If your firmware differs, use its own network details.
4. If the device says **“No Internet”**, stay connected to the target's network. This is expected: the target provides scoring data, not internet access. Some phones may switch away from networks without internet; verify the `FET-` network remains selected.
5. Open **freETarget Minimalist → Settings → Connection**. Choose **Wi-Fi / TCP**, then **Access Point Mode**. The app uses **`192.168.10.9`**, port **`1090`**; these fields are locked in AP Mode.
6. Choose **Save connection**, then use **Connect Target** on the dashboard. Confirm the connected status and incoming live scores.

**Note:** In AP Mode, the computer/phone connects to the target's Wi-Fi network, **not** to your normal home/club Wi-Fi. You may temporarily lose internet access on that device.

## Station Mode — connect through an existing network

Best when you want the target and your computer/phone on the same home or club network.

1. **Configure the target's firmware** with the existing Wi-Fi network name (SSID) and password, as explained in [Change the target's Wi-Fi mode](#change-the-targets-wi-fi-mode). This is a **target-side setup step**, not merely an app selection. The included ESP-01 firmware needs a compatible **2.4 GHz Wi-Fi** network.
2. Restart/power-cycle the target so it joins the configured network.
3. **Find the target's current IP address.** It is assigned by the router's DHCP service and can change. Look in the router's connected-device/DHCP list, or use the target's USB serial startup output: the included firmware prints `[WIFI] STA IP <address>:1090` on a successful join.
4. Connect your **Windows computer, Mac, or Android device** to the same reachable local network as the target. Avoid guest Wi-Fi and client/AP isolation, which can block communication between devices.
5. Open **freETarget Minimalist → Settings → Connection**. Choose **Wi-Fi / TCP**, then **Station Mode**.
6. Enter the target's **actual assigned IP address** and TCP port **`1090`**. Choose **Save connection**, then **Connect Target**. Confirm incoming scores.

**Do not enter `192.168.10.9` just because it appears in the AP instructions.** That address is the included firmware's **direct AP address**, not its usual Station Mode address. If the Station IP changes after a router restart, update it in the app. A DHCP reservation in your router can help keep it stable.

## Change the target's Wi-Fi mode

The instructions here are for the **included Arduino Mega / ESP-01 firmware**, which stores `WIFI_SSID` and `WIFI_PWD` in the target's nonvolatile configuration.

**Windows and macOS:** Connect to the target first (for example via USB, or its current working Wi-Fi mode). Open **Arduino Terminal** in the desktop app and send the JSON command below; confirm the target-configuration warning. You can alternatively use a compatible USB serial terminal connected to the target at **115200 baud**.

**Android:** The current Android beta does not offer Arduino Terminal or target-side settings editing. Configure the target using a Windows/Mac computer or a compatible USB serial terminal before connecting from Android.

To make the **target join your home/club network (Station Mode)**, send a command using your network details:

```json
{"WIFI_SSID":"YourNetworkName","WIFI_PWD":"YourWiFiPassword"}
```

To make the **target create its own network again (Access Point Mode)**, clear the SSID:

```json
{"WIFI_SSID":""}
```

**Power-cycle the target after changing these settings.** Switching networks can immediately interrupt an existing Wi-Fi connection, so **USB is the safest way to recover or reconfigure the target** if you lose access.

Firmware-specific limits: the included source accepts an SSID of **up to 32 characters** and a Wi-Fi password of **up to 16 characters**. It rejects certain control/escaped characters. If your existing Wi-Fi password is longer, use a separate compatible 2.4 GHz network or change the network configuration; do not enter a truncated password. The included AP network is open, so use it only in an environment where that is appropriate.

## Platform-specific notes

| Platform | Where to set the connection | Notes |
| --- | --- | --- |
| **Windows (x64 / x86 source)** | **Settings → Connection → Wi-Fi / TCP** | Both AP and Station options are present. Desktop **Arduino Terminal** can send supported target JSON commands after a connection is established. |
| **macOS (Intel / Apple Silicon)** | **Settings → Connection → Wi-Fi / TCP** | Same AP and Station workflow as Windows. Desktop **Arduino Terminal** is available. |
| **Android (phone / tablet)** | **Settings → Connection → Connection method: Wi-Fi / TCP** | Choose AP or Station, save, then connect. Android may warn about the AP network having no internet. The APK has passed emulator testing; **physical-device and real-target Wi-Fi testing are pending**. |

The steps above apply to the application's Wi-Fi connection. **USB serial** is a separate connection method and does not require the target or device to be on Wi-Fi.

## Troubleshooting

- **Can't see the `FET-` network?** Confirm the target is powered on and actually configured for AP Mode. A target already in Station Mode will attempt to join its configured router instead.
- **Connected to `FET-`, but the app won't connect?** Confirm the device stayed on that Wi-Fi network; select AP Mode in the app and use **`192.168.10.9:1090`**.
- **Station Mode won't connect?** Confirm the target joined the router, verify its current IP, check the **2.4 GHz** network and credentials, and make sure the router isn't isolating clients.
- **App reports disconnected?** Check the target's power and network connection, then try **Settings → Connection → Enable TCP / USB Diagnostics** (wording varies slightly by platform). Use **Use last successful connection** if you have previously connected.
- **Changing modes locked you out?** Connect to the target over USB serial and restore the intended `WIFI_SSID`, or clear it for AP Mode, then restart.
- **Still no live scores?** Confirm the app says connected first, then check whether the target is actually reporting shots. A Wi-Fi connection alone does not prove scoring hardware is working.

See the [Android-specific setup and USB notes](../android/README.md) and [Arduino firmware source and build notes](../firmware/arduino-mega/README.md).
