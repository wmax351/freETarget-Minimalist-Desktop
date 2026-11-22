# freETarget Minimalist Beta 0.1.0 — portable Windows release

This document is copied into the portable release by BUILD_WINDOWS.bat. The source package itself does not include a compiled executable.

Extract the whole portable ZIP and double-click **freETargetMinimalist.exe**. Keep its `_internal` folder beside it. Windows 10/11 x64, Microsoft Edge WebView2 Runtime and .NET Framework 4.8 are required; Python is not required for the compiled release.

The app runs the existing TCP/USB bridge internally. Choose your connection in Settings, then Connect. Retain your usual USB serial driver. Stop any old bridge that is connected to the same target.

Records are stored separately in `%LOCALAPPDATA%\freETarget\DesktopBeta`. Replacing the executable folder keeps profiles, guns, History, settings and custom logos. Use **Settings → General → Export Backup** to save a copy elsewhere. Automatic/pre-restore copies are in the data folder's `backups` directory; the latest 30 are retained. Unlogged shots are not saved by backup.

## Sync with Android

Sync is a manual file exchange, not cloud sync. Finish or discard the current session and disconnect the target first. In **Settings → General**, choose **Export Sync File** on one device, transfer the JSON file, then choose **Import & Merge Sync File** on the other. Export again there and import that file back to carry merged changes to the first device.

Profiles and saved sessions are merged; differing profile versions and portable settings require confirmation. Items absent from the file are kept, so deletions are not propagated. Connection details remain local to each device. Sync files are unencrypted JSON; keep them somewhere private and delete transfer copies when no longer needed. Files larger than 32 MB are not accepted.

To migrate old browser data, choose **Export Existing Browser Data** in General, then open `http://127.0.0.1:8765/` in the original browser/profile (use `localhost` instead if that was your original address). Stop the old bridge first. Download the browser backup, then select it using **Restore / Migrate Data** in the desktop app. Finish/log or discard any current session and disconnect the target first. Review the counts before replacing data. Restore replaces all desktop data and saves a copy of the previous records first. The browser copy is preserved.

Five-Shot Standard retains the existing voice cues and manual review of delayed, early or late reports. The desktop wrapper does not make its timing competition certified. Test Commands and verify your Windows speaker output before using a sequence.

For startup problems, check WebView2/.NET and `%LOCALAPPDATA%\freETarget\DesktopBeta\logs\desktop.log`. Only one instance may use the data folder. Do not delete the database as a troubleshooting step; keep an exported backup. Native Windows and real-target acceptance status depends on the build's test record.

WebView2: https://developer.microsoft.com/microsoft-edge/webview2/

.NET Framework 4.8: https://dotnet.microsoft.com/download/dotnet-framework/net48
