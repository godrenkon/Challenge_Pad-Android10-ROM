import importlib.util
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/inspect-system-image.py"
SPEC = importlib.util.spec_from_file_location("ctz_image", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def sparse(chunk_type=0xCAC3, blocks=2, payload=b"", declared_blocks=None):
    header = struct.pack("<I4H4I", MODULE.SPARSE_MAGIC, 1, 0, 28, 12, 4096,
                         blocks if declared_blocks is None else declared_blocks, 1, 0)
    return header + struct.pack("<2H2I", chunk_type, 0, blocks, 12 + len(payload)) + payload


class ImageTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "test.img"

    def tearDown(self):
        self.temp.cleanup()

    def check_image(self, data):
        self.path.write_bytes(data)
        return MODULE.inspect_image(self.path)

    def test_sparse_expansion_not_download_length(self):
        result = self.check_image(sparse())
        self.assertEqual(result["expandedBytes"], 8192)
        self.assertFalse(result["flashReady"])

    def test_fill_chunk(self):
        self.assertEqual(self.check_image(sparse(0xCAC2, payload=b"1234"))["expandedBytes"], 8192)

    def test_raw_chunk(self):
        self.assertEqual(self.check_image(sparse(0xCAC1, 1, b"\0" * 4096))["chunks"], 1)

    def test_reject_bad_chunks(self):
        for data in (sparse(0xDEAD), sparse(0xCAC1), sparse(declared_blocks=1),
                     sparse(declared_blocks=3), sparse() + b"extra", sparse()[:-1],
                     sparse(0xCAC4, 1, b"1234")):
            with self.subTest(data=data[:40]), self.assertRaises(ValueError):
                self.check_image(data)

    def test_reject_invalid_header(self):
        data = bytearray(sparse())
        struct.pack_into("<H", data, 4, 2)
        with self.assertRaises(ValueError):
            self.check_image(data)

    def test_raw_ext4(self):
        data = bytearray(4096)
        struct.pack_into("<I", data, 1028, 4)
        struct.pack_into("<H", data, 1080, 0xEF53)
        result = self.check_image(data)
        self.assertEqual(result["format"], "raw-ext4")
        self.assertEqual(result["expandedBytes"], 4096)
        self.assertFalse(result["flashReady"])

    def test_ext4_truncation(self):
        data = bytearray(4096)
        struct.pack_into("<I", data, 1028, 10)
        struct.pack_into("<H", data, 1080, 0xEF53)
        with self.assertRaises(ValueError):
            self.check_image(data)

    def test_xz_and_html_rejected(self):
        for data in (b"\xfd7zXZ\x00" + b"\0" * 100, b"<html>error</html>", b""):
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.check_image(data)

    def test_cli_size_gate(self):
        self.path.write_bytes(sparse())
        for size, code, fits in ((8191, 3, False), (8192, 0, True)):
            proc = subprocess.run([sys.executable, str(SCRIPT), str(self.path),
                                   "--partition-bytes", str(size)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, code, proc.stderr)
            report = json.loads(proc.stdout)
            self.assertEqual(report["fitsMeasuredPartition"], fits)
            self.assertFalse(report["flashReady"])

    def test_cli_without_size_does_not_approve(self):
        self.path.write_bytes(sparse())
        proc = subprocess.run([sys.executable, str(SCRIPT), str(self.path)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIsNone(json.loads(proc.stdout)["fitsMeasuredPartition"])


if __name__ == "__main__":
    unittest.main()
