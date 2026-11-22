# Implementation notes

The v1.7.9 HTML/JavaScript UI runs in pywebview with EdgeChromium forced. The original `freetarget_bridge.py` is retained byte-for-byte and runs in the same process. A localhost-only HTTP server on a random port serves the window and delegates the original hardware endpoints. No target firmware changes or automatic device connection were added.

SQLite is the authoritative data store. The desktop bootstrap provides the UI's synchronous Storage interface from a validated initial snapshot. Each mutation makes a synchronous local request; the server commits a SQLite transaction before acknowledging it. Failed writes preserve the cache and propagate errors to existing UI save handlers. A global revision prevents stale overwrites. This intentionally preserves original JSON data formats and scoring logic. The synchronous local call may briefly block rendering during disk writes; large histories should be measured on Windows.

The webview origin can change each launch without losing records. The desktop logo store uses the same SQLite adapter. Browser migration uses a separate read-only helper at the original browser origin, including IndexedDB's custom logo; it creates a JSON download without posting those records to the helper server.

Local requests require the expected Host/Origin and a per-run token. The HTML URL contains a separate secret path; API calls use a session header. The app is bound to loopback, does not expose generic file reads, and provides no CORS access. This is local-process isolation, not a boundary against malware running as the user. Backup files are plain JSON and are not encrypted. Native file dialogs select imports/exports, restore uses a ten-minute staged preview and rechecks the data revision, target connection and session state.

The native closing event is cancelled synchronously; JavaScript preparation and confirmation then run on a worker thread to avoid blocking the GUI while evaluating JavaScript. Committed records remain on disk. Shutdown stops bridge/exporter/server, attempts a final backup and checkpoints SQLite. A per-data-folder OS lock prevents concurrent app writers.

## Developer checks

From this directory, with Python 3.10–3.13:

```
python -m unittest discover -s tests -p "test_*.py" -v
node tests/test_portable_sync_core.cjs
python tests/run_ui.py
```

The Python command uses only Python's standard library and simulated USB/TCP devices. The sync-core check uses Node 18+ and no npm packages. The UI command also needs Node 18+ and uses deterministic DOM/audio mocks with the real UI code and embedded WAVs. Neither command proves native WebView2 rendering, real audio latency or hardware behavior.

`tools/prepare_assets.py` records the changes applied to an unmodified v1.7.9 UI. It is a developer conversion tool, not a launch step; its baseline assertion prevents reapplying it to the prepared desktop asset. The actual launch asset is `app/assets/index.html`. `desktop_data.html` and `desktop_ui.js` are source fragments embedded into that file. `desktop_bootstrap.js` is injected dynamically by the local server.

## Packaging

Run BUILD_WINDOWS.bat on Windows x64. Dependencies are pinned in requirements files. PyInstaller's spec collects pywebview resources, serial support and assets. The optional Inno Setup script installs per user and does not remove the separate data directory. Generated artifacts are unsigned. No CI runner or Windows signing certificate is included.

Useful upstream documentation:

- pywebview: https://pywebview.flowrl.com/api/
- Packaging: https://pywebview.flowrl.com/guide/freezing.html
- PyInstaller: https://pyinstaller.org/en/stable/operating-mode.html
- SQLite: https://docs.python.org/3/library/sqlite3.html

The source package retains the baseline README, including voice-cue provenance and event references. Existing project and third-party licensing obligations continue to apply; no new license for the original project is asserted here.

## 0.3.5 source-of-truth note

The shipping desktop UI is `app/assets/index.html`. The older `desktop_ui.js` / `desktop_data.html` fragments and `tools/prepare_assets.py` document the original conversion workflow; running the old preparation script on this release may overwrite newer 0.3.5 UI features. Do not regenerate `index.html` from those fragments without first porting the changes.
