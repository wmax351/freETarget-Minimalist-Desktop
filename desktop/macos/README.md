# freETarget Minimalist for macOS

Mac source version **0.3.11-beta.1**, with Universal support for Intel and Apple Silicon Macs, Wi-Fi/TCP and USB target connections, shooter profiles, session history, target zoom/pan, and the updated logo.

## Build and notarize

From this repository's `desktop/macos/` directory:

```bash
bash BUILD_SIGNED_MAC.command
bash NOTARIZE_MAC.command
```

The signed build requires a Developer ID Application identity and a Developer ID provisioning profile authorizing the shared iCloud container. Configure `FREETARGET_MAC_SIGN_IDENTITY` and `FREETARGET_MAC_ICLOUD_PROFILE` for your own team. The script defaults are the maintainer's local setup; certificates, private keys, profiles and passwords are not committed.

Notarization uses the local Keychain credential profile `freETarget-notary`, or `FREETARGET_NOTARY_PROFILE` when set. The script submits, staples, validates, then runs Gatekeeper and system-policy checks. It produces the distribution ZIP only after those checks pass.

For a local build without configured Developer ID signing, use `bash BUILD_MAC.command`. That alone does not create a notarized public release.

See [Universal build instructions](BUILD_UNIVERSAL_MAC.md) and [clean build walkthrough](START_CLEAN_MAC.md).

## Apple device sync

The Mac source uses the shared iCloud Documents container `iCloud.designs.struve.freetarget.sync`. Compatible Mac, iPhone and iPad builds signed by the same developer team can sync shooter profiles and saved sessions for the same iCloud account. Use Settings → Backup → Apple Device Sync to confirm the account, sync manually, and optionally enable automatic sync. Automatic sync runs while the app is open and idle; it is not an iOS background service.

Local data remains under `~/Library/Application Support/freETarget/DesktopBeta`. Back up records before upgrading. Independent developers must register and configure their own App IDs, shared container and profiles.

## Validation

On November 21, 2026 the maintainer reported that the clean Mac build passed stapler validation, Gatekeeper assessment (`Notarized Developer ID`), and all system-policy pre-distribution checks. The maintainer also reported the app working in testing. Portable automated checks: 91 Python tests passed; shell syntax checks passed. These results apply to that compiled build, not automatically to every rebuild.

The release asset is published separately from source commits. Use the [release page](https://github.com/DaveStruve/freETarget-Minimalist-Desktop/releases/tag/v0.3.11-beta.1) for currently available application downloads.

Experimental iOS preview sources in this directory are retained; the current iOS app is released separately. See `licenses/` and `THIRD_PARTY_NOTICES.md` for attribution.
