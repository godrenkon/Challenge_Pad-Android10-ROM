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
        report = {'blockers': [], 'freeOutputBytes': CLOUD.SOURCE_ATTEMPT_FREE - 1}
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
        report = {'blockers': [], 'freeOutputBytes': CLOUD.SOURCE_ATTEMPT_FREE}
        with self.env(), patch.object(CLOUD.FLOW.BUILD, 'host_report', return_value=report), \
                patch.object(CLOUD.shutil, 'which', return_value='/fixture/repo'), \
                patch.object(CLOUD.FLOW, 'run_pipeline', return_value={'fixture': True}) as run, \
                redirect_stdout(io.StringIO()):
            self.assertEqual(CLOUD.main([str(self.workspace)]), 0)
            self.assertIs(run.call_args.kwargs['perform'], CLOUD.cloud_stage)
            self.assertEqual(run.call_args.kwargs['jobs'], 2)

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


if __name__ == '__main__':
    unittest.main()
