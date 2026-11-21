freETarget Minimalist 0.3.12-beta.1 — Windows x86 build and installer

1. Install Python 3.12 (32-bit), and verify: py -3.12-32 -c "import struct; print(struct.calcsize('P')*8)"  (must print 32).
2. Install Inno Setup 6 from https://jrsoftware.org/isinfo.php
3. Double-click BUILD_AND_INSTALL_X86.bat (or build separately with BUILD_WINDOWS_X86.bat and CREATE_INSTALLER_X86.bat).
4. Find the installer under release-x86\installer\.

This archive contains source and scripts, NOT a precompiled installer. The build needs Windows, network access for dependencies, and must pass tests. The 32-bit build and installer have not been executed in this environment; test on a real Windows 10 x86 computer.
The existing installer/freETargetDesktop.iss and BUILD_INSTALLER.bat are for x64, not x86.
