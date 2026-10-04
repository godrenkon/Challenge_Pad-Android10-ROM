"""Exercise a real ext4 container with synthetic contents; never boot Android."""
import importlib.util
import json
import shutil
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('content', ROOT / 'scripts/verify-rom-content.py')
CONTENT = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CONTENT)

BUILD = b'''ro.build.version.release=10
ro.build.version.sdk=29
ro.build.type=userdebug
ro.product.cpu.abi=arm64-v8a
ro.product.system.name=suiram_ctz10
ro.product.system.model=TAB-A05-BA1
ro.product.locale=ja-JP
'''
DEFAULT = b'ro.adb.secure=1\npersist.sys.usb.config=mtp,adb\n'


class PropertyTests(unittest.TestCase):
    def test_android10_partition_properties_and_userdebug_usb(self):
        result = CONTENT.check_properties(CONTENT.properties(BUILD), CONTENT.properties(DEFAULT))
        self.assertEqual(result['persist.sys.usb.config'], 'mtp,adb')

    def test_wrong_os_product_and_insecure_adb_are_refused(self):
        for old, new in [(b'sdk=29', b'sdk=28'), (b'name=suiram_ctz10', b'name=aosp_arm64_ab'),
                         (b'abi=arm64-v8a', b'abi=armeabi-v7a')]:
            with self.subTest(new=new), self.assertRaises(ValueError):
                CONTENT.check_properties(CONTENT.properties(BUILD.replace(old, new)), CONTENT.properties(DEFAULT))
        with self.assertRaises(ValueError):
            CONTENT.check_properties(CONTENT.properties(BUILD), CONTENT.properties(DEFAULT.replace(b'secure=1', b'secure=0')))

    def test_duplicate_properties_refused(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            CONTENT.properties(b'ro.build.type=user\nro.build.type=userdebug\n')

    def test_build_prop_cannot_disable_default_adb_authentication(self):
        with self.assertRaisesRegex(ValueError, 'authenticated-ADB'):
            CONTENT.check_properties(CONTENT.properties(BUILD + b'ro.adb.secure=0\n'),
                                     CONTENT.properties(DEFAULT))
        result = CONTENT.check_properties(CONTENT.properties(BUILD + b'ro.adb.secure=1\n'),
                                          CONTENT.properties(DEFAULT))
        self.assertEqual(result['ro.adb.secure'], '1')


@unittest.skipUnless(all(shutil.which(x) for x in ['mkfs.ext4', 'debugfs', 'e2fsck']), 'e2fsprogs unavailable')
class FilesystemTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ctz-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tree = self.root / 'tree'
        system = self.tree / 'system'
        (system / 'etc').mkdir(parents=True)
        (system / 'build.prop').write_bytes(BUILD)
        (system / 'etc/prop.default').write_bytes(DEFAULT)
        for name in ['Settings', 'DocumentsUI', 'Launcher3QuickStep']:
            folder = system / 'priv-app' / name
            folder.mkdir(parents=True)
            (folder / (name + '.apk')).write_bytes(b'SYNTHETIC PLACEHOLDER, NOT AN APK')
        native = bytearray(20)
        native[:6] = b'\x7fELF\x02\x01'
        struct.pack_into('<H', native, 18, 183)
        (system / 'lib64').mkdir()
        (system / 'lib64/libandroid_runtime.so').write_bytes(native)
        for folder, bits, machine in [('lib', 32, 40), ('lib64', 64, 183)]:
            vndk = system / folder / 'vndk-28'
            vndk.mkdir(parents=True)
            elf = bytearray(20)
            elf[:6] = b'\x7fELF' + bytes([2 if bits == 64 else 1, 1])
            struct.pack_into('<H', elf, 18, machine)
            (vndk / 'libstdc++.so').write_bytes(elf)
        (system / 'etc/ld.config.28.txt').write_text('# SYNTHETIC PLACEHOLDER, NOT A LINKER CONFIG\n')
        self.image = self.root / 'fixture.img'

    def make_image(self):
        with self.image.open('wb') as stream:
            stream.truncate(16 * 1024 ** 2)
        subprocess.run(['mkfs.ext4', '-q', '-F', '-d', str(self.tree), str(self.image)],
                       check=True, capture_output=True)

    def test_read_only_filesystem_verification_and_accurate_limits(self):
        self.make_image()
        before = CONTENT.file_sha256(self.image)
        result = CONTENT.verify_image(self.image)
        self.assertEqual(before, CONTENT.file_sha256(self.image))
        self.assertEqual(result['status'], 'filesystem-and-content-checked')
        self.assertTrue(result['systemAsRootLayout'])
        self.assertFalse(result['bootTested'])
        self.assertFalse(result['hardwareTested'])
        self.assertFalse(result['flashReady'])
        self.assertIn('File presence', result['limits'])
        self.assertIn('/system/bin/dbclient', result['omittedRemoteDebugPaths'])
        self.assertEqual(set(result['vndk28CompatibilityFiles']), {'32', '64'})

    def test_android10_embedded_product_apps_in_sar_and_flat_image(self):
        system = self.tree / 'system'
        (system / 'product').mkdir()
        shutil.move(str(system / 'priv-app'), str(system / 'product/priv-app'))
        for sar in [True, False]:
            with self.subTest(sar=sar):
                if not sar:
                    for path in list(system.iterdir()):
                        shutil.move(str(path), str(self.tree / path.name))
                    system.rmdir()
                self.make_image()
                result = CONTENT.verify_image(self.image)
                prefix = '/system' if sar else ''
                self.assertEqual(result['applications']['settings'],
                                 prefix + '/product/priv-app/Settings/Settings.apk')
                self.assertEqual(result['systemAsRootLayout'], sar)

    def test_missing_or_wrong_architecture_vendor_compatibility_library_refused(self):
        for folder in ['lib', 'lib64']:
            path = self.tree / 'system' / folder / 'vndk-28/libstdc++.so'
            original = path.read_bytes()
            for wrong_arch in [False, True]:
                with self.subTest(folder=folder, wrong_arch=wrong_arch):
                    if wrong_arch:
                        bad = bytearray(original)
                        struct.pack_into('<H', bad, 18, 62)
                        path.write_bytes(bad)
                    else:
                        path.unlink()
                    self.make_image()
                    with self.assertRaises(ValueError):
                        CONTENT.verify_image(self.image)
                    path.write_bytes(original)

    def test_missing_vndk28_linker_configuration_refused(self):
        (self.tree / 'system/etc/ld.config.28.txt').unlink()
        self.make_image()
        with self.assertRaisesRegex(ValueError, 'linker configuration'):
            CONTENT.verify_image(self.image)

    def test_reverse_debug_helper_and_symlink_are_refused(self):
        helper = self.tree / 'system/bin/dbclient'
        helper.parent.mkdir()
        for symlink in [False, True]:
            with self.subTest(symlink=symlink):
                if symlink:
                    helper.symlink_to('/missing/helper')
                else:
                    helper.write_bytes(b'SYNTHETIC DISALLOWED HELPER')
                self.make_image()
                with self.assertRaisesRegex(ValueError, 'reverse-debugging helper'):
                    CONTENT.verify_image(self.image)
                helper.unlink()

    def test_missing_launcher_and_wrong_native_architecture_refused(self):
        launcher = self.tree / 'system/priv-app/Launcher3QuickStep/Launcher3QuickStep.apk'
        launcher.unlink()
        self.make_image()
        with self.assertRaisesRegex(ValueError, 'launcher'):
            CONTENT.verify_image(self.image)
        launcher.write_bytes(b'SYNTHETIC PLACEHOLDER')
        native = self.tree / 'system/lib64/libandroid_runtime.so'
        data = bytearray(native.read_bytes())
        struct.pack_into('<H', data, 18, 62)
        native.write_bytes(data)
        self.make_image()
        with self.assertRaisesRegex(ValueError, 'AArch64'):
            CONTENT.verify_image(self.image)

    def test_corrupt_ext4_is_refused(self):
        self.make_image()
        with self.image.open('r+b') as stream:
            stream.seek(1080)
            stream.write(b'\x00\x00')
        with self.assertRaises(ValueError):
            CONTENT.verify_image(self.image)

    def test_existing_verification_report_is_preserved(self):
        self.make_image()
        output = self.root / 'report.json'
        output.write_text('preserve this report')
        self.assertEqual(CONTENT.main([str(self.image), '--output', str(output)]), 1)
        self.assertEqual(output.read_text(), 'preserve this report')


if __name__ == '__main__':
    unittest.main()
