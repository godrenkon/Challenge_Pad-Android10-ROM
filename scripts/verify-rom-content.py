#!/usr/bin/env python3
"""Read-only ext4 inspection of the built Android system image, never device testing."""
import argparse
import hashlib
import importlib.util
import json
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('rom_geometry', ROOT / 'scripts/inspect-system-image.py')
GEOMETRY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GEOMETRY)


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def properties(data):
    result = {}
    for raw in data.decode('utf-8', errors='strict').splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            raise ValueError('Malformed Android property line')
        key, value = line.split('=', 1)
        if not key or key != key.strip() or key in result:
            raise ValueError('Missing or duplicate Android property key: ' + key)
        result[key] = value
    return result


def check_properties(build, defaults):
    required = {'ro.build.version.release': '10', 'ro.build.version.sdk': '29',
                'ro.build.type': 'userdebug', 'ro.product.cpu.abi': 'arm64-v8a',
                'ro.product.system.name': 'suiram_ctz10', 'ro.product.system.model': 'TAB-A05-BA1',
                'ro.product.locale': 'ja-JP'}
    combined = dict(defaults)
    combined.update(build)
    for key, expected in required.items():
        if combined.get(key) != expected:
            raise ValueError('Unexpected system property: ' + key + '=' + str(combined.get(key)))
    # Android 10 post_process_props.py adds adb to userdebug USB defaults.
    if combined.get('ro.adb.secure') != '1' or combined.get('persist.sys.usb.config') not in {'mtp', 'mtp,adb'}:
        raise ValueError('Built image did not retain the reviewed authenticated-ADB/MTP settings')
    return {key: combined[key] for key in list(required) + ['ro.adb.secure', 'persist.sys.usb.config']}


def debugfs(image, command, *, allow_missing=False):
    # No -w and no mount: debugfs accesses the image in read-only mode.
    result = subprocess.run(['debugfs', '-R', command, str(image)], capture_output=True,
                            check=False, timeout=120)
    errors = result.stderr.decode('utf-8', 'replace')
    if allow_missing and result.returncode == 0 and any(marker in errors for marker in
                                                        ['File not found', 'not found by ext2_lookup']):
        return None
    if result.returncode or any(marker in errors for marker in
                                ['File not found', 'not found by ext2_lookup', 'Filesystem not open',
                                 'Bad magic number', 'short read', 'Command not found']):
        raise ValueError('Cannot inspect image entry: ' + command + ': ' + errors.strip())
    return result.stdout


def entry_exists(image, path):
    data = debugfs(image, 'stat ' + path, allow_missing=True)
    if data is None:
        return False
    if b'Inode:' not in data:
        raise ValueError('Cannot establish whether image entry exists: ' + path)
    return True


def exists(image, path):
    try:
        data = debugfs(image, 'stat ' + path)
        return b'Inode:' in data and b'Type: regular' in data
    except ValueError:
        return False


def check_elf(data, *, bits, machine, path):
    elf_class = 2 if bits == 64 else 1
    if (len(data) < 20 or data[:4] != b'\x7fELF' or data[4:6] != bytes([elf_class, 1])
            or struct.unpack_from('<H', data, 18)[0] != machine):
        raise ValueError('Unexpected ELF architecture in ' + path + ': expected ' +
                         ('AArch64' if machine == 183 else 'ARM') + '/' + str(bits))


