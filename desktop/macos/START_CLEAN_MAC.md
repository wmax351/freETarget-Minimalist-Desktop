# freETarget Minimalist — clean Mac rebuild

This is a fresh source copy of 0.3.11-beta.1 with the current logo, target controls,
and Apple device sync code. No old build outputs, virtual environments, tickets,
certificates, credentials, or provisioning profiles are included.

The maintainer's clean rebuild passed notarization, stapler, Gatekeeper and all
system-policy pre-distribution checks on November 21, 2026. Every new build must
still be signed, notarized and tested on a Mac.

## 1. Extract into a new folder

For a repository checkout, open desktop/macos. For the standalone clean source ZIP,
open its freETarget-Mac-Clean-Source folder instead. Adjust the path below to match.
Use a fresh checkout or extraction when starting over.
Open Terminal and run:

```bash
cd "$HOME/Downloads/freETarget-Minimalist-Desktop/desktop/macos"
chmod +x BUILD_SIGNED_MAC.command NOTARIZE_MAC.command
```

Keep the same Developer ID certificate and private key in your Mac's Keychain.
Keep `freETarget_Mac_iCloud.provisionprofile` in Downloads. Existing Keychain
credentials named `freETarget-notary` can be reused. Do not revoke or recreate them.

## 2. Build with signing and iCloud

```bash
./BUILD_SIGNED_MAC.command
```

The build uses a separate virtual environment inside this new folder. It derives
the application ID, team ID and production environment from your provisioning
profile and checks the Mac bundle ID and shared container before packaging.
License notices exclude dependency test fixtures and debug symbols.

Output: `release/mac/freETarget Minimalist.app`.
The ordinary build ZIP is signed but has not been notarized.

## 3. Submit and verify

Stay connected to internet Wi-Fi, then run:

```bash
./NOTARIZE_MAC.command
```

This submits the new ZIP, waits for Accepted, staples and validates the ticket,
and runs Gatekeeper plus system-policy checks. It stops on any failure.
Do not rebuild or re-sign the app between submission and verification.
Submission details are saved to `.build/notarization/result.json`.

Only after all checks pass, distribute:
`release/mac/freETarget-Minimalist-0.3.11-beta.1-macOS-Notarized.zip`.
If Gatekeeper rejects it, keep the result and app intact and report the output.
The script does not disable or bypass Gatekeeper.

## 4. Test

Extract the final ZIP on a second Mac and open normally in Finder. Test target
Wi-Fi/USB, zoom and pan, then iCloud profile/session sync with your iPhone/iPad.
All devices must use builds with the shared container and the same iCloud account.
Cross-device sync and native build behavior require real-device verification.

## Signing identifiers

- Bundle ID: `designs.struve.freetarget.desktop.preview`
- Developer team: `PKH73HWP3S`
- Shared iCloud container: `iCloud.designs.struve.freetarget.sync`

Public version remains 0.3.11-beta.1; this is a build-process refresh.
