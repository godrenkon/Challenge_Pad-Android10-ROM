#!/usr/bin/env python3
"""Attempt the full Android systemimage build on an ephemeral GitHub-hosted runner."""
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

from source_manifest import ROOT

SPEC = importlib.util.spec_from_file_location('ctz_cloud_workflow', ROOT / 'scripts/build-workflow.py')
FLOW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FLOW)

# Experimental attempt limits, NOT estimates that the full build will fit.
# The normal desktop workflow retains its conservative 400/150 GiB policies.
SOURCE_ATTEMPT_FREE = 60 * 1024 ** 3
OUTPUT_ATTEMPT_FREE = 20 * 1024 ** 3


def cloud_stage(stage, context, state, log):
    if stage == 'init':
        FLOW.check_manifest_checkout(context['source'], context['revision'], allow_missing=True)
        FLOW.run_command(['repo', 'init', '-u', FLOW.MANIFEST_REPO, '-b', context['revision'],
                          '-m', FLOW.MANIFEST_NAME, '-g', 'all', '--no-clone-bundle',
                          '--depth=1', '--partial-clone', '--clone-filter=blob:none'], context['source'], log)
        FLOW.check_manifest_checkout(context['source'], context['revision'])
    else:
        FLOW.perform_stage(stage, context, state, log)
    log.write((json.dumps({'freeBytesAfterStage': shutil.disk_usage(context['records']).free,
                           'effectiveMemoryBytes': FLOW.BUILD.effective_memory()}) + '\n').encode())


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
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
    if host['freeOutputBytes'] < SOURCE_ATTEMPT_FREE:
        host['blockers'].append('Experimental cloud attempt requires at least 60 GiB free before sync')
    if shutil.which('repo') is None:
        host['blockers'].append('Pinned Repo launcher is missing')
    print(json.dumps({'policy': 'experimental-github-attempt-not-capacity-guarantee', 'host': host,
                      'manifestRevision': FLOW.PINNED_MANIFEST_REVISION,
                      'cloudBuilderSHA256': FLOW.BUILD.sha256_file(Path(__file__)),
                      'flashReady': False, 'bootTested': False}, indent=2), flush=True)
    if host['blockers']:
        return 2
    state = FLOW.run_pipeline(workspace, FLOW.PINNED_MANIFEST_REVISION, jobs=2,
                              perform=cloud_stage)
    print(json.dumps(state, indent=2), flush=True)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
