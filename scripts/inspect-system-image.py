#!/usr/bin/env python3
"""Read-only image geometry inspection. Never establishes boot/flash safety."""
import argparse
import json
import struct
import sys
from pathlib import Path

SPARSE_MAGIC = 0xED26FF3A


def read_exact(stream, count):
    value = stream.read(count)
    if len(value) != count:
        raise ValueError("Truncated image")
    return value


def inspect_image(path):
    path = Path(path)
    size = path.stat().st_size
    with path.open("rb") as stream:
        prefix = read_exact(stream, 6)
        if prefix == b"\xfd7zXZ\x00":
            raise ValueError("XZ is compressed: extract it before image inspection")
        stream.seek(0)
        magic = struct.unpack("<I", read_exact(stream, 4))[0]
        stream.seek(0)
        if magic == SPARSE_MAGIC:
            fields = struct.unpack("<I4H4I", read_exact(stream, 28))
            _, major, minor, header_size, chunk_header_size, block_size, blocks, chunks, checksum = fields
            if major != 1 or header_size < 28 or chunk_header_size < 12:
                raise ValueError("Unsupported sparse header")
            if block_size < 4 or block_size > 1048576 or block_size % 4 or not blocks:
                raise ValueError("Invalid sparse block geometry")
            if not chunks or header_size > size or chunks > (size - header_size) // chunk_header_size:
                raise ValueError("Invalid sparse chunk count")
            stream.seek(header_size)
            output_blocks = 0
            for _ in range(chunks):
                start = stream.tell()
                chunk_type, reserved, chunk_blocks, total_size = struct.unpack("<2H2I", read_exact(stream, 12))
                if total_size < chunk_header_size or start + total_size > size:
                    raise ValueError("Truncated or invalid sparse chunk")
                payload = total_size - chunk_header_size
                expected = {0xCAC1: chunk_blocks * block_size, 0xCAC2: 4, 0xCAC3: 0, 0xCAC4: 4}
                if chunk_type not in expected or payload != expected[chunk_type]:
                    raise ValueError("Invalid sparse chunk type or payload")
                if chunk_type == 0xCAC4:
                    if chunk_blocks != 0:
                        raise ValueError("CRC chunk must not contribute output blocks")
                else:
                    output_blocks += chunk_blocks
                    if output_blocks > blocks:
                        raise ValueError("Sparse output exceeds header block count")
                stream.seek(start + total_size)
            if output_blocks != blocks or stream.tell() != size:
                raise ValueError("Sparse block count or trailing bytes mismatch")
            result = {"format": "android-sparse", "expandedBytes": blocks * block_size,
                      "blockSize": block_size, "chunks": chunks,
                      "sparseChecksumVerified": False}
        else:
            stream.seek(1024)
            superblock = read_exact(stream, 1024)
            if struct.unpack_from("<H", superblock, 56)[0] != 0xEF53:
                raise ValueError("Not a recognized raw ext4 or Android sparse image")
            log_block_size = struct.unpack_from("<I", superblock, 24)[0]
            if log_block_size > 6:
                raise ValueError("Invalid ext4 block size")
            block_size = 1024 << log_block_size
            blocks = struct.unpack_from("<I", superblock, 4)[0]
            incompat = struct.unpack_from("<I", superblock, 96)[0]
            if incompat & 0x80:
                blocks |= struct.unpack_from("<I", superblock, 0x150)[0] << 32
            filesystem_bytes = blocks * block_size
            if not blocks or filesystem_bytes > size:
                raise ValueError("Truncated ext4 image or invalid superblock")
            result = {"format": "raw-ext4", "expandedBytes": size,
                      "filesystemBytes": filesystem_bytes, "blockSize": block_size}
    result.update({"fileBytes": size, "flashReady": False,
                   "verification": "geometry-only-not-filesystem-or-boot-validation"})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--partition-bytes", type=int,
                        help="Measured system partition size, not a guessed value")
    args = parser.parse_args(argv)
    if args.partition_bytes is not None and args.partition_bytes <= 0:
        parser.error("--partition-bytes must be positive")
    try:
        result = inspect_image(args.image)
        result["partitionBytes"] = args.partition_bytes
        result["fitsMeasuredPartition"] = (None if args.partition_bytes is None else
                                            result["expandedBytes"] <= args.partition_bytes)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 3 if result["fitsMeasuredPartition"] is False else 0
    except (OSError, ValueError, struct.error) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
