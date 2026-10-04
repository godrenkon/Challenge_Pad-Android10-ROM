#!/usr/bin/env python3
"""Create compressed build storage only on an ephemeral GitHub-hosted runner."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

VIRTUAL_BYTES = 256 * 1024 ** 3
MIN_BACKING_FREE = 60 * 1024 ** 3


def command(argv):
    return subprocess.run(argv, check=True, capture_output=True, text=True).stdout


def prepare(root):
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted':
        raise ValueError('Storage setup is restricted to an ephemeral GitHub-hosted runner')
    root = Path(root)
    expected = Path(os.environ['RUNNER_TEMP'])
    if root.is_symlink() or not root.is_dir() or root.resolve() != expected.resolve():
        raise ValueError('Use the existing RUNNER_TEMP directory')
    root = root.resolve()
    if root == Path(root.anchor):
        raise ValueError('RUNNER_TEMP cannot be the filesystem root')
    if shutil.disk_usage(root).free < MIN_BACKING_FREE:
        raise ValueError('At least 60 GiB of real backing space is required')
    image = root / 'ctz-build-storage.btrfs'
    mount = root / 'ctz-rom-storage'
    report = root / 'ctz-storage-report.json'
    if any(p.exists() or p.is_symlink() for p in (image, mount, report)):
        raise ValueError('Storage setup requires new paths; existing storage is never formatted')
    # Exclusive creation, no fallocate: preallocation would consume backing
    # space and defeat the purpose of a compressed sparse-file filesystem.
    with image.open('xb') as stream:
        stream.truncate(VIRTUAL_BYTES)
    mount.mkdir()
    mounted = False
    try:
        command(['mkfs.btrfs', '-d', 'single', '-m', 'single', str(image)])
        command(['sudo', 'mount', '-o', 'loop,compress-force=zstd:3,noatime,discard=async',
                 str(image), str(mount)])
        mounted = True
        command(['sudo', 'chown', str(os.getuid()) + ':' + str(os.getgid()), str(mount)])
        info = json.loads(command(['findmnt', '--json', '--target', str(mount),
                                   '--output', 'TARGET,FSTYPE,OPTIONS']))['filesystems']
        if len(info) != 1 or info[0]['target'] != str(mount) or info[0]['fstype'] != 'btrfs' or \
                'compress-force=zstd:3' not in info[0]['options'].split(','):
            raise ValueError('The build directory is not the expected compressed mount')
        # Verify real kernel compression before spending hours syncing/building.
        probe = mount / 'compression-probe'
        with probe.open('xb') as stream:
            block = b'CTZ Android build compression probe\n' * 1024
            for _ in range(256):
                stream.write(block)
            stream.flush()
            os.fsync(stream.fileno())
        command(['sudo', 'btrfs', 'filesystem', 'sync', str(mount)])
        table = command(['sudo', 'compsize', '-b', str(probe)])
        total = next((line.split() for line in table.splitlines() if line.startswith('TOTAL')), None)
        if total is None or len(total) < 5 or int(total[2]) >= int(total[3]):
            raise ValueError('Kernel compression probe did not reduce allocated storage')
        probe.unlink()
        command(['sudo', 'btrfs', 'filesystem', 'sync', str(mount)])
        data = {'schemaVersion': 1, 'filesystem': info[0], 'virtualBytes': VIRTUAL_BYTES,
                'backingFreeBytes': shutil.disk_usage(root).free,
                'backingAllocatedBytes': image.stat().st_blocks * 512,
                'compressionProbe': table, 'capacityGuaranteed': False,
                'bootTested': False, 'flashReady': False}
        report.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(data, indent=2))
        return data
    except BaseException:
        if mounted:
            command(['sudo', 'umount', str(mount)])
        raise


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise ValueError('Usage: prepare-cloud-storage.py RUNNER_TEMP')
        prepare(sys.argv[1])
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
