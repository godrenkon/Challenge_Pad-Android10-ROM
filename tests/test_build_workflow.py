"""Offline workflow tests with injected stages; never download/build Android."""
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("ctz_workflow", ROOT / "scripts/build-workflow.py")
FLOW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FLOW)
REVISION = "89e0df49cc69e650839e713059883971fd508d94"


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name) / "workspace with spaces"
        self.calls = []

    def tearDown(self):
        self.temp.cleanup()

    def fake_stage(self, stage, context, state, log):
        self.calls.append(stage)
        log.write(b"Offline fake stage only\n")
        if stage == "lock":
            context["lock"].write_bytes(b"offline synthetic lock\n")
            state["lockSHA256"] = FLOW.BUILD.sha256_file(context["lock"])
        if stage == "build":
            state["buildDirectory"] = "build-attempt-" + str(len(state["attempts"]))

    def run_fake(self, resume=False, perform=None):
        with redirect_stdout(io.StringIO()):
            return FLOW.run_pipeline(self.workspace, REVISION, 2, resume, perform=perform or self.fake_stage,
                                     recheck=lambda context, state: None)

    def state(self):
        return json.loads((self.workspace / "workflow-state.json").read_text())

    def test_stages_in_order_and_second_run_no_repeat(self):
        state = self.run_fake()
        self.assertEqual(self.calls, list(FLOW.STAGES))
        self.assertEqual(state["completed"], list(FLOW.STAGES))
        self.assertFalse(state["flashReady"])
        self.assertFalse(state["bootTested"])
        self.calls.clear()
        self.run_fake(resume=True)
        self.assertEqual(self.calls, [])
        self.assertEqual(len(self.state()["attempts"]), 5)

    def test_failure_stops_and_resume_only_retries_remaining(self):
        def fail(stage, context, state, log):
            if stage == "sync":
                self.calls.append(stage)
                raise ValueError("synthetic sync failure")
            self.fake_stage(stage, context, state, log)
        with self.assertRaises(ValueError):
            self.run_fake(perform=fail)
        self.assertEqual(self.calls, ["init", "sync"])
        self.assertEqual(self.state()["completed"], ["init"])
        self.assertEqual(self.state()["attempts"][-1]["status"], "failed-or-interrupted")
        old_log = (self.workspace / "records/logs/2-sync.log").read_bytes()
        self.calls.clear()
        self.run_fake(resume=True)
        self.assertEqual(self.calls, ["sync", "lock", "prepare", "build"])
        self.assertEqual((self.workspace / "records/logs/2-sync.log").read_bytes(), old_log)
        self.assertTrue((self.workspace / "records/logs/3-sync.log").is_file())

    def test_interrupt_record_is_saved(self):
        def interrupt(stage, *_):
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.run_fake(perform=interrupt)
        self.assertEqual(self.state()["completed"], [])
        self.assertEqual(self.state()["status"], "failed-or-interrupted")

    def test_existing_directory_is_not_adopted_or_overwritten(self):
        self.workspace.mkdir()
        sentinel = self.workspace / "user-file.txt"
        sentinel.write_text("must survive")
        for resume in (False, True):
            with self.assertRaises((OSError, ValueError)):
                self.run_fake(resume=resume)
        self.assertEqual(sentinel.read_text(), "must survive")
        self.assertEqual(list(self.workspace.iterdir()), [sentinel])

    def test_revision_or_tool_identity_change_refused(self):
        self.run_fake()
        expected = FLOW.identity(self.workspace, "1" * 40)
        with self.assertRaises(ValueError):
            FLOW.validate_workspace(self.workspace, expected, True)
        expected = FLOW.identity(self.workspace, REVISION)
        expected["inputSHA256"]["gsi/ctz_locale.mk"] = "0" * 64
        with self.assertRaises(ValueError):
            FLOW.validate_workspace(self.workspace, expected, True)

    def test_corrupt_stage_history_refused(self):
        self.run_fake()
        state = self.state()
        state["completed"] = ["sync", "init"]
        FLOW.atomic_json(self.workspace / "workflow-state.json", state)
        with self.assertRaises(ValueError):
            self.run_fake(resume=True)

    def test_unknown_workspace_files_refused(self):
        self.run_fake()
        (self.workspace / "unexpected").write_text("user content")
        with self.assertRaises(ValueError):
            self.run_fake(resume=True)

    def test_managed_directory_symlink_refused(self):
        self.run_fake()
        records = self.workspace / "records"
        outside = Path(self.temp.name) / "outside"
        records.rename(outside)
        records.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.run_fake(resume=True)

    def test_state_build_path_traversal_refused(self):
        self.run_fake()
        state = self.state()
        state["buildDirectory"] = "../../outside"
        FLOW.atomic_json(self.workspace / "workflow-state.json", state)
        with self.assertRaises(ValueError):
            self.run_fake(resume=True)

    def test_concurrent_runner_lock_refused(self):
        self.run_fake()
        with FLOW.workspace_lock(self.workspace), self.assertRaises(ValueError):
            self.run_fake(resume=True)

    def test_completed_stages_are_rechecked_before_new_mutation(self):
        def fail(stage, context, state, log):
            if stage == "sync":
                raise ValueError("stop fixture")
            self.fake_stage(stage, context, state, log)
        with self.assertRaises(ValueError):
            self.run_fake(perform=fail)
        before = (self.workspace / "workflow-state.json").read_bytes()
        def bad_recheck(*_):
            raise ValueError("source changed after previous run")
        with self.assertRaises(ValueError), redirect_stdout(io.StringIO()):
            FLOW.run_pipeline(self.workspace, REVISION, 2, True, perform=self.fake_stage, recheck=bad_recheck)
        self.assertEqual((self.workspace / "workflow-state.json").read_bytes(), before)

    def test_default_preview_has_no_writes_or_commands(self):
        ready = {"blockers": [], "freeOutputBytes": FLOW.NEW_WORKSPACE_FREE}
        with patch.object(FLOW.BUILD, "host_report", return_value=ready), \
                patch.object(FLOW.shutil, "which", return_value="/fake/repo"), \
                patch.object(FLOW, "run_pipeline") as run, redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(FLOW.main([str(self.workspace), "--project-revision", REVISION]), 0)
            run.assert_not_called()
            self.assertIn("検査のみ", stdout.getvalue())
        self.assertFalse(self.workspace.exists())

    def test_host_blocker_prevents_even_explicit_run(self):
        blocked = {"blockers": ["synthetic capacity failure"], "freeOutputBytes": 1}
        with patch.object(FLOW.BUILD, "host_report", return_value=blocked), \
                patch.object(FLOW.shutil, "which", return_value=None), \
                patch.object(FLOW, "run_pipeline") as run, redirect_stdout(io.StringIO()):
            self.assertEqual(FLOW.main([str(self.workspace), "--project-revision", REVISION, "--run"]), 2)
            run.assert_not_called()
        self.assertFalse(self.workspace.exists())

    def test_stage_command_arguments_and_no_force_operations(self):
        source = Path(self.temp.name)
        context = {"source": source, "revision": REVISION, "jobs": 2, "lock": source / "lock.xml"}
        with patch.object(FLOW, "check_manifest_checkout"), patch.object(FLOW, "check_partial_sync"), \
                patch.object(FLOW, "inspect_sources"), patch.object(FLOW, "run_command") as command:
            FLOW.perform_stage("init", context, {}, io.BytesIO())
            init = command.call_args.args[0]
            self.assertEqual(init[init.index("-b") + 1], REVISION)
            self.assertEqual(init[init.index("-g") + 1], "all")
            FLOW.perform_stage("sync", context, {}, io.BytesIO())
            sync = command.call_args.args[0]
            self.assertIn("--no-manifest-update", sync)
            self.assertIn("--fail-fast", sync)
            self.assertFalse(any(a.startswith("--force") for a in init + sync))

    def test_changed_lock_refused_on_resume(self):
        self.run_fake()
        state = self.state()
        state["completed"] = ["init", "sync", "lock"]
        lock = self.workspace / "records/source-locked.xml"
        lock.write_text("modified")
        context = {"source": self.workspace / "android", "lock": lock, "revision": REVISION}
        with patch.object(FLOW, "check_manifest_checkout"), self.assertRaisesRegex(ValueError, "lock changed"):
            FLOW.recheck_completed(context, state)

    def test_active_manifest_selection_is_checked(self):
        source = Path(self.temp.name) / "manifest-fixture"
        manifests = source / ".repo/manifests"
        candidate = manifests / FLOW.MANIFEST_NAME
        candidate.parent.mkdir(parents=True)
        candidate.write_bytes(FLOW.RECIPE.read_bytes())
        active = source / ".repo/manifest.xml"
        active.write_text('<manifest><include name="manifest/ctz-android10.xml"/></manifest>')
        def fake_git(path, *args):
            if args[0] == "rev-parse":
                return (REVISION + "\n").encode()
            if args[0] == "config":
                return b"all,platform-linux\n"
            return b""
        with patch.object(FLOW, "git", side_effect=fake_git), patch.object(FLOW, "assert_clear_index"):
            FLOW.check_manifest_checkout(source, REVISION)
            active.write_text('<manifest><include name="other.xml"/></manifest>')
            with self.assertRaises(ValueError):
                FLOW.check_manifest_checkout(source, REVISION)
            active.unlink()
            active.symlink_to(candidate)
            FLOW.check_manifest_checkout(source, REVISION)

    def test_command_failure_is_not_a_completed_stage(self):
        log = Path(self.temp.name) / "child.log"
        with log.open("wb") as stream, self.assertRaisesRegex(ValueError, "17"):
            FLOW.run_command([sys.executable, "-c", "print('fake child failure'); raise SystemExit(17)"],
                             Path(self.temp.name), stream)
        self.assertIn("fake child failure", log.read_text())

    def test_partial_prepare_rechecks_other_projects_before_retry(self):
        self.run_fake()
        state = self.state()
        state["completed"] = ["init", "sync", "lock"]
        state["attempts"] = [{"stage": "prepare", "status": "failed-or-interrupted"}]
        context = {"source": self.workspace / "android", "lock": self.workspace / "records/source-locked.xml",
                   "revision": REVISION}
        with patch.object(FLOW, "check_manifest_checkout"), patch.object(FLOW, "read_lock", return_value={}), \
                patch.object(FLOW.BUILD.PREPARE, "make_plan"), \
                patch.object(FLOW, "inspect_sources", side_effect=ValueError("edited unrelated source")) as inspect, \
                self.assertRaisesRegex(ValueError, "unrelated"):
            FLOW.recheck_completed(context, state)
        self.assertEqual(inspect.call_args.kwargs["allowed_changes"], FLOW.BUILD.SOURCE_PATCH_PATHS)


if __name__ == "__main__":
    unittest.main()
