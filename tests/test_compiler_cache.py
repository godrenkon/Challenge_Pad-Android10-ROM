"""Cache activation guards and propagation into the build invocation."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('cache_build', ROOT / 'scripts/build-ctz.py')
BUILD = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BUILD)


class CompilerCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cache = self.root / 'ctz-compiler-cache'
        self.cache.mkdir()
        self.env = {'CTZ_COMPILER_CACHE': 'true', 'GITHUB_ACTIONS': 'true',
                    'RUNNER_ENVIRONMENT': 'github-hosted', 'RUNNER_TEMP': str(self.root)}

    def test_default_does_not_allow_caller_compiler_wrappers(self):
        with patch.dict(os.environ, {'CC_WRAPPER': '/untrusted/wrapper'}, clear=True):
            self.assertEqual(BUILD.compiler_cache_environment(), {})

    def test_cloud_opt_in_cannot_enable_cache_on_desktop(self):
        with patch.dict(os.environ, {'CTZ_COMPILER_CACHE': 'true'}, clear=True):
            with self.assertRaisesRegex(ValueError, 'GitHub-hosted'):
                BUILD.execute_build(self.root, self.root / 'records', 2, b'lock')
        self.assertFalse((self.root / 'records').exists())

    def test_missing_cache_directory_is_rejected(self):
        self.cache.rmdir()
        with patch.dict(os.environ, self.env, clear=True):
            with self.assertRaisesRegex(ValueError, 'directory'):
                BUILD.compiler_cache_environment()

    def test_missing_executable_is_rejected(self):
        with patch.dict(os.environ, self.env, clear=True), patch.object(BUILD.shutil, 'which', return_value=None):
            with self.assertRaisesRegex(ValueError, 'missing'):
                BUILD.compiler_cache_environment()

    def test_cache_reaches_compiler_and_failure_receipt_without_reusing_output(self):
        records = self.root / 'records'
        BUILD.platform.uname()  # Resolve Windows host details before mocking subprocess.run.
        with patch.dict(os.environ, self.env, clear=True), \
                patch.object(BUILD.shutil, 'which', return_value='/usr/bin/ccache'), \
                patch.object(BUILD.subprocess, 'run', return_value=SimpleNamespace(returncode=23)) as run:
            with self.assertRaisesRegex(ValueError, 'Android build failed'):
                BUILD.execute_build(self.root, records, 4, b'lock')
        env = run.call_args.kwargs['env']
        self.assertEqual(env['CC_WRAPPER'], '/usr/bin/ccache')
        self.assertEqual(env['CCACHE_DIR'], str(self.cache))
        self.assertEqual(env['CCACHE_COMPILERCHECK'], 'content')
        self.assertEqual(env['OUT_DIR'], str(records / 'out'))
        receipt = json.loads((records / 'build-receipt.json').read_text())
        self.assertTrue(receipt['compilerCache']['enabled'])
        self.assertFalse(receipt['flashReady'])
        self.assertNotIn('image', receipt)


if __name__ == '__main__':
    unittest.main()
