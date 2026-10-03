import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ctz_extract", ROOT / "scripts/extract-stock.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ExtractionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.source = self.base / "stock"
        (self.source / "system").mkdir(parents=True)
        self.profile = json.loads((ROOT / "config/ctz-stock.json").read_text())["required"]
        self.prop = self.source / "system/build.prop"
        self.prop.write_text("\n".join(f"{key}={value}" for key, value in self.profile.items()))
        self.blob = self.source / "vendor/lib/test.so"
        self.blob.parent.mkdir(parents=True)
        self.blob.write_bytes(b"synthetic fixture, not vendor firmware")
        self.manifest = self.base / "manifest.txt"
        self.manifest.write_text("vendor/lib/test.so:lib/test.so\n")
        self.output = self.base / "output"

    def tearDown(self):
        self.temp.cleanup()

    def extract(self):
        return MODULE.extract(self.source, self.manifest, self.output)

    def test_correct_stock_and_explicit_destination(self):
        self.assertEqual(self.extract(), 1)
        self.assertEqual((self.output / "lib/test.so").read_bytes(), self.blob.read_bytes())

    def test_wrong_model_or_build_or_fingerprint(self):
        original = self.prop.read_text()
        for key in ("ro.product.model", "ro.build.id", "ro.build.version.release", "ro.build.fingerprint"):
            self.prop.write_text(original.replace(f"{key}={self.profile[key]}", f"{key}=wrong"))
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.extract()
            self.assertFalse(self.output.exists())

    def test_empty_manifest_creates_nothing(self):
        self.manifest.write_text("# comments only\n")
        self.assertEqual(self.extract(), 0)
        self.assertFalse(self.output.exists())

    def test_no_colon_uses_same_relative_path(self):
        self.manifest.write_text("vendor/lib/test.so\n")
        self.assertEqual(self.extract(), 1)
        self.assertTrue((self.output / "vendor/lib/test.so").is_file())

    def test_reject_overwrite(self):
        self.extract()
        existing = (self.output / "lib/test.so").read_bytes()
        with self.assertRaises(ValueError):
            self.extract()
        self.assertEqual(existing, (self.output / "lib/test.so").read_bytes())

    def test_reject_unsafe_paths_before_writing(self):
        for entry in ("../outside", "/absolute", "vendor/lib/test.so:../../outside",
                      "vendor/lib/test.so:/absolute", "vendor\\lib\\test.so",
                      "vendor/lib/test.so:a:b", "vendor/lib/test.so:./relative"):
            self.manifest.write_text(entry)
            with self.subTest(entry=entry), self.assertRaises((ValueError, OSError)):
                self.extract()
            self.assertFalse(self.output.exists())

    def test_reject_duplicate(self):
        self.manifest.write_text("vendor/lib/test.so:a\nvendor/lib/test.so:a\n")
        with self.assertRaises(ValueError):
            self.extract()
        self.assertFalse(self.output.exists())

    def test_preflight_missing_file(self):
        self.manifest.write_text("vendor/lib/test.so:a\nvendor/lib/missing.so:b\n")
        with self.assertRaises(OSError):
            self.extract()
        self.assertFalse(self.output.exists())

    def test_sar_layout(self):
        content = self.prop.read_bytes()
        self.prop.unlink()
        (self.source / "system/system").mkdir()
        (self.source / "system/system/build.prop").write_bytes(content)
        self.assertEqual(self.extract(), 1)

    def test_source_overlap(self):
        with self.assertRaises(ValueError):
            MODULE.extract(self.source, self.manifest, self.source / "output")

    def test_reject_dangling_destination_symlink(self):
        (self.output / "lib").mkdir(parents=True)
        (self.output / "lib/test.so").symlink_to(self.output / "missing-target.so")
        with self.assertRaises(ValueError):
            self.extract()
        self.assertFalse((self.output / "missing-target.so").exists())

    def test_symlink_escape(self):
        outside = self.base / "outside.so"
        outside.write_bytes(b"outside")
        link = self.source / "vendor/lib/link.so"
        link.symlink_to(outside)
        self.manifest.write_text("vendor/lib/link.so")
        with self.assertRaises(ValueError):
            self.extract()
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
