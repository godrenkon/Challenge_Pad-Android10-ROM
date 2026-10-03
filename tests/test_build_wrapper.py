"""Wrapper tests using a tiny fake build script, never compiling Android."""
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("ctz_build", ROOT / "scripts/build-ctz.py")
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class WrapperTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "fake source with spaces"
        (self.root / "build").mkdir(parents=True)
        self.records = Path(self.temp.name) / "records with spaces"
        self.lock = b"<manifest/><!-- offline wrapper fixture only -->\n"

    def tearDown(self):
        self.temp.cleanup()

    def script(self, body):
        # envsetup routinely reads unset variables; nounset is intentionally not enabled.
        prelude = ('echo "$CTZ_OPTIONAL_UNSET" >/dev/null\n'
                   'lunch() { test "$1" = suiram_ctz10-userdebug; }\n'
                   'm() { test "$1" = -j2 && test "$2" = systemimage || return 91;\n')
        (self.root / "build/envsetup.sh").write_text(prelude + body + '\n}\n')

    def receipt(self):
        return json.loads((self.records / "build-receipt.json").read_text())

    def test_fake_image_receipt_and_fresh_output(self):
        self.script("""python3 - <<'PY'
import os, pathlib, struct
p=pathlib.Path(os.environ['OUT_DIR'])/'target/product/phhgsi_arm64_ab/system.img'
p.parent.mkdir(parents=True)
data=bytearray(4096)
struct.pack_into('<I',data,1024+4,4)
struct.pack_into('<H',data,1024+56,0xEF53)
p.write_bytes(data)
PY""")
        with patch.dict(os.environ, {"OUT_DIR": "/should/not/be/used"}):
            receipt = BUILD.execute_build(self.root, self.records, 2, self.lock)
        self.assertEqual(receipt["status"], "systemimage-produced-unverified-on-device")
        self.assertFalse(receipt["flashReady"])
        self.assertFalse(receipt["bootTested"])
        self.assertEqual(receipt["image"]["expandedBytes"], 4096)
        self.assertEqual((self.records / "source-locked.xml").read_bytes(), self.lock)
        self.assertEqual(self.receipt(), receipt)
        with self.assertRaises(FileExistsError):
            BUILD.execute_build(self.root, self.records, 2, self.lock)

    def test_build_failure_records_failure(self):
        self.script("echo synthetic-failure; return 23")
        with self.assertRaises(ValueError):
            BUILD.execute_build(self.root, self.records, 2, self.lock)
        self.assertEqual(self.receipt()["exitCode"], 23)
        self.assertEqual(self.receipt()["status"], "failed-or-interrupted")
        self.assertNotIn("image", self.receipt())
        self.assertIn("synthetic-failure", (self.records / "build.log").read_text())

    def test_success_without_image_is_failure(self):
        self.script("return 0")
        with self.assertRaises(ValueError):
            BUILD.execute_build(self.root, self.records, 2, self.lock)
        self.assertEqual(self.receipt()["status"], "failed-or-interrupted")

    def test_unrecognized_image_is_failure(self):
        self.script('mkdir -p "$OUT_DIR/target/product/phhgsi_arm64_ab"; '
                    'printf "not-an-image" > "$OUT_DIR/target/product/phhgsi_arm64_ab/system.img"')
        with self.assertRaises(ValueError):
            BUILD.execute_build(self.root, self.records, 2, self.lock)
        self.assertEqual(self.receipt()["status"], "failed-or-interrupted")

    def test_symlinked_image_parent_is_failure(self):
        old = Path(self.temp.name) / "old-output"
        old.mkdir()
        (old / "system.img").write_bytes(b"old image must not be accepted")
        self.script("python3 - <<'PY'\n"
                    "import os,pathlib\n"
                    "p=pathlib.Path(os.environ['OUT_DIR'])/'target/product'\n"
                    "p.mkdir(parents=True)\n"
                    f"(p/'phhgsi_arm64_ab').symlink_to({str(old)!r},target_is_directory=True)\nPY")
        with self.assertRaisesRegex(ValueError, "symlink"):
            BUILD.execute_build(self.root, self.records, 2, self.lock)
        self.assertEqual(self.receipt()["status"], "failed-or-interrupted")

    def test_default_check_does_not_run_or_create_outputs(self):
        lock = Path(self.temp.name) / "locked.xml"
        lock.write_bytes(self.lock)
        with patch.object(BUILD, "host_report", return_value={"blockers": []}), \
                patch.object(BUILD, "validate_sources", return_value=self.root), \
                patch.object(BUILD, "execute_build") as execute, redirect_stdout(io.StringIO()):
            self.assertEqual(BUILD.main([str(self.root), "--locked-manifest", str(lock),
                                         "--record-dir", str(self.records)]), 0)
            execute.assert_not_called()
        self.assertFalse(self.records.exists())

    def test_host_blockers_prevent_build(self):
        with patch.object(BUILD, "host_report", return_value={"blockers": ["synthetic disk shortage"]}), \
                patch.object(BUILD, "validate_sources") as validate, patch.object(BUILD, "execute_build") as execute, \
                redirect_stdout(io.StringIO()):
            code = BUILD.main([str(self.root), "--locked-manifest", "not-present.xml",
                               "--record-dir", str(self.records), "--run"])
            self.assertEqual(code, 2)
            validate.assert_not_called()
            execute.assert_not_called()
        self.assertFalse(self.records.exists())

    def test_lock_mutation_during_validation_prevents_run(self):
        lock = Path(self.temp.name) / "locked.xml"
        lock.write_bytes(self.lock)
        def validate(*_):
            lock.write_bytes(b"changed during source validation\n")
            return self.root
        with patch.object(BUILD, "host_report", return_value={"blockers": []}), \
                patch.object(BUILD, "validate_sources", side_effect=validate), \
                patch.object(BUILD, "execute_build") as execute, \
                patch.object(sys, "stderr", io.StringIO()):
            self.assertEqual(BUILD.main([str(self.root), "--locked-manifest", str(lock),
                                         "--record-dir", str(self.records), "--run"]), 1)
            execute.assert_not_called()
        self.assertFalse(self.records.exists())

    def test_records_inside_sources_refused(self):
        with patch.object(BUILD, "host_report") as host, patch.object(sys, "stderr", io.StringIO()):
            self.assertEqual(BUILD.main([str(self.root), "--locked-manifest", "unused.xml",
                                         "--record-dir", str(self.root / "run"), "--run"]), 1)
            host.assert_not_called()
        self.assertFalse((self.root / "run").exists())


if __name__ == "__main__":
    unittest.main()
