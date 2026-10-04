#!/usr/bin/env python3
"""Attempt the full Android systemimage build on an ephemeral GitHub-hosted runner."""
import importlib.util
import json
import os
import signal
import shutil
import subprocess
import sys
import time
from pathlib import Path

from source_manifest import ROOT

SPEC = importlib.util.spec_from_file_location('ctz_cloud_workflow', ROOT / 'scripts/build-workflow.py')
FLOW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FLOW)

# Experimental attempt limits, NOT estimates that the full build will fit.
# The normal desktop workflow retains its conservative 400/150 GiB policies.
SOURCE_ATTEMPT_FREE = 60 * 1024 ** 3
OUTPUT_ATTEMPT_FREE = 20 * 1024 ** 3
# Leave time and disk space for the failure report, not just the build process.
REPORT_RESERVE_FREE = 3 * 1024 ** 3
ATTEMPT_SECONDS = 315 * 60
SYNC_JOBS = 4


def disk_free(workspace):
    # The compressed filesystem is backed by a sparse file. Its virtual free
    # space must never hide exhaustion of the real runner filesystem.
    paths = [workspace.parent]
    if os.environ.get('CTZ_COMPRESSED_STORAGE') == 'true':
        paths.append(Path(os.environ['RUNNER_TEMP']))
    return min(shutil.disk_usage(path).free for path in paths)


def compiler_jobs(memory_bytes, cpu_count):
    # A public runner reported ~15.6 GiB usable RAM. Use its four CPUs, but
    # retain the lower-memory policy and never scale beyond four compiler jobs.
    memory_limit = 4 if memory_bytes >= 14 * 1024 ** 3 else 2
    return min(memory_limit, max(1, cpu_count or 1))


def follow_logs(workspace, offsets):
    """Mirror newly written stage/compiler logs without walking the source tree."""
    records = workspace / 'records'
    if records.is_symlink():
        raise ValueError('Refusing report directory symlink')
    paths = list((records / 'logs').glob('*.log'))
    paths += list(records.glob('build-attempt-*/build.log'))
    for path in sorted(paths):
        if path.is_symlink() or not path.is_file() or path.parent.is_symlink():
            continue
        previous = offsets.get(path, 0)
        size = path.stat().st_size
        if size < previous:
            raise ValueError('Build log was truncated: ' + str(path))
        if size == previous:
            continue
        # Retain complete files in the artifact; bound each console burst.
        start = max(previous, size - 256 * 1024)
        with path.open('rb') as stream:
            stream.seek(start)
            data = stream.read(size - start)
        print('\n--- ' + str(path.relative_to(workspace)) + ' ---', flush=True)
        if start != previous:
            print('[Console burst limited; full output remains in the report file.]', flush=True)
        print(data.decode('utf-8', errors='replace'), end='', flush=True)
        offsets[path] = size


def stop_group(process):
    """Stop Repo/compiler children too, then allow receipts to be written."""
    try:
        os.killpg(process.pid, signal.SIGINT)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
    else:
        # A child that ignored SIGINT must not outlive an already-exited leader.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def supervise(command, workspace, *, budget=ATTEMPT_SECONDS, interval=10):
    started = time.monotonic()
    offsets = {}
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, start_new_session=True)
    try:
        while process.poll() is None:
            follow_logs(workspace, offsets)
            free = disk_free(workspace)
            elapsed = time.monotonic() - started
            print(json.dumps({'cloudHeartbeat': True, 'elapsedSeconds': round(elapsed),
                              'freeBytes': free, 'reportReserveBytes': REPORT_RESERVE_FREE}), flush=True)
            if free < REPORT_RESERVE_FREE:
                raise ValueError('Stopping build before disk exhaustion; preserving report space')
            if elapsed >= budget:
                raise ValueError('Cloud attempt time budget exhausted; preserving stage logs')
            time.sleep(interval)
        follow_logs(workspace, offsets)
        return process.returncode
    finally:
        # The leader may exit while a child still runs. Signal the original group regardless.
        stop_group(process)
        follow_logs(workspace, offsets)


