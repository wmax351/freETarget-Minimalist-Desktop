"""macOS launch and native/universal2 packaging for freETarget Minimalist."""
from pathlib import Path
import argparse
import json
import os
import platform
import plistlib
import subprocess
import shutil
import sys
import sysconfig
import venv

ROOT = Path(__file__).resolve().parents[1]
APP_VERSION = '0.3.11-beta.1'
APP_NAME = 'freETarget Minimalist.app'
ARCH_CHOICES = {'arm64', 'x86_64', 'universal2'}
MACHO_MAGICS = {
    b'\xfe\xed\xfa\xce', b'\xce\xfa\xed\xfe',  # 32-bit Mach-O
    b'\xfe\xed\xfa\xcf', b'\xcf\xfa\xed\xfe',  # 64-bit Mach-O
    b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe',  # fat Mach-O
    b'\xca\xfe\xba\xbf', b'\xbf\xba\xfe',  # fat Mach-O (64-bit)
}
REQUIRED_UNIVERSAL_ARCHES = {'arm64', 'x86_64'}


def icloud_entitlements(profile, bundle_id):
    """Resolve required signing identifiers from an authorised Mac profile."""
    allowed = profile['Entitlements']
    team = allowed['com.apple.developer.team-identifier']
    app_id = allowed['com.apple.application-identifier']
    if app_id != team + '.' + bundle_id:
        raise ValueError('Provisioning profile does not match the Mac bundle identifier.')
    if 'OSX' not in profile.get('Platform', []) or not profile.get('ProvisionsAllDevices'):
        raise ValueError('Use a Developer ID provisioning profile for macOS distribution.')
    entitlements = plistlib.loads((ROOT / 'mac/icloud-entitlements.plist').read_bytes())
    for key in ('com.apple.developer.icloud-container-identifiers',
                'com.apple.developer.ubiquity-container-identifiers'):
        if not set(entitlements[key]).issubset(allowed.get(key, [])):
            raise ValueError('Provisioning profile does not authorise the shared iCloud container.')
    services = allowed.get('com.apple.developer.icloud-services', [])
    if services != '*' and 'CloudDocuments' not in services:
        raise ValueError('Provisioning profile does not authorise iCloud Documents.')
    entitlements['com.apple.application-identifier'] = app_id
    entitlements['com.apple.developer.team-identifier'] = team
    if 'com.apple.developer.icloud-container-environment' in allowed:
        entitlements['com.apple.developer.icloud-container-environment'] = allowed[
            'com.apple.developer.icloud-container-environment']
    return entitlements


