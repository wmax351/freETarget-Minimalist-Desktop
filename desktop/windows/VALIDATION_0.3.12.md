# Validation — 2026-11-21

Windows portable checks: 72 Python tests passed (including fixed-clock backup collision regression). Full Node UI/session/competition,
statistics, storage bridge and migration regression suites passed. Target gestures
passed: pinch, pinch-to-pan, bounded mouse pan, pointer release, Ctrl+wheel zoom,
normal scroll and zoom limits. JavaScript syntax, unique HTML IDs and language
options checked on both platforms.

Android JavaScript adapter checks passed: persisted Demo Mode, tablet detection,
version, navigation theme updates, Wi-Fi/USB request routing, events and external
request rejection. Native Android source changes have not been compiled here.

Windows installers cannot be built in this Linux environment. Android SDK is not
installed here, and Gradle distribution download failed with Network is unreachable.
No APK or Windows EXE from this source refresh was generated or tested here.
Build natively and test saved data, physical target USB/Wi-Fi and voice playback
before replacing the currently published binaries.