def inspect_ext4(image):
    prefix = '/system' if exists(image, '/system/build.prop') else ''
    build_path = prefix + '/build.prop'
    build = properties(debugfs(image, 'cat ' + build_path))
    defaults = {}
    for path in [prefix + '/etc/prop.default', '/default.prop']:
        if exists(image, path):
            for key, value in properties(debugfs(image, 'cat ' + path)).items():
                if key in defaults and defaults[key] != value:
                    raise ValueError('Conflicting default properties: ' + key)
                defaults[key] = value
    selected = check_properties(build, defaults)
    omitted_remote = [prefix + path for path in
                      ['/bin/dbclient', '/bin/phh-remotectl.sh', '/etc/init/phh-remotectl.rc']]
    for path in omitted_remote:
        if entry_exists(image, path):
            raise ValueError('Unexpected PHH reverse-debugging helper in image: ' + path)
    # Android 10 GSI embeds product and product_services under system. Settings
    # and QuickStep are product modules in the actual pinned build, not system
    # modules. Search embedded paths only; an external partition is not this image.
    app_roots = [prefix + suffix for suffix in ['', '/product', '/product_services']]
    paths = {feature: [root + '/' + location + '/' + name + '/' + name + '.apk'
                       for root in app_roots for location in ['priv-app', 'app'] for name in names]
             for feature, names in {'settings': ['Settings'], 'files': ['DocumentsUI'],
                                    'launcher': ['Launcher3QuickStep', 'Launcher3', 'Launcher3Go']}.items()}
    verified = {}
    for feature, candidates in paths.items():
        match = next((path for path in candidates if exists(image, path)), None)
        if match is None:
            raise ValueError('Required system application is missing: ' + feature)
        verified[feature] = match
    native = debugfs(image, 'cat ' + prefix + '/lib64/libandroid_runtime.so')
    check_elf(native, bits=64, machine=183, path=prefix + '/lib64/libandroid_runtime.so')
    # CTZ's published stock declares VNDK 28 and both ARM userspaces. These
    # PHH compatibility files are copied by the pinned vndk32.mk/vndk64.mk.
    # Checking them does not establish full vendor/HAL compatibility.
    compatibility = {}
    for folder, bits, machine in [('lib', 32, 40), ('lib64', 64, 183)]:
        path = prefix + '/' + folder + '/vndk-28/libstdc++.so'
        if not exists(image, path):
            raise ValueError('Missing Android 9 vendor compatibility library: ' + path)
        check_elf(debugfs(image, 'cat ' + path), bits=bits, machine=machine, path=path)
        compatibility[str(bits)] = path
    linker = prefix + '/etc/ld.config.28.txt'
    if not exists(image, linker):
        raise ValueError('Missing VNDK 28 linker configuration: ' + linker)
    return {'properties': selected, 'applications': verified, 'runtimeELF': 'AArch64-64bit-little-endian',
            'systemAsRootLayout': prefix == '/system', 'omittedRemoteDebugPaths': omitted_remote,
            'vndk28CompatibilityFiles': compatibility, 'vndk28LinkerConfig': linker}


def verify_image(image):
    if shutil.which('debugfs') is None or shutil.which('e2fsck') is None:
        raise ValueError('debugfs and e2fsck are required')
    geometry = GEOMETRY.inspect_image(image)
    with tempfile.TemporaryDirectory(prefix='ctz-rom-verify-') as temporary:
        raw = image
        if geometry['format'] == 'android-sparse':
            if shutil.which('simg2img') is None:
                raise ValueError('simg2img is required for Android sparse input')
            if shutil.disk_usage(temporary).free < geometry['expandedBytes'] + 1024 ** 3:
                raise ValueError('Not enough temporary space to inspect sparse image')
            raw = Path(temporary) / 'expanded.img'
            subprocess.run(['simg2img', str(image), str(raw)], check=True, timeout=300)
            raw_geometry = GEOMETRY.inspect_image(raw)
            if raw_geometry['format'] != 'raw-ext4' or raw.stat().st_size != geometry['expandedBytes']:
                raise ValueError('Expanded image geometry differs from sparse header')
        fsck = subprocess.run(['e2fsck', '-f', '-n', str(raw)], capture_output=True,
                              check=False, timeout=300)
        if fsck.returncode != 0:
            raise ValueError('Read-only filesystem check failed: ' + fsck.stdout.decode('utf-8', 'replace') +
                             fsck.stderr.decode('utf-8', 'replace'))
        result = inspect_ext4(raw)
    return {'status': 'filesystem-and-content-checked', 'imageSHA256': file_sha256(image),
            'geometry': geometry, **result, 'filesystemCheck': 'e2fsck -f -n exit 0',
            'bootTested': False, 'hardwareTested': False, 'gmsTested': False, 'flashReady': False,
            'limits': 'File presence and ELF/property checks do not establish app behavior, AVB or device boot.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.output and (args.output.exists() or args.output.is_symlink()):
            raise ValueError('Verification output already exists; refusing overwrite')
        result = verify_image(args.image.resolve(strict=True))
        data = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if args.output:
            with args.output.open('x', encoding='utf-8') as stream:
                stream.write(data)
        print(data, end='')
        return 0
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError, struct.error) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