def macho_arches(path):
    """Return the architecture slices in a Mach-O file, or None for other files."""
    path = Path(path)
    if not path.is_file():
        return None
    with path.open('rb') as source:
        if source.read(4) not in MACHO_MAGICS:
            return None
    result = subprocess.run(['lipo', '-archs', str(path)], text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError('Cannot inspect Mach-O binary %s: %s' % (path, result.stderr.strip()))
    return set(result.stdout.split())


def require_universal_python():
    """Reject Homebrew/single-arch Python before downloading build dependencies."""
    candidates = [Path(sys.executable), Path(sys.base_prefix) / 'Python']
    libdir = sysconfig.get_config_var('LIBDIR')
    library = sysconfig.get_config_var('LDLIBRARY')
    if libdir and library:
        candidates.append(Path(libdir) / library)
    inspected = set()
    macho_found = False
    for candidate in candidates:
        if not candidate.is_file():
            continue
        resolved = candidate.resolve()
        if resolved in inspected:
            continue
        inspected.add(resolved)
        arches = macho_arches(candidate)
        if arches is not None:
            macho_found = True
        if arches is not None and not REQUIRED_UNIVERSAL_ARCHES.issubset(arches):
            raise SystemExit(
                'Universal2 build requires both arm64 and x86_64 Python slices.\n'
                'Found %s in %s.\n'
                'Install the macOS universal2 Python 3.13 installer from '
                'https://www.python.org/downloads/macos/ and rerun BUILD_MAC.command.'
                % (', '.join(sorted(arches)), candidate)
            )
    if not inspected or not macho_found:
        raise SystemExit('Could not confirm a universal2 Python binary. Install Python 3.13 from python.org.')


def verify_universal_app(app):
    """Require both slices in every Mach-O inside the complete .app bundle."""
    app = Path(app)
    executable = app / 'Contents/MacOS/freETargetMinimalist'
    if not executable.is_file():
        raise RuntimeError('The expected .app executable was not produced: %s' % executable)
    count = 0
    for path in sorted(app.rglob('*')):
        if not path.is_file():
            continue
        arches = macho_arches(path)
        if arches is None:
            continue
        count += 1
        if not REQUIRED_UNIVERSAL_ARCHES.issubset(arches):
            raise RuntimeError(
                'Universal2 build is incomplete: %s has %s (requires arm64 and x86_64).\n'
                'Use a python.org universal2 Python and universal2-compatible dependency wheels.'
                % (path.relative_to(app), ', '.join(sorted(arches)))
            )
    if not count:
        raise RuntimeError('No Mach-O binaries found in built .app; cannot validate architecture.')
    if macho_arches(executable) is None:
        raise RuntimeError('The .app executable is not a Mach-O binary: %s' % executable)
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['launch', 'build'])
    action = parser.parse_args().action
    if sys.platform != 'darwin':
        raise SystemExit('Launch/build the Mac app on macOS; Apple binaries cannot be built in this Linux workspace.')
    if sys.version_info[:2] not in ((3, 12), (3, 13), (3, 14), (3, 15)):
        raise SystemExit('Use Python 3.12-3.15 for this preview (selected: %s).' % platform.python_version())

    requested_arch = os.environ.get('FREETARGET_MAC_ARCH') if action == 'build' else None
    if requested_arch and requested_arch not in ARCH_CHOICES:
        raise SystemExit('Invalid FREETARGET_MAC_ARCH=%s (choose arm64, x86_64, or universal2).' % requested_arch)
    if requested_arch == 'universal2':
        require_universal_python()

    profile = os.environ.get('FREETARGET_MAC_ICLOUD_PROFILE')
    identity = os.environ.get('FREETARGET_MAC_SIGN_IDENTITY')
    signing_plist = None
    if profile:
        if not identity:
            raise SystemExit('Set FREETARGET_MAC_SIGN_IDENTITY for the iCloud profile.')
        profile = Path(profile).expanduser().resolve()
        if not profile.is_file():
            raise SystemExit('Provisioning profile not found: %s' % profile)
        decoded = subprocess.run(['security', 'cms', '-D', '-i', str(profile)],
                                 check=True, capture_output=True)
        resolved = icloud_entitlements(plistlib.loads(decoded.stdout),
                                      'designs.struve.freetarget.desktop.preview')
        signing_plist = ROOT / '.build/mac-signing/entitlements.plist'
        signing_plist.parent.mkdir(parents=True, exist_ok=True)
        signing_plist.write_bytes(plistlib.dumps(resolved))

    # Keep universal2 and single-arch dependencies in different environments.
    # This also prevents accidental reuse of a previous Homebrew ARM-only venv.
    env_tag = '-universal2' if requested_arch == 'universal2' else ''
    folder = ROOT / ('.venv-mac%s-%d.%d' % ((env_tag,) + sys.version_info[:2]))
    python = folder / 'bin/python'
    if not python.is_file():
        venv.EnvBuilder(with_pip=True).create(folder)
    marker = folder / 'runtime-ready'
    if action == 'build' or not marker.exists():
        requirement = ROOT / 'mac' / ('requirements-build.txt' if action == 'build' else 'requirements.txt')
        print('Installing macOS dependencies for Python %s (%s). This may take a few minutes.' %
              (platform.python_version(), requested_arch or 'native'), flush=True)
        subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(requirement)], check=True)
        marker.write_text(APP_VERSION + ' / Python ' + platform.python_version() + ' / ' + (requested_arch or 'native'))
    if action == 'launch':
        return subprocess.call([str(python), str(ROOT / 'app/desktop.py')], cwd=ROOT)

    subprocess.run([str(python), '-m', 'unittest', 'discover', '-v', '-s', 'tests', '-p', 'test_*.py'],
                   cwd=ROOT, check=True)
    subprocess.run([str(python), str(ROOT / 'tools/mac_notices.py'), str(ROOT / '.build/mac-notices')],
                   check=True)
    subprocess.run([str(python), '-m', 'PyInstaller', '--clean', '--noconfirm',
                    '--distpath', str(ROOT / 'release/mac'),
                    '--workpath', str(ROOT / '.build/mac'), str(ROOT / 'mac/freETargetMac.spec')],
                   cwd=ROOT, check=True)
    app = ROOT / 'release/mac' / APP_NAME
    executable = app / 'Contents/MacOS/freETargetMinimalist'
    if not executable.is_file():
        raise SystemExit('The expected .app was not produced.')

    if profile:
        shutil.copyfile(profile, app / 'Contents/embedded.provisionprofile')
        subprocess.run(['codesign', '--force', '--options', 'runtime', '--timestamp',
                        '--sign', identity, '--entitlements', str(signing_plist),
                        str(app)], check=True)
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)

    architecture = requested_arch or platform.machine()
    if architecture == 'universal2':
        checked = verify_universal_app(app)
        print('Verified both arm64 and x86_64 slices in %d Mach-O files.' % checked, flush=True)
    (app.parent / 'BUILD_INFO.json').write_text(json.dumps({
        'version': APP_VERSION,
        'architecture': architecture,
        'python': platform.python_version(),
        'universal2_verified': architecture == 'universal2',
    }, indent=2) + '\n')
    archive = app.parent / ('freETarget-Minimalist-' + APP_VERSION + '-' + architecture + '.zip')
    subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(app), str(archive)], check=True)
    print('Mac app:', app, '\nArchive:', archive,
          '\nSigning/notarization and testing on both Mac architectures are still required.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
