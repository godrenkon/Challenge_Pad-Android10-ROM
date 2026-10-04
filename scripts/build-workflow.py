#!/usr/bin/env python3
"""Japanese-first orchestration of source init/sync/lock/patch/systemimage build."""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from source_manifest import ROOT, SHA, RECIPE, assert_clear_index, checked_recipe, git, inspect_sources, locked_bytes, parse_xml, project_map, read_lock

STAGES = ("init", "sync", "lock", "prepare", "build")
MANIFEST_REPO = "https://github.com/godrenkon/Challenge_Pad-Android10-ROM.git"
MANIFEST_NAME = "manifest/ctz-android10.xml"
PINNED_MANIFEST_REVISION = "38974bf7945751ad9eb38e29420c329c07f56a89"
NEW_WORKSPACE_FREE = 400 * 1024 ** 3
MESSAGES = {
    "ja": {"check": "検査のみ。ダウンロード・変更・ビルドは実行しません。",
           "blocked": "実行条件を満たしていません。", "stage": "実行中", "done": "工程完了",
           "error": "エラー", "resume": "記録済みの工程を検査して再開します。",
           "unfinished": "実機未検証。完成ROMとしては扱えません。"},
    "en": {"check": "Check only. No download, changes or build.",
           "blocked": "Host requirements are not met.", "stage": "Running", "done": "Stages completed",
           "error": "Error", "resume": "Rechecking recorded stages before resuming.",
           "unfinished": "Device boot is untested. This is not a finished ROM."}}