def interrupted(signum, frame):
    raise KeyboardInterrupt('Cloud supervisor received signal ' + str(signum))


def cloud_stage(stage, context, state, log):
    if stage == 'build' and os.environ.get('CTZ_COMPRESSED_STORAGE') == 'true' and \
            disk_free(context['records']) < OUTPUT_ATTEMPT_FREE:
        raise ValueError('At least 20 GiB of real backing space is required before compilation')
    if stage == 'init':
        FLOW.check_manifest_checkout(context['source'], context['revision'], allow_missing=True)
        FLOW.run_command(['repo', 'init', '-u', FLOW.MANIFEST_REPO, '-b', context['revision'],
                          '-m', FLOW.MANIFEST_NAME, '-g', 'all', '--no-clone-bundle',
                          '--depth=1', '--partial-clone', '--clone-filter=blob:none'], context['source'], log)
        FLOW.check_manifest_checkout(context['source'], context['revision'])
    elif stage == 'sync':
        # Source download concurrency is independent of the memory-limited compiler.
        FLOW.perform_stage(stage, dict(context, jobs=SYNC_JOBS), state, log)
    else:
        FLOW.perform_stage(stage, context, state, log)
    log.write((json.dumps({'freeBytesAfterStage': disk_free(context['records']),
                           'effectiveMemoryBytes': FLOW.BUILD.effective_memory()}) + '\n').encode())


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    worker = bool(args and args[0] == '--worker')
    if worker:
        args.pop(0)
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted':
        print('This experimental policy is restricted to an ephemeral GitHub-hosted runner.', file=sys.stderr)
        return 2
    if len(args) != 1:
        print('Usage: run-github-rom-build.py NEW_WORKSPACE', file=sys.stderr)
        return 2
    workspace = Path(args[0])
    if workspace.is_symlink() or not workspace.parent.is_dir():
        raise ValueError('Use a new workspace under an existing runner directory')
    workspace = workspace.resolve()
    runner_temp = Path(os.environ['RUNNER_TEMP']).resolve()
    if not workspace.is_relative_to(runner_temp):
        raise ValueError('Cloud workspace must be inside RUNNER_TEMP')
    FLOW.BUILD.MIN_FREE = OUTPUT_ATTEMPT_FREE
    host = FLOW.BUILD.host_report(workspace.parent)
    if os.environ.get('CTZ_COMPRESSED_STORAGE') == 'true':
        host['freeOutputBytes'] = min(host['freeOutputBytes'], disk_free(workspace))
    jobs = compiler_jobs(host['effectiveMemoryBytes'], os.cpu_count())
    if host['freeOutputBytes'] < SOURCE_ATTEMPT_FREE:
        host['blockers'].append('Experimental cloud attempt requires at least 60 GiB free before sync')
    if shutil.which('repo') is None:
        host['blockers'].append('Pinned Repo launcher is missing')
    print(json.dumps({'policy': 'experimental-github-attempt-not-capacity-guarantee', 'host': host,
                      'compilerJobs': jobs,
                      'manifestRevision': FLOW.PINNED_MANIFEST_REVISION,
                      'cloudBuilderSHA256': FLOW.BUILD.sha256_file(Path(__file__)),
                      'flashReady': False, 'bootTested': False}, indent=2), flush=True)
    if host['blockers']:
        return 2
    if worker:
        state = FLOW.run_pipeline(workspace, FLOW.PINNED_MANIFEST_REVISION, jobs=jobs,
                                  perform=cloud_stage)
        print(json.dumps(state, indent=2), flush=True)
        return 0
    if workspace.exists():
        raise ValueError('Cloud attempt requires a new workspace')
    return supervise([sys.executable, '-u', str(Path(__file__).resolve()), '--worker', str(workspace)],
                     workspace)


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, interrupted)
    try:
        sys.exit(main())
    except KeyboardInterrupt as error:
        print('Build interrupted: ' + str(error), file=sys.stderr)
        sys.exit(130)
    except (OSError, ValueError, KeyError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
