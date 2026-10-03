#!/usr/bin/env python3
"""Build an unsigned Japanese IME candidate; never install or modify Android sources."""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from source_manifest import ROOT, assert_clear_index, blob_sha, git

PROFILE = ROOT / 'config/japanese-ime.json'
NOTICE = '''Japanese IME candidate for the CTZ Android 10 engineering project.
Upstream: https://github.com/gorry/nicoWnnG
Copyright: OMRON SOFTWARE Co., Ltd.; hiroshica; Hiroaki Goto (GORRY).
License: Apache-2.0. Preserve LICENSE and both upstream README files.
Our build changes SDK/ABI/NDK settings, omits private signing configuration,
removes jcenter and obsolete native flags, and explicitly links libdl.
The APK is unsigned, not an installable application or a finished ROM.
Runtime, Japanese conversion and CTZ hardware operation are untested.
AndroidX dependency licenses are also retained inside the APK where supplied.
'''


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('Reviewed build setting is missing or duplicated: ' + before)
    return text.replace(before, after, 1)


def source_plan(source, profile):
    source = Path(source).resolve(strict=True)
    if not source.is_dir() or source == ROOT or ROOT.is_relative_to(source):
        raise ValueError('Use a separate upstream source checkout')
    if Path(git(source, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != source:
        raise ValueError('Source must be its own Git checkout')
    if git(source, 'rev-parse', 'HEAD').decode().strip() != profile['commit']:
        raise ValueError('Upstream source commit differs from pinned candidate')
    assert_clear_index(source)
    if git(source, 'status', '--porcelain=v1', '--untracked-files=all', '--ignored'):
        raise ValueError('Use a clean checkout, including untracked and ignored files')
    files = {}
    for name, expected in profile['requiredFiles'].items():
        path = source
        for part in name.split('/'):
            path /= part
            if path.is_symlink():
                raise ValueError('Refusing source symlink: ' + name)
        data = path.read_bytes()
        if blob_sha(data) != expected:
            raise ValueError('Unreviewed source input: ' + name)
        files[name] = data
    app = files['app/build.gradle'].decode('utf-8')
    app = replace_once(app, 'targetSdk 36', 'targetSdk 29')
    app = replace_once(app, '// ndkVersion "26.3.11579264"',
                       'ndkVersion "' + profile['ndkVersion'] + '"')
    app = replace_once(app, 'abiFilters "armeabi-v7a", "x86", "arm64-v8a", "x86_64"',
                       'abiFilters "armeabi-v7a", "arm64-v8a"')
    # Empty configs let release packaging run without upstream private keystores.
    signing = 'android { signingConfigs { master {} develop {} } }\n'
    application = ('APP_ABI := armeabi-v7a arm64-v8a\n'
                   'APP_PLATFORM := android-24\n')
    native = files['app/src/main/jni/libwnnDictionary/Android.mk'].decode('utf-8')
    native = replace_once(native, '-fno-inline-small-functions', '')
    native = replace_once(native, 'LOCAL_STATIC_LIBRARIES :=',
                          'LOCAL_LDLIBS += -ldl\nLOCAL_STATIC_LIBRARIES :=')
    top = files['build.gradle'].decode('utf-8')
    if top.count('jcenter()') != 2:
        raise ValueError('Unexpected repository settings')
    top = top.replace('jcenter()', '// jcenter omitted by CTZ build')
    changes = {'app/build.gradle': app.encode('utf-8'),
               'app/signingConfigs.gradle': signing.encode('utf-8'),
               'app/src/main/jni/Application.mk': application.encode('utf-8'),
               'app/src/main/jni/libwnnDictionary/Android.mk': native.encode('utf-8'),
               'build.gradle': top.encode('utf-8')}
    return source, files, changes


def inspect_apk(path, badging, profile):
    if "package: name='" + profile['applicationId'] + "'" not in badging:
        raise ValueError('Unexpected APK application ID')
    for field, value in [('sdkVersion', profile['minSdk']), ('targetSdkVersion', profile['targetSdk'])]:
        if re.search(r"^" + field + r":'([0-9]+)'$", badging, re.M) is None or \
                re.search(r"^" + field + r":'([0-9]+)'$", badging, re.M).group(1) != str(value):
            raise ValueError('Unexpected APK SDK setting: ' + field)
    if 'application-debuggable' in badging:
        raise ValueError('Refusing a debuggable APK')
    libraries = ['libnicownngdict.so', 'libnicoWnnGJpnDic.so', 'libnicoWnnGEngDic.so']
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate APK ZIP members')
        if 'AndroidManifest.xml' not in names or 'classes.dex' not in names:
            raise ValueError('APK manifest/classes are missing')
        if any(re.match(r'META-INF/.*\.(RSA|DSA|EC|SF)$', name, re.I) for name in names):
            raise ValueError('Expected unsigned APK, found JAR signature')
        actual = {name.split('/')[1] for name in names if name.startswith('lib/') and name.endswith('.so')}
        if actual != set(profile['abis']):
            raise ValueError('APK native ABI set differs from the CTZ candidate')
        for abi in profile['abis']:
            for library in libraries:
                header = archive.read('lib/' + abi + '/' + library)[:20]
                machine = 183 if abi == 'arm64-v8a' else 40
                bits = 2 if abi == 'arm64-v8a' else 1
                if len(header) < 20 or header[:4] != b'\x7fELF' or header[4:6] != bytes([bits, 1]) or \
                        int.from_bytes(header[18:20], 'little') != machine:
                    raise ValueError('Invalid native library architecture: ' + abi + '/' + library)


def run_build(source, output, profile, files, changes, gradle):
    if output.is_symlink() or output.exists():
        raise ValueError('Output already exists; retain it and choose a new directory')
    if output.is_relative_to(source) or source.is_relative_to(output) or output.is_relative_to(ROOT):
        raise ValueError('Keep build output outside both checkouts')
    sdk_value = os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT')
    if not sdk_value:
        raise ValueError('ANDROID_HOME is required')
    sdk = Path(sdk_value)
    aapt = sdk / 'build-tools/36.0.0/aapt'
    signer = sdk / 'build-tools/36.0.0/apksigner'
    if not all(p.is_file() for p in [aapt, signer, sdk / 'platforms/android-36/android.jar',
                                   sdk / ('ndk/' + profile['ndkVersion'] + '/source.properties')]):
        raise ValueError('Pinned SDK/build-tools/NDK are not installed')
    if shutil.which(gradle) is None:
        raise ValueError('Gradle executable is missing')
    output.mkdir(parents=True)
    receipt = {'status': 'building', 'upstreamRepository': profile['repository'],
               'upstreamCommit': profile['commit'], 'profileSHA256': sha256(PROFILE),
               'toolSHA256': sha256(Path(__file__)), 'runtimeTested': False,
               'romIntegrated': False, 'flashReady': False,
               'patches': {name: {'beforeBlob': blob_sha(files[name]) if name in files else None,
                                  'afterBlob': blob_sha(data)} for name, data in changes.items()}}
    receipt_path = output / 'build-receipt.json'
    def save():
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    save()
    try:
        # Recheck the complete checkout immediately before writing.
        _, current, current_changes = source_plan(source, profile)
        if current != files or current_changes != changes:
            raise ValueError('Source changed after inspection')
        for name, data in changes.items():
            (source / name).write_bytes(data)
        with (output / 'build.log').open('xb') as log:
            version = subprocess.run([gradle, '--version'], cwd=source, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, check=True, timeout=120)
            log.write(version.stdout)
            if ('Gradle ' + profile['gradleVersion'] + '\n').encode() not in version.stdout:
                raise ValueError('Gradle version differs from pinned build tool')
            result = subprocess.run([gradle, '--no-daemon', '--console=plain', '--stacktrace',
                                     ':app:assembleDevelopRelease'], cwd=source, stdout=log,
                                    stderr=subprocess.STDOUT, check=False, timeout=1500)
            receipt['exitCode'] = result.returncode
            if result.returncode:
                raise ValueError('Japanese IME build failed; see build.log')
        candidates = list((source / 'app/build/outputs/apk/develop/release').glob('*.apk'))
        if len(candidates) != 1:
            raise ValueError('Expected exactly one new release APK')
        apk = candidates[0]
        badging = subprocess.run([str(aapt), 'dump', 'badging', str(apk)], capture_output=True,
                                 text=True, check=True, timeout=120).stdout
        inspect_apk(apk, badging, profile)
        signed = subprocess.run([str(signer), 'verify', str(apk)], capture_output=True,
                                text=True, check=False, timeout=120)
        # A failed verification alone does not establish absence of signing blocks.
        # AGP output name and the ZIP signature checks are checked too.
        if signed.returncode == 0 or not apk.name.endswith('-unsigned.apk'):
            raise ValueError('Expected unsigned Gradle release output')
        target = output / 'ctz-japanese-ime-unsigned.apk'
        shutil.copyfile(apk, target)
        (output / 'apk-badging.txt').write_text(badging, encoding='utf-8')
        for name in ['LICENSE', 'README.txt', 'README.orig.txt']:
            (output / ('upstream-' + name)).write_bytes(files[name])
        (output / 'NOTICE.txt').write_text(NOTICE, encoding='utf-8')
        receipt.update(status='compiled-unsigned', apkSHA256=sha256(target), apkBytes=target.stat().st_size,
                       applicationId=profile['applicationId'], minSdk=profile['minSdk'],
                       targetSdk=profile['targetSdk'], abis=profile['abis'])
        save()
    except Exception as error:
        receipt.update(status='failed', error=str(error))
        save()
        raise
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--gradle', default='gradle')
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args(argv)
    try:
        profile = json.loads(PROFILE.read_text(encoding='utf-8'))
        source, files, changes = source_plan(args.source, profile)
        if not args.run:
            print('検査完了。ソース変更・ダウンロード・ビルドは実行していません。')
            print(json.dumps({'upstreamCommit': profile['commit'], 'plannedChanges': list(changes),
                              'runtimeTested': False, 'romIntegrated': False}, indent=2))
            return 0
        if args.output is None:
            raise ValueError('--output is required with --run')
        print(json.dumps(run_build(source, args.output.resolve(), profile, files, changes, args.gradle), indent=2))
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError, zipfile.BadZipFile) as error:
        print('エラー: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
