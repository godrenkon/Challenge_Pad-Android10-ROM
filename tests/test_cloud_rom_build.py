"""Cloud policy guards; these tests do not compile Android."""
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('cloud_rom', ROOT / 'scripts/run-github-rom-build.py')
CLOUD = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CLOUD)


class CloudBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / 'ctz-rom'
        self.addCleanup(setattr, CLOUD.FLOW.BUILD, 'MIN_FREE', CLOUD.FLOW.BUILD.MIN_FREE)

    def env(self):
        return patch.dict(os.environ, {'GITHUB_ACTIONS': 'true', 'RUNNER_ENVIRONMENT': 'github-hosted',
                                       'RUNNER_TEMP': str(self.root)})

    def test_not_a_general_policy_bypass(self):
        with patch.dict(os.environ, {'GITHUB_ACTIONS': 'false'}), \
                patch.object(CLOUD.FLOW, 'run_pipeline') as run:
            self.assertEqual(CLOUD.main([str(self.workspace)]), 2)
            run.assert_not_called()
        self.assertFalse(self.workspace.exists())

    def test_source_capacity_gate_stops_before_download(self):
        report = {'blockers': [], 'freeOutputBytes': CLOUD.SOURCE_ATTEMPT_FREE - 1,
                  'effectiveMemoryBytes': 8 * 1024 ** 3}
        with self.env(), patch.object(CLOUD.FLOW.BUILD, 'host_report', return_value=report), \
                patch.object(CLOUD.shutil, 'which', return_value='/fixture/repo'), \
                patch.object(CLOUD.FLOW, 'run_pipeline') as run, redirect_stdout(io.StringIO()):
            self.assertEqual(CLOUD.main([str(self.workspace)]), 2)
            run.assert_not_called()
        self.assertFalse(self.workspace.exists())

    def test_workspace_must_belong_to_runner_temp(self):
        with self.env(), self.assertRaisesRegex(ValueError, 'RUNNER_TEMP'):
            CLOUD.main([str(self.root.parent / 'outside-runner')])

    def test_success_path_runs_the_full_pipeline(self):
        report = {'blockers': [], 'freeOutputBytes': CLOUD.SOURCE_ATTEMPT_FREE,
                  'effectiveMemoryBytes': 8 * 1024 ** 3}
        with self.env(), patch.object(CLOUD.FLOW.BUILD, 'host_report', return_value=report), \
                patch.object(CLOUD.shutil, 'which', return_value='/fixture/repo'), \
                patch.object(CLOUD.os, 'cpu_count', return_value=4), \
                patch.object(CLOUD.FLOW, 'run_pipeline', return_value={'fixture': True}) as run, \
                redirect_stdout(io.StringIO()):
            self.assertEqual(CLOUD.main(['--worker', str(self.workspace)]), 0)
            self.assertIs(run.call_args.kwargs['perform'], CLOUD.cloud_stage)
            self.assertEqual(run.call_args.kwargs['jobs'], 2)

    def test_worker_uses_four_jobs_only_with_sufficient_ram_and_cpus(self):
        for memory, cpus, expected in [(16765415424, 4, 4), (16765415424, 2, 2),
                                       (8 * 1024 ** 3, 4, 2), (16765415424, None, 1)]:
            report = {'blockers': [], 'freeOutputBytes': CLOUD.SOURCE_ATTEMPT_FREE,
                      'effectiveMemoryBytes': memory}
            with self.subTest(memory=memory, cpus=cpus), self.env(), \
                    patch.object(CLOUD.FLOW.BUILD, 'host_report', return_value=report), \
                    patch.object(CLOUD.shutil, 'which', return_value='/fixture/repo'), \
                    patch.object(CLOUD.os, 'cpu_count', return_value=cpus), \
                    patch.object(CLOUD.FLOW, 'run_pipeline', return_value={}) as run, \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(CLOUD.main(['--worker', str(self.workspace)]), 0)
                self.assertEqual(run.call_args.kwargs['jobs'], expected)

    def test_clone_optimization_keeps_all_projects_and_fixed_revision(self):
        context = {'source': self.root, 'records': self.root, 'revision': '1' * 40}
        with patch.object(CLOUD.FLOW, 'check_manifest_checkout'), \
                patch.object(CLOUD.FLOW, 'run_command') as command:
            CLOUD.cloud_stage('init', context, {}, io.BytesIO())
            argv = command.call_args.args[0]
            self.assertEqual(argv[argv.index('-b') + 1], context['revision'])
            self.assertEqual(argv[argv.index('-g') + 1], 'all')
            self.assertIn('--depth=1', argv)
            self.assertIn('--clone-filter=blob:none', argv)

    def test_supervisor_returns_real_worker_failure(self):
        with redirect_stdout(io.StringIO()):
            code = CLOUD.supervise([sys.executable, '-c', 'raise SystemExit(7)'], self.workspace,
                                   interval=0.01)
        self.assertEqual(code, 7)

    def test_public_entry_uses_supervisor_and_preserves_worker_status(self):
        report = {'blockers': [], 'freeOutputBytes': CLOUD.SOURCE_ATTEMPT_FREE,
                  'effectiveMemoryBytes': 8 * 1024 ** 3}
        with self.env(), patch.object(CLOUD.FLOW.BUILD, 'host_report', return_value=report), \
                patch.object(CLOUD.shutil, 'which', return_value='/fixture/repo'), \
                patch.object(CLOUD, 'supervise', return_value=7) as supervise, \
                redirect_stdout(io.StringIO()):
            self.assertEqual(CLOUD.main([str(self.workspace)]), 7)
            self.assertEqual(supervise.call_args.args[0][-2:], ['--worker', str(self.workspace)])

    def test_budget_stops_a_running_process_group(self):
        marker = self.root / 'late-child-output'
        child = 'import time,pathlib; time.sleep(1); pathlib.Path(' + repr(str(marker)) + ').touch()'
        parent = 'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",' + repr(child) + ']); time.sleep(5)'
        with redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, 'time budget'):
            CLOUD.supervise([sys.executable, '-c', parent], self.workspace, budget=0.15, interval=0.01)
        # Make a surviving descendant observable, not just the leader's exit code.
        import time
        time.sleep(1.1)
        self.assertFalse(marker.exists())

    def test_disk_reserve_stops_before_runner_is_full(self):
        low_disk = type('Disk', (), {'free': CLOUD.REPORT_RESERVE_FREE - 1})()
        with patch.object(CLOUD.shutil, 'disk_usage', return_value=low_disk), \
                redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, 'disk exhaustion'):
            CLOUD.supervise([sys.executable, '-c', 'import time; time.sleep(5)'], self.workspace,
                             interval=0.01)

    def test_sparse_volume_cannot_hide_low_backing_disk(self):
        large = type('Disk', (), {'free': 200 * 1024 ** 3})()
        small = type('Disk', (), {'free': CLOUD.REPORT_RESERVE_FREE - 1})()
        def usage(path):
            return small if Path(path) == self.root else large
        nested = self.root / 'ctz-rom-storage/ctz-rom'
        nested.parent.mkdir()
        with self.env(), patch.dict(os.environ, {'CTZ_COMPRESSED_STORAGE': 'true'}), \
                patch.object(CLOUD.shutil, 'disk_usage', side_effect=usage), \
                redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, 'disk exhaustion'):
            CLOUD.supervise([sys.executable, '-c', 'import time; time.sleep(5)'], nested, interval=0.01)

    def test_backing_disk_is_checked_before_sync_despite_virtual_capacity(self):
        nested = self.root / 'ctz-rom-storage/ctz-rom'
        nested.parent.mkdir()
        large = type('Disk', (), {'free': 200 * 1024 ** 3})()
        small = type('Disk', (), {'free': CLOUD.SOURCE_ATTEMPT_FREE - 1})()
        report = {'blockers': [], 'freeOutputBytes': large.free, 'effectiveMemoryBytes': 16 * 1024 ** 3}
        with self.env(), patch.dict(os.environ, {'CTZ_COMPRESSED_STORAGE': 'true'}), \
                patch.object(CLOUD.FLOW.BUILD, 'host_report', return_value=report), \
                patch.object(CLOUD.shutil, 'disk_usage', side_effect=lambda p: small if Path(p) == self.root else large), \
                patch.object(CLOUD.shutil, 'which', return_value='/fixture/repo'), \
                patch.object(CLOUD.FLOW, 'run_pipeline') as run, redirect_stdout(io.StringIO()):
            self.assertEqual(CLOUD.main(['--worker', str(nested)]), 2)
            run.assert_not_called()

    def test_streams_compiler_log_incrementally(self):
        log = self.workspace / 'records/build-attempt-5/build.log'
        log.parent.mkdir(parents=True)
        log.write_bytes(b'compiler first\n')
        offsets = {}
        output = io.StringIO()
        with redirect_stdout(output):
            CLOUD.follow_logs(self.workspace, offsets)
            with log.open('ab') as stream:
                stream.write(b'compiler error\n')
            CLOUD.follow_logs(self.workspace, offsets)
            CLOUD.follow_logs(self.workspace, offsets)
        self.assertEqual(output.getvalue().count('compiler first'), 1)
        self.assertEqual(output.getvalue().count('compiler error'), 1)
        self.assertEqual(log.read_bytes(), b'compiler first\ncompiler error\n')

    def test_sync_jobs_do_not_increase_compiler_jobs(self):
        context = {'source': self.root, 'records': self.root, 'jobs': 2}
        with patch.object(CLOUD.FLOW, 'perform_stage') as perform:
            CLOUD.cloud_stage('sync', context, {}, io.BytesIO())
            self.assertEqual(perform.call_args.args[1]['jobs'], 4)
            CLOUD.cloud_stage('build', context, {}, io.BytesIO())
            self.assertEqual(perform.call_args.args[1]['jobs'], 2)
        self.assertEqual(context['jobs'], 2)


if __name__ == '__main__':
    unittest.main()
