"""Offline guards only; the separate Actions job performs the actual APK build."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('ime', ROOT / 'scripts/build-japanese-ime.py')
IME = importlib.util.module_from_spec(spec)
spec.loader.exec_module(IME)


class JapaneseImeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.profile = json.loads(IME.PROFILE.read_text())
        fixture = {
            'app/build.gradle': 'targetSdk 36\n// ndkVersion "26.3.11579264"\nabiFilters "armeabi-v7a", "x86", "arm64-v8a", "x86_64"\n',
            'build.gradle': 'jcenter()\njcenter()\n',
            'app/src/main/jni/libwnnDictionary/Android.mk': '-fno-inline-small-functions\nLOCAL_STATIC_LIBRARIES :=\n',
            'app/src/main/jni/Application.mk': 'APP_PLATFORM := android-3\n',
            'app/src/main/AndroidManifest.xml': '<manifest/>',
            'LICENSE': 'synthetic fixture license',
            'README.txt': 'synthetic fixture', 'README.orig.txt': 'synthetic fixture'}
        for name, content in fixture.items():
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        self.profile['requiredFiles'] = {name: IME.blob_sha((self.source / name).read_bytes()) for name in fixture}
        self.git('init', '-q')
        self.git('add', '.')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture')
        self.profile['commit'] = self.git('rev-parse', 'HEAD').strip()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.source), *args], text=True)

    def test_preview_is_read_only(self):
        before = {p: p.read_bytes() for p in self.source.rglob('*') if p.is_file()}
        _, _, changes = IME.source_plan(self.source, self.profile)
        self.assertIn('targetSdk 29', changes['app/build.gradle'].decode())
        self.assertNotIn('x86', changes['app/build.gradle'].decode())
        self.assertIn('APP_PLATFORM := android-24', changes['app/src/main/jni/Application.mk'].decode())
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_other_commit_refused(self):
        self.profile['commit'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'commit differs'):
            IME.source_plan(self.source, self.profile)

    def test_dirty_source_refused(self):
        (self.source / 'LICENSE').write_text('modified')
        with self.assertRaisesRegex(ValueError, 'clean checkout'):
            IME.source_plan(self.source, self.profile)

    def test_hidden_change_refused(self):
        self.git('update-index', '--assume-unchanged', 'LICENSE')
        (self.source / 'LICENSE').write_text('modified')
        with self.assertRaises(ValueError):
            IME.source_plan(self.source, self.profile)

    def test_untracked_source_refused(self):
        (self.source / 'private.key').write_text('fixture')
        with self.assertRaisesRegex(ValueError, 'clean checkout'):
            IME.source_plan(self.source, self.profile)

    def test_wrong_reviewed_blob_refused(self):
        self.profile['requiredFiles']['LICENSE'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'Unreviewed'):
            IME.source_plan(self.source, self.profile)

    def test_existing_output_preserved(self):
        output = self.root / 'output'
        output.mkdir()
        marker = output / 'old.log'
        marker.write_text('keep')
        _, files, changes = IME.source_plan(self.source, self.profile)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            IME.run_build(self.source, output, self.profile, files, changes, 'gradle')
        self.assertEqual(marker.read_text(), 'keep')
        self.assertEqual(self.git('status', '--porcelain'), '')

    def apk(self, omit=None, wrong_elf=False, signature=False):
        path = self.root / 'synthetic.apk'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('AndroidManifest.xml', 'synthetic fixture')
            archive.writestr('classes.dex', 'synthetic fixture')
            for abi in self.profile['abis']:
                for name in ['libnicownngdict.so', 'libnicoWnnGJpnDic.so', 'libnicoWnnGEngDic.so']:
                    if name == omit:
                        continue
                    header = bytearray(20)
                    header[:6] = b'\x7fELF' + bytes([2 if abi == 'arm64-v8a' else 1, 1])
                    header[18:20] = (62 if wrong_elf else 183 if abi == 'arm64-v8a' else 40).to_bytes(2, 'little')
                    archive.writestr('lib/' + abi + '/' + name, header)
            if signature:
                archive.writestr('META-INF/TEST.RSA', 'synthetic signature')
        return path

    def badging(self):
        return "package: name='net.gorry.android.input.nicownng'\nsdkVersion:'24'\ntargetSdkVersion:'29'\n"

    def test_archive_guard_accepts_expected_headers_only(self):
        IME.inspect_apk(self.apk(), self.badging(), self.profile)

    def test_missing_japanese_dictionary_refused(self):
        with self.assertRaises(KeyError):
            IME.inspect_apk(self.apk(omit='libnicoWnnGJpnDic.so'), self.badging(), self.profile)

    def test_x86_library_disguised_as_arm_refused(self):
        with self.assertRaisesRegex(ValueError, 'architecture'):
            IME.inspect_apk(self.apk(wrong_elf=True), self.badging(), self.profile)

    def test_wrong_sdk_refused(self):
        with self.assertRaisesRegex(ValueError, 'SDK'):
            IME.inspect_apk(self.apk(), self.badging().replace("'29'", "'36'"), self.profile)

    def test_debuggable_or_signed_apk_refused(self):
        with self.assertRaisesRegex(ValueError, 'debuggable'):
            IME.inspect_apk(self.apk(), self.badging() + 'application-debuggable\n', self.profile)
        with self.assertRaisesRegex(ValueError, 'signature'):
            IME.inspect_apk(self.apk(signature=True), self.badging(), self.profile)


if __name__ == '__main__':
    unittest.main()
