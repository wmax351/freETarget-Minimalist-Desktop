"""Windows-only setup/build helper. It never changes the app data directory."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import pathlib
import platform
import shutil
import struct
import subprocess
import sys
import venv
import zipfile
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION = '0.3.12-beta.1'
PE_MACHINES = {'x86': 0x014C, 'x64': 0x8664}


def require_windows(architecture='x64'):
    if sys.platform != 'win32' or struct.calcsize('P') != {'x86': 4, 'x64': 8}[architecture]:
        raise RuntimeError(f'Use {architecture} Python on Windows 10/11.')
    if architecture == 'x86' and sys.version_info[:2] != (3, 12):
        raise RuntimeError('Use Python 3.12 x86 for the 32-bit build.')
    if not (3, 10) <= sys.version_info[:2] <= (3, 13):
        raise RuntimeError('Use Python 3.10–3.13 x64; Python 3.12 x64 is recommended.')


def require_pe_machine(path, architecture):
    with path.open('rb') as executable:
        if executable.read(2) == b'MZ':
            executable.seek(0x3C)
            offset = executable.read(4)
            if len(offset) == 4:
                executable.seek(int.from_bytes(offset, 'little'))
                pe_header = executable.read(6)
                if pe_header == b'PE\x00\x00' + struct.pack('<H', PE_MACHINES[architecture]):
                    return
    raise RuntimeError(f'{path} is not a Windows {architecture} executable.')


def environment(build=False, architecture='x64'):
    require_windows(architecture)
    folder = ROOT / ('.venv-x86' if architecture == 'x86' else '.venv')
    python = folder / 'Scripts/python.exe'
    if not python.exists():
        print('Creating a private Python environment in the extracted project folder…', flush=True)
        venv.EnvBuilder(with_pip=True).create(folder)
    require_pe_machine(python, architecture)
    requirement = ROOT / ('requirements-build.txt' if build else 'requirements-win.txt')
    subprocess.run([str(python), '-m', 'pip', 'install', '--disable-pip-version-check', '-r', str(requirement)], check=True)
    # A partially created environment is not a successful installation. Recheck
    # the runtime requirements on the next launch if setup was interrupted.
    (folder / 'runtime-ready.sha256').write_text(hashlib.sha256((ROOT / 'requirements-win.txt').read_bytes()).hexdigest(), encoding='ascii')
    return python


def launch(python):
    pythonw = python.with_name('pythonw.exe')
    subprocess.Popen([str(pythonw), str(ROOT / 'app/desktop.py')], cwd=ROOT)
    print('Desktop window is starting. Logs: %LOCALAPPDATA%\\freETarget\\DesktopBeta\\logs\\desktop.log')


def build(architecture='x64'):
    python = environment(build=True, architecture=architecture)
    release = ROOT / ('release-x86' if architecture == 'x86' else 'release')
    work = ROOT / ('.build-x86' if architecture == 'x86' else '.build')
    archive = release / f'freETargetMinimalist-{VERSION}-Windows-{architecture}.zip'
    subprocess.run([str(python), '-m', 'unittest', 'discover', '-s', str(ROOT / 'tests'), '-p', 'test_*.py', '-v'], cwd=ROOT, check=True)
    subprocess.run([str(python), '-m', 'PyInstaller', '--clean', '--noconfirm', '--distpath', str(release), '--workpath', str(work), str(ROOT / 'freETargetDesktop.spec')], cwd=ROOT, check=True)
    folder = release / 'freETargetMinimalist'
    exe = folder / 'freETargetMinimalist.exe'
    require_pe_machine(exe, architecture)
    if architecture == 'x86':
        loader = folder / '_internal/webview/lib/runtimes/win-x86/native/WebView2Loader.dll'
        require_pe_machine(loader, architecture)
    shutil.copy2(ROOT / 'RUN_DESKTOP.md', folder / 'README.md')
    freeze = subprocess.run([str(python), '-m', 'pip', 'freeze'], capture_output=True, text=True, check=True)
    (folder / 'BUILD_DEPENDENCIES.txt').write_text(freeze.stdout, encoding='utf-8')
    hashes = {str(path.relative_to(folder)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(folder.rglob('*')) if path.is_file()}
    manifest = dict(version=VERSION, architecture=architecture, built_at=datetime.now(timezone.utc).isoformat(), platform=platform.platform(), python=platform.python_version(), sha256=hashes)
    (folder / 'BUILD_MANIFEST.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as out:
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                out.write(path, pathlib.Path('freETargetMinimalist') / path.relative_to(folder))
    print('Portable Windows app:', folder)
    print('Portable ZIP:', archive)
    print('Run freETargetMinimalist.exe. Recipients do not need Python.')
    return folder


def installer():
    require_windows()
    if not (ROOT / 'release/freETargetMinimalist/freETargetMinimalist.exe').is_file():
        raise RuntimeError('Run BUILD_WINDOWS.bat first.')
    candidates = [shutil.which('ISCC.exe')]
    for var in ('ProgramFiles(x86)', 'ProgramFiles'):
        if os.environ.get(var):
            candidates.append(str(pathlib.Path(os.environ[var]) / 'Inno Setup 6/ISCC.exe'))
    compiler = next((path for path in candidates if path and pathlib.Path(path).is_file()), None)
    if not compiler:
        raise RuntimeError('Optional installer compiler not found. The portable app is ready; install Inno Setup 6 from jrsoftware.org and run BUILD_INSTALLER.bat if you want a Setup.exe.')
    subprocess.run([compiler, str(ROOT / 'installer/freETargetDesktop.iss')], cwd=ROOT, check=True)
    print('Installer generated in release/installer. It is unsigned until you apply your own signing certificate.')


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['setup', 'launch', 'build', 'build-x86', 'installer'])
    args = parser.parse_args(argv)
    try:
        if args.action == 'build':
            build()
        elif args.action == 'build-x86':
            build('x86')
        elif args.action == 'installer':
            installer()
        elif args.action == 'setup':
            launch(environment())
        else:
            require_windows()
            python = ROOT / '.venv/Scripts/python.exe'
            marker = ROOT / '.venv/runtime-ready.sha256'
            expected = hashlib.sha256((ROOT / 'requirements-win.txt').read_bytes()).hexdigest()
            if not python.exists() or not marker.is_file() or marker.read_text(encoding='ascii') != expected:
                python = environment()
            launch(python)
        return 0
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print('\nFAILED:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
