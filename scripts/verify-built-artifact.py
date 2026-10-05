#!/usr/bin/env python3
"""Bind a downloaded ROM to its build receipt and inspect it without flashing."""
import argparse
import hashlib
import importlib.util
import json
import lzma
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('ctz_content', ROOT / 'scripts/verify-rom-content.py')
CONTENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTENT)
NAME = 'suiram-ctz-android10-system.img.xz'
MAX_IMAGE_BYTES = 8 * 1024 ** 3
CHUNK = 1024 * 1024


def regular(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('Expected regular artifact file: ' + str(path))
    return path


def receipt_for(report):
    if (report / 'records').is_symlink():
        raise ValueError('Build record directory must not be a symlink')
    receipts = []
    for path in report.glob('records/build-attempt-*/build-receipt.json'):
        regular(path)
        if path.parent.is_symlink() or path.stat().st_size > 1024 * 1024:
            raise ValueError('Invalid build receipt file')
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('Build receipt must be a JSON object')
        if data.get('status') == 'systemimage-produced-unverified-on-device':
            receipts.append(data)
    if len(receipts) != 1:
        raise ValueError('Expected exactly one completed system image receipt')
    receipt = receipts[0]
    image = receipt.get('image', {})
    if not isinstance(image, dict):
        raise ValueError('Build receipt image must be a JSON object')
    if not re.fullmatch(r'[0-9a-f]{64}', str(image.get('SHA256', ''))):
        raise ValueError('Invalid raw-image checksum in receipt')
    size = image.get('fileBytes')
    if type(size) is not int or not 0 < size <= MAX_IMAGE_BYTES:
        raise ValueError('Invalid or excessive raw-image size in receipt')
    return receipt


def expand_xz(source, target, limit):
    """Bound both XZ dictionary allocation and the emitted image size."""
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ, memlimit=256 * CHUNK)
    total = 0
    digest = hashlib.sha256()
    with source.open('rb') as stream, target.open('xb') as output:
        while not decoder.eof:
            data = stream.read(65536) if decoder.needs_input else b''
            if decoder.needs_input and not data:
                raise ValueError('Truncated compressed image')
            block = decoder.decompress(data, max_length=CHUNK)
            total += len(block)
            if total > limit:
                raise ValueError('Expanded image exceeds its receipt size')
            output.write(block)
            digest.update(block)
        if decoder.unused_data or stream.read(1):
            raise ValueError('Unexpected trailing data or concatenated XZ stream')
    return total, digest.hexdigest()


def prepare_image(image_dir, report_dir, destination):
    for root in (image_dir, report_dir):
        if root.is_symlink() or not root.is_dir():
            raise ValueError('Artifact root must be a regular directory')
    if destination.exists() or destination.is_symlink():
        raise ValueError('Inspection directory already exists')
    receipt = receipt_for(report_dir)
    compressed = regular(image_dir / NAME)
    checksum = regular(image_dir / 'SHA256SUMS')
    if checksum.stat().st_size > 1024:
        raise ValueError('Unexpected compressed checksum file size')
    lines = checksum.read_text(encoding='ascii').splitlines()
    if len(lines) != 1 or not re.fullmatch(r'[0-9a-f]{64}  ' + re.escape(NAME), lines[0]):
        raise ValueError('Unexpected compressed checksum record')
    expected = lines[0][:64]
    if CONTENT.file_sha256(compressed) != expected:
        raise ValueError('Compressed image checksum mismatch')
    if shutil.disk_usage(destination.parent).free < receipt['image']['fileBytes'] + 1024 ** 3:
        raise ValueError('Not enough space to unpack the image with a 1 GiB reserve')
    destination.mkdir()
    partial = destination / 'system.img.partial'
    count, digest = expand_xz(compressed, partial, receipt['image']['fileBytes'])
    if count != receipt['image']['fileBytes'] or digest != receipt['image']['SHA256']:
        raise ValueError('Expanded image differs from its build receipt')
    image = destination / 'system.img'
    partial.rename(image)
    return image, receipt, expected


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image-dir', type=Path, required=True)
    parser.add_argument('--build-report-dir', type=Path, required=True)
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--partition-bytes', type=int, required=True)
    parser.add_argument('--build-run-id', type=int, required=True)
    args = parser.parse_args(argv)
    if args.partition_bytes <= 0 or args.build_run_id <= 0:
        parser.error('Partition size and build run ID must be positive')
    if args.output.exists() or args.output.is_symlink():
        parser.error('Output report already exists')
    result = {'status': 'inspection-failed', 'buildRunId': args.build_run_id,
              'partitionBytes': args.partition_bytes, 'bootTested': False,
              'restorationVerified': False, 'flashReady': False}
    code = 1
    try:
        image, receipt, compressed_digest = prepare_image(args.image_dir, args.build_report_dir, args.work_dir)
        result.update(CONTENT.verify_image(image))
        result.update({'buildRunId': args.build_run_id, 'partitionBytes': args.partition_bytes,
                       'compressedSHA256': compressed_digest, 'buildReceiptImageSHA256': receipt['image']['SHA256'],
                       'buildReceiptMatched': result['imageSHA256'] == receipt['image']['SHA256']})
        if not result['buildReceiptMatched']:
            raise ValueError('Inspected image differs from the build receipt')
        result['fitsMeasuredPartition'] = result['geometry']['expandedBytes'] <= args.partition_bytes
        if not result['systemAsRootLayout']:
            raise ValueError('CTZ requires the measured system-as-root layout')
        if not result['fitsMeasuredPartition']:
            result['status'] = 'content-checked-capacity-exceeded'
            result['error'] = 'Expanded system image exceeds the measured device partition'
            code = 3
        else:
            result['status'] = 'content-and-measured-capacity-checked'
            code = 0
    except (OSError, ValueError, UnicodeError, lzma.LZMAError, subprocess.SubprocessError, struct.error) as error:
        result['status'] = 'inspection-failed'
        result['error'] = str(error)
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(result, output, indent=2, ensure_ascii=False)
        output.write('\n')
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return code


if __name__ == '__main__':
    sys.exit(main())