def load_build():
    spec = importlib.util.spec_from_file_location("ctz_workflow_build", ROOT / "scripts/build-ctz.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILD = load_build()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def identity(workspace, revision):
    checked_recipe()
    files = ("scripts/build-workflow.py", "scripts/build-ctz.py", "scripts/source_manifest.py",
             "scripts/prepare-gsi-source.py", "scripts/inspect-system-image.py",
             "config/source-profile.json", "config/source-provenance.json", "manifest/ctz-android10.xml",
             "gsi/suiram_ctz10.mk", "gsi/ctz_locale.mk")
    return {"workspace": str(workspace), "projectRevision": revision,
            "inputSHA256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}}


def atomic_json(path, data):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".ctz-state-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write((json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def validate_workspace(workspace, expected, resume):
    if workspace.is_symlink():
        raise ValueError("Refusing workspace symlink")
    if not workspace.exists():
        if resume:
            raise ValueError("No workspace exists to resume")
        return None
    if not resume:
        raise ValueError("Workspace already exists; use --resume only for a recorded CTZ workspace")
    if not workspace.is_dir():
        raise ValueError("Workspace is not a directory")
    for name in ("workflow-state.json", ".workflow.lock", "android", "records", "records/logs", "records/source-locked.xml"):
        if (workspace / name).is_symlink():
            raise ValueError("Refusing managed workspace symlink: " + name)
    state = json.loads((workspace / "workflow-state.json").read_text(encoding="utf-8"))
    if state.get("schemaVersion") != 1 or state.get("identity") != expected:
        raise ValueError("Workspace identity/tool inputs differ; do not reset or overwrite it")
    completed = state.get("completed")
    if not isinstance(completed, list) or completed != list(STAGES[:len(completed)]) or len(completed) > len(STAGES):
        raise ValueError("Invalid workflow stage history")
    attempts = state.get("attempts")
    if not isinstance(attempts, list) or any(not isinstance(a, dict) or a.get("stage") not in STAGES for a in attempts):
        raise ValueError("Invalid workflow attempt history")
    if "build" in completed and not re.fullmatch(r"build-attempt-[1-9][0-9]*", state.get("buildDirectory", "")):
        raise ValueError("Invalid completed build directory")
    allowed = {"workflow-state.json", ".workflow.lock", "android", "records"}
    if set(p.name for p in workspace.iterdir()) - allowed:
        raise ValueError("Unexpected files at workspace root; inspect them before resuming")
    if not (workspace / "android").is_dir() or not (workspace / "records/logs").is_dir():
        raise ValueError("Managed workspace directories are missing")
    return state


@contextmanager
def workspace_lock(workspace):
    # Linux host preflight occurs before this function. The file persists; the OS lock does not.
    import fcntl
    path = workspace / ".workflow.lock"
    if path.is_symlink():
        raise ValueError("Refusing workspace lock symlink")
    with path.open("a+b") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("Another workflow process is using this workspace") from error
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def check_manifest_checkout(source, revision, allow_missing=False):
    manifests = source / ".repo/manifests"
    candidate = manifests / MANIFEST_NAME
    if not candidate.is_file():
        if allow_missing:
            return
        raise ValueError("Repo manifest checkout is incomplete")
    if candidate.read_bytes() != RECIPE.read_bytes():
        raise ValueError("Downloaded manifest differs from the reviewed recipe")
    active = source / ".repo/manifest.xml"
    if active.is_symlink():
        if active.resolve() != candidate.resolve():
            raise ValueError("Active Repo manifest points at another file")
    else:
        active_data = active.read_bytes()
        if active_data != RECIPE.read_bytes():
            wrapper = parse_xml(active_data)
            if wrapper.attrib or len(wrapper) != 1 or wrapper[0].tag != "include" or \
                    wrapper[0].attrib != {"name": MANIFEST_NAME} or len(wrapper[0]):
                raise ValueError("Active Repo manifest includes unexpected source definitions")
    if git(manifests, "rev-parse", "--verify", "HEAD").decode().strip() != revision:
        raise ValueError("Manifest checkout revision differs from the requested project commit")
    if git(manifests, "status", "--porcelain=v1", "--untracked-files=all", "-z"):
        raise ValueError("Repo manifest checkout has local changes")
    assert_clear_index(manifests)
    groups = git(manifests, "config", "--get", "manifest.groups").decode().strip().split(",")
    if "all" not in groups or any(g.startswith("-") for g in groups):
        raise ValueError("Repo source groups differ from the required all-project selection")
    if (source / ".repo/local_manifests").exists() or (source / ".repo/local_manifest.xml").exists():
        raise ValueError("Extra local manifests are not supported by this workflow")


def check_partial_sync(source):
    # A partial sync may lack projects/HEADs. Refuse edited existing Git checkouts before retrying.
    for relative in project_map(checked_recipe()):
        path = BUILD.PREPARE.safe_path(source, relative)
        if not path.is_dir() or not (path / ".git").exists():
            continue
        if git(path, "status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching", "-z"):
            raise ValueError("Edited partial checkout; refusing automatic sync retry: " + relative)
        assert_clear_index(path)


def recheck_completed(context, state):
    source, lock = context["source"], context["lock"]
    done = state["completed"]
    if "init" in done:
        check_manifest_checkout(source, context["revision"])
    if "lock" in done:
        if BUILD.sha256_file(lock) != state.get("lockSHA256"):
            raise ValueError("Recorded full source lock changed")
        heads = read_lock(lock)
        # A failed/interrupted patch may already have modified approved files.
        if "prepare" in done:
            BUILD.validate_sources(source, lock)
        elif any(a["stage"] == "prepare" for a in state["attempts"]):
            BUILD.PREPARE.make_plan(source)
            inspect_sources(source, expected_heads=heads, allowed_changes=BUILD.SOURCE_PATCH_PATHS)
        else:
            inspect_sources(source, expected_heads=heads)
    elif "sync" in done:
        inspect_sources(source)
    if "build" in done:
        record = context["records"] / state["buildDirectory"]
        if record.is_symlink():
            raise ValueError("Build record symlink")
        receipt = json.loads((record / "build-receipt.json").read_text(encoding="utf-8"))
        image = BUILD.PREPARE.safe_path(record, "out/target/product/phhgsi_arm64_ab/system.img")
        if receipt.get("status") != "systemimage-produced-unverified-on-device" or \
                BUILD.sha256_file(image) != receipt["image"]["SHA256"]:
            raise ValueError("Completed build output differs from its receipt")
        if BUILD.sha256_file(record / "source-locked.xml") != state["lockSHA256"]:
            raise ValueError("Build receipt source manifest differs from the source lock")


def run_command(args, source, log):
    result = subprocess.run(args, cwd=source, stdin=subprocess.DEVNULL,
                            stdout=log, stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        raise ValueError("Command failed with exit code " + str(result.returncode) + "; see the stage log")


def perform_stage(stage, context, state, log):
    source, lock = context["source"], context["lock"]
    if stage == "init":
        check_manifest_checkout(source, context["revision"], allow_missing=True)
        run_command(["repo", "init", "-u", MANIFEST_REPO, "-b", context["revision"],
                     "-m", MANIFEST_NAME, "-g", "all", "--no-clone-bundle"], source, log)
        check_manifest_checkout(source, context["revision"])
    elif stage == "sync":
        check_manifest_checkout(source, context["revision"])
        check_partial_sync(source)
        run_command(["repo", "sync", "-c", "-j" + str(context["jobs"]),
                     "--fail-fast", "--no-manifest-update"], source, log)
        inspect_sources(source)
    elif stage == "lock":
        recipe = checked_recipe()
        data = locked_bytes(recipe, inspect_sources(source, recipe))
        if lock.exists():
            if lock.read_bytes() != data:
                raise ValueError("Existing source lock is different; refusing overwrite")
        else:
            with lock.open("xb") as stream:
                stream.write(data)
        state["lockSHA256"] = hashlib.sha256(data).hexdigest()
    elif stage == "prepare":
        root, observed, changes = BUILD.PREPARE.make_plan(source)
        BUILD.PREPARE.apply_plan(root, observed, changes)
        BUILD.validate_sources(source, lock)
    elif stage == "build":
        host = BUILD.host_report(context["records"])
        if host["blockers"]:
            raise ValueError("Build host preflight failed: " + "; ".join(host["blockers"]))
        lock_data = lock.read_bytes()
        BUILD.validate_sources(source, lock)
        if hashlib.sha256(lock_data).hexdigest() != state["lockSHA256"] or lock.read_bytes() != lock_data:
            raise ValueError("Source lock changed before build")
        dirname = "build-attempt-" + str(len(state["attempts"]))
        receipt = BUILD.execute_build(source, context["records"] / dirname, context["jobs"], lock_data)
        state["buildDirectory"] = dirname
        log.write((json.dumps(receipt, indent=2) + "\n").encode("utf-8"))
    else:
        raise ValueError("Unknown workflow stage")


def run_pipeline(workspace, revision, jobs, resume=False, language="ja", perform=None, recheck=None):
    perform = perform_stage if perform is None else perform
    recheck = recheck_completed if recheck is None else recheck
    expected = identity(workspace, revision)
    state = validate_workspace(workspace, expected, resume)
    if state is None:
        workspace.mkdir()
        (workspace / "android").mkdir()
        (workspace / "records/logs").mkdir(parents=True)
        state = {"schemaVersion": 1, "identity": expected, "completed": [], "attempts": [],
                 "status": "ready", "createdAt": stamp(), "flashReady": False, "bootTested": False}
        atomic_json(workspace / "workflow-state.json", state)
    context = {"source": workspace / "android", "records": workspace / "records",
               "lock": workspace / "records/source-locked.xml", "revision": revision, "jobs": jobs}
    with workspace_lock(workspace):
        # Reload under the OS lock so simultaneous starts/resumes cannot share stale state.
        state = validate_workspace(workspace, expected, True)
        recheck(context, state)
        for stage in STAGES[len(state["completed"]):]:
            attempt = {"stage": stage, "startedAt": stamp(), "status": "running", "jobs": jobs}
            state["attempts"].append(attempt)
            index = len(state["attempts"])
            attempt["log"] = "logs/" + str(index) + "-" + stage + ".log"
            state["status"] = "running"
            atomic_json(workspace / "workflow-state.json", state)
            print(MESSAGES[language]["stage"] + ": " + stage, flush=True)
            try:
                with (context["records"] / attempt["log"]).open("xb") as log:
                    perform(stage, context, state, log)
                state["completed"].append(stage)
                attempt["status"] = "completed"
                state["status"] = "completed" if len(state["completed"]) == len(STAGES) else "ready"
            except (OSError, ValueError, KeyError, KeyboardInterrupt) as error:
                attempt["status"] = "failed-or-interrupted"
                attempt["error"] = str(error)
                state["status"] = "failed-or-interrupted"
                if isinstance(error, KeyboardInterrupt):
                    raise
                raise ValueError(str(error) + "; stage log: " + str(context["records"] / attempt["log"])) from error
            finally:
                attempt["finishedAt"] = stamp()
                atomic_json(workspace / "workflow-state.json", state)
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--project-revision", default=PINNED_MANIFEST_REVISION,
                        help="40-character manifest-project Git commit, never main")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--language", choices=("ja", "en"), default="ja")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    if not SHA.fullmatch(args.project_revision) or not 1 <= args.jobs <= 128:
        parser.error("Use a 40-character lowercase commit and 1..128 jobs")
    messages = MESSAGES[args.language]
    try:
        if args.workspace.is_symlink():
            raise ValueError("Refusing workspace symlink")
        workspace = args.workspace.resolve()
        if not workspace.parent.is_dir() or workspace == Path(workspace.anchor) or \
                workspace.is_relative_to(ROOT) or ROOT.is_relative_to(workspace):
            raise ValueError("Use a separate workspace under an existing parent directory")
        expected = identity(workspace, args.project_revision)
        validate_workspace(workspace, expected, args.resume)
        report = BUILD.host_report(workspace / "records" if args.resume else workspace.parent)
        if shutil.which("repo") is None:
            report["blockers"].append("Install the Android Repo command before running")
        if not args.resume and report["freeOutputBytes"] < NEW_WORKSPACE_FREE:
            report["blockers"].append("New workspace policy requires 400 GiB free for source plus output")
        print(messages["resume"] if args.resume else messages["check"] if not args.run else "CTZ Android 10")
        print(json.dumps({"workspace": str(workspace), "stages": list(STAGES), "host": report,
                          "flashReady": False}, ensure_ascii=False, indent=2))
        if report["blockers"]:
            print(messages["blocked"])
            return 2
        if args.run:
            state = run_pipeline(workspace, args.project_revision, args.jobs, args.resume, args.language)
            print(messages["done"] + ": " + ", ".join(state["completed"]))
            print(messages["unfinished"])
        return 0
    except KeyboardInterrupt:
        print(messages["error"] + ": " + ("中断しました。工程記録を確認してください。" if args.language == "ja"
                                               else "Interrupted. Inspect the stage record before resuming."), file=sys.stderr)
        return 130
    except (OSError, ValueError, KeyError) as error:
        print(messages["error"] + ": " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
