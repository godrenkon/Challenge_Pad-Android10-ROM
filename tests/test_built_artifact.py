"""Exercise real compressed artifacts, checksum binding and capacity failures."""
import contextlib
import hashlib
import importlib.util
import io
import json
import lzma
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('artifact', ROOT / 'scripts/verify-built-artifact.py')
ARTIFACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ARTIFACT)


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ctz-artifact-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.images = self.root / 'image-artifact'
        self.reports = self.root / 'build-report'
        self.destination = self.root / 'unpacked'
        self.images.mkdir()
        folder = self.reports / 'records/build-attempt-5'
        folder.mkdir(parents=True)
        self.receipt_path = folder / 'build-receipt.json'
        self.data = b'CTZ image fixture\x00' * 64
        self.receipt = {'status': 'systemimage-produced-unverified-on-device',
                        'image': {'fileBytes': len(self.data), 'SHA256': hashlib.sha256(self.data).hexdigest()}}
        self.write_receipt()
        self.write_compressed(lzma.compress(self.data, format=lzma.FORMAT_XZ))

    def write_receipt(self):
        self.receipt_path.write_text(json.dumps(self.receipt), encoding='utf-8')

    def write_compressed(self, data):
        (self.images / ARTIFACT.NAME).write_bytes(data)
        (self.images / 'SHA256SUMS').write_text(hashlib.sha256(data).hexdigest() + '  ' + ARTIFACT.NAME + '\n', encoding='ascii')

    def prepare(self):
        return ARTIFACT.prepare_image(self.images, self.reports, self.destination)

    def test_valid_compressed_artifact_matches_raw_receipt(self):
        image, receipt, compressed_hash = self.prepare()
        self.assertEqual(image.read_bytes(), self.data)
        self.assertEqual(receipt, self.receipt)
        self.assertEqual(len(compressed_hash), 64)
        self.assertFalse((self.destination / 'system.img.partial').exists())

    def test_corrupt_compressed_bytes_rejected_before_unpack(self):
        (self.images / ARTIFACT.NAME).write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'Compressed image checksum'):
            self.prepare()
        self.assertFalse(self.destination.exists())

    def test_truncated_xz_with_updated_checksum_is_not_complete(self):
        self.write_compressed(lzma.compress(self.data)[:-8])
        with self.assertRaises((ValueError, lzma.LZMAError)):
            self.prepare()
        self.assertFalse((self.destination / 'system.img').exists())

    def test_extra_xz_stream_is_rejected(self):
        self.write_compressed(lzma.compress(self.data) + lzma.compress(b'extra'))
        with self.assertRaisesRegex(ValueError, 'trailing data'):
            self.prepare()

    def test_expansion_cannot_exceed_receipt_size(self):
        self.receipt['image']['fileBytes'] = len(self.data) - 1
        self.write_receipt()
        with self.assertRaisesRegex(ValueError, 'exceeds its receipt'):
            self.prepare()
        self.assertFalse((self.destination / 'system.img').exists())

    def test_wrong_raw_image_hash_is_rejected(self):
        self.receipt['image']['SHA256'] = '0' * 64
        self.write_receipt()
        with self.assertRaisesRegex(ValueError, 'differs from its build receipt'):
            self.prepare()

    def test_checksum_filename_cannot_choose_another_file(self):
        (self.images / 'SHA256SUMS').write_text('0' * 64 + '  ../outside.img.xz\n')
        with self.assertRaisesRegex(ValueError, 'checksum record'):
            self.prepare()

    def test_duplicate_completed_receipts_are_ambiguous(self):
        other = self.reports / 'records/build-attempt-6/build-receipt.json'
        other.parent.mkdir()
        other.write_text(json.dumps(self.receipt), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            self.prepare()

    def test_existing_image_directory_is_preserved(self):
        self.destination.mkdir()
        keep = self.destination / 'keep.txt'
        keep.write_text('preserve me')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.prepare()
        self.assertEqual(keep.read_text(), 'preserve me')

    def run_main(self, content):
        output = self.root / 'inspection.json'
        args = ['--image-dir', str(self.images), '--build-report-dir', str(self.reports),
                '--work-dir', str(self.destination), '--output', str(output),
                '--partition-bytes', '4096', '--build-run-id', '123']
        with patch.object(ARTIFACT.CONTENT, 'verify_image', return_value=content), contextlib.redirect_stdout(io.StringIO()):
            code = ARTIFACT.main(args)
        return code, json.loads(output.read_text(encoding='utf-8'))

    def content(self, expanded):
        return {'imageSHA256': self.receipt['image']['SHA256'], 'geometry': {'expandedBytes': expanded},
                'systemAsRootLayout': True, 'bootTested': False, 'flashReady': False}

    def test_measured_capacity_uses_expanded_geometry(self):
        code, result = self.run_main(self.content(8192))
        self.assertEqual(code, 3)
        self.assertEqual(result['status'], 'content-checked-capacity-exceeded')
        self.assertFalse(result['fitsMeasuredPartition'])
        self.assertFalse(result['flashReady'])

    def test_exact_capacity_passes_without_claiming_boot(self):
        code, result = self.run_main(self.content(4096))
        self.assertEqual(code, 0)
        self.assertTrue(result['buildReceiptMatched'])
        self.assertTrue(result['fitsMeasuredPartition'])
        self.assertFalse(result['bootTested'])

    def test_wrong_system_layout_remains_unusable(self):
        content = self.content(4096)
        content['systemAsRootLayout'] = False
        code, result = self.run_main(content)
        self.assertEqual(code, 1)
        self.assertEqual(result['status'], 'inspection-failed')
        self.assertIn('system-as-root', result['error'])


if __name__ == '__main__':
    unittest.main()
