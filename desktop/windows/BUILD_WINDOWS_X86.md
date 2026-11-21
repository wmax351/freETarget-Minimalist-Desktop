# Build freETarget Minimalist 0.3.12-beta.1 for 32-bit Windows 10

You can build the x86 portable app on a 64-bit Windows 11 PC.

1. Open https://www.python.org/downloads/release/python-31210/ and choose **Windows installer (32-bit)** under **Files**. Keep or install the Python launcher. Your existing 64-bit Python can stay installed.
2. Extract the entire source ZIP. Open the resulting folder in File Explorer, type `cmd` into the address bar, and press Enter.
3. Verify the interpreter. The command should print `32`.

   ```bat
   py -3.12-32 -c "import struct; print(struct.calcsize('P') * 8)"
   ```

4. From that same Command Prompt, start the build. Internet access is needed to download the build dependencies.

   ```bat
   BUILD_WINDOWS_X86.bat
   ```

   If the launcher cannot find the x86 interpreter, substitute its actual path and run
   `"C:\path\to\32-bit\python.exe" tools\windows_tasks.py build-x86`.

5. Find the portable ZIP at `release-x86\freETargetMinimalist-0.3.12-beta.1-Windows-x86.zip`. Extract the entire portable ZIP on the destination PC and open `freETargetMinimalist.exe` inside the extracted folder. Keep the `_internal` folder alongside it.

The destination PC needs Microsoft Edge WebView2 Runtime and .NET Framework 4.8.
If WebView2 is missing on a 32-bit Windows 10 PC, download the x86 Evergreen
Standalone Installer from https://developer.microsoft.com/microsoft-edge/webview2/.
The portable app bundles Python.

Before sharing, open the app on a 32-bit Windows 10 machine and verify that the
main window renders and that your normal connection method works. This source
package produces a portable ZIP. BUILD_INSTALLER.bat is for the existing x64 installer.
