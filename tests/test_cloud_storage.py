"""Storage provisioning guards; the workflow separately tests actual mounting."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ctz_cloud_storage', ROOT / 'scripts/prepare-cloud-storage.py')
STORAGE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(STORAGE)


class StorageGuards(unittest.TestCase):
    def test_local_machine_is_never_formatted(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {'GITHUB_ACTIONS': 'false'}), \
                patch.object(STORAGE, 'command') as command:
            with self.assertRaisesRegex(ValueError, 'ephemeral'):
                STORAGE.prepare(td)
            command.assert_not_called()
            self.assertEqual(list(Path(td).iterdir()), [])

    def test_existing_image_and_symlink_are_never_formatted(self):
        for symlink in (False, True):
            with self.subTest(symlink=symlink), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                image = root / 'ctz-build-storage.btrfs'
                if symlink:
                    image.symlink_to(root / 'missing-target')
                else:
                    image.write_bytes(b'keep existing data')
                free = type('Disk', (), {'free': STORAGE.MIN_BACKING_FREE})()
                with patch.dict(os.environ, {'GITHUB_ACTIONS': 'true', 'RUNNER_ENVIRONMENT': 'github-hosted',
                                             'RUNNER_TEMP': td}), \
                        patch.object(STORAGE.shutil, 'disk_usage', return_value=free), \
                        patch.object(STORAGE, 'command') as command:
                    with self.assertRaisesRegex(ValueError, 'new paths'):
                        STORAGE.prepare(td)
                    command.assert_not_called()
                    if not symlink:
                        self.assertEqual(image.read_bytes(), b'keep existing data')

    def test_insufficient_real_capacity_does_not_create_virtual_disk(self):
        with tempfile.TemporaryDirectory() as td, \
                patch.dict(os.environ, {'GITHUB_ACTIONS': 'true', 'RUNNER_ENVIRONMENT': 'github-hosted',
                                       'RUNNER_TEMP': td}), \
                patch.object(STORAGE.shutil, 'disk_usage', return_value=type('Disk', (), {'free': 0})()), \
                patch.object(STORAGE, 'command') as command:
            with self.assertRaisesRegex(ValueError, 'real backing'):
                STORAGE.prepare(td)
            command.assert_not_called()
            self.assertEqual(list(Path(td).iterdir()), [])
