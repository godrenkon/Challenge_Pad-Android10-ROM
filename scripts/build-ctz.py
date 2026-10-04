#!/usr/bin/env python3
"""Check a locked, patched source tree; --run explicitly builds systemimage only."""
import argparse
import hashlib
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from source_manifest import ROOT, checked_recipe, inspect_sources, read_lock

GIB = 1024 ** 3
# Conservative project preflight policy, not official Android 10 minimum requirements.
MIN_FREE = 150 * GIB
MIN_MEMORY = 8 * GIB
SOURCE_PATCH_PATHS = {"device/phh/treble": {
    "base.mk", "base.mk.ctz-original", "system.prop", "system.prop.ctz-original", "AndroidProducts.mk",
    "AndroidProducts.mk.ctz-original", "suiram_ctz10.mk"}}
BUILD_COMMAND = ('set -eo pipefail\n'
                 'source build/envsetup.sh\n'
                 'lunch suiram_ctz10-userdebug\n'
                 'm -j"$1" systemimage\n')


def load_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PREPARE = load_script("ctz_prepare", "prepare-gsi-source.py")
IMAGE = load_script("ctz_image", "inspect-system-image.py")


def effective_memory():
    memory = os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
    # A process can have less memory than the host; check known root cgroup limits too.
    for filename in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        path = Path(filename)
        if path.is_file():
            value = path.read_text().strip()
            if value.isdigit() and int(value) > 0:
                memory = min(memory, int(value))
    return memory


def host_report(destination):
    blockers = []
    if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        blockers.append("Linux x86_64 is required by this build wrapper")
    commands = [name for name in ("bash", "git", "make", "python3") if shutil.which(name) is None]
    if commands:
        blockers.append("Missing commands: " + ", ".join(commands))
    memory = effective_memory() if platform.system() == "Linux" else 0
    free = shutil.disk_usage(destination).free
    if free < MIN_FREE:
        blockers.append("Project policy requires " + str(MIN_FREE // GIB) + " GiB free on the build-output filesystem")
    if memory < MIN_MEMORY:
        blockers.append("Project policy requires 8 GiB effective memory")
    return {"system": platform.system(), "architecture": platform.machine(),
            "effectiveMemoryBytes": memory, "freeOutputBytes": free,
            "requiredFreeBytes": MIN_FREE, "requiredMemoryBytes": MIN_MEMORY,
            "blockers": blockers}


def validate_sources(root, locked_manifest):
    recipe = checked_recipe()
    heads = read_lock(locked_manifest, recipe)
    prepared_root, _, changes = PREPARE.make_plan(root)
    if changes:
        raise ValueError("Source recipe patch is not fully installed; review prepare-gsi-source.py first")
    inspect_sources(prepared_root, recipe, heads, SOURCE_PATCH_PATHS)
    return prepared_root


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compiler_cache_environment():
    """Opt in to a compiler cache only on the disposable cloud build host."""
    if os.environ.get("CTZ_COMPILER_CACHE") != "true":
        return {}
    if os.environ.get("GITHUB_ACTIONS") != "true" or \
            os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted":
        raise ValueError("Compiler cache is restricted to the GitHub-hosted build")
    cache = Path(os.environ["RUNNER_TEMP"]) / "ctz-compiler-cache"
    if cache.is_symlink() or not cache.is_dir():
        raise ValueError("Compiler cache must be a regular runner cache directory")
    executable = shutil.which("ccache")
    if not executable:
        raise ValueError("Compiler cache requested but ccache is missing")
    return {"USE_CCACHE": "1", "CCACHE_EXEC": executable,
            "CC_WRAPPER": executable, "CXX_WRAPPER": executable,
            "CCACHE_DIR": str(cache), "CCACHE_COMPILERCHECK": "content",
            "CCACHE_MAXSIZE": "7G", "CCACHE_COMPRESS": "true"}


def execute_build(root, records, jobs, lock_data):
    # records must not exist. The dedicated OUT_DIR prevents stale image reuse.
    cache_env = compiler_cache_environment()
    records.mkdir()
    with (records / "source-locked.xml").open("xb") as stream:
        stream.write(lock_data)
    for path in ("gsi/suiram_ctz10.mk", "gsi/ctz_locale.mk", "config/source-profile.json"):
        target = records / Path(path).name
        with target.open("xb") as stream:
            stream.write((ROOT / path).read_bytes())
    env = {key: os.environ[key] for key in ("PATH", "HOME", "USER", "LOGNAME", "TMPDIR") if key in os.environ}
    env.update({"LC_ALL": "C", "LANG": "C", "OUT_DIR": str(records / "out"),
                "PYTHONDONTWRITEBYTECODE": "1"})
    env.update(cache_env)
    receipt = {"target": "suiram_ctz10-userdebug", "goal": "systemimage", "jobs": jobs,
               "startedAt": datetime.now(timezone.utc).isoformat(),
               "sourceManifestSHA256": sha256_file(records / "source-locked.xml"),
               "toolingSHA256": {name: sha256_file(ROOT / "scripts" / name)
                                  for name in ("build-ctz.py", "source_manifest.py", "prepare-gsi-source.py",
                                               "inspect-system-image.py")},
               "host": {"system": platform.system(), "release": platform.release(),
                        "architecture": platform.machine(), "python": platform.python_version()},
               "status": "building", "bootTested": False, "flashReady": False}
    receipt["compilerCache"] = {"enabled": bool(cache_env), "maxSize": "7G" if cache_env else None}
    receipt_path = records / "build-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    try:
        with (records / "build.log").open("xb") as log:
            result = subprocess.run(["bash", "--noprofile", "--norc", "-c", BUILD_COMMAND,
                                     "ctz-system-build", str(jobs)], cwd=root, env=env,
                                    stdout=log, stderr=subprocess.STDOUT, check=False)
        receipt["exitCode"] = result.returncode
        if result.returncode:
            raise ValueError("Android build failed; see " + str(records / "build.log"))
        image = PREPARE.safe_path(records, "out/target/product/phhgsi_arm64_ab/system.img")
        if image.is_symlink() or not image.is_file():
            raise ValueError("Build did not produce a regular system.img in the dedicated OUT_DIR")
        receipt["image"] = {"path": str(image), "SHA256": sha256_file(image), **IMAGE.inspect_image(image)}
        receipt["status"] = "systemimage-produced-unverified-on-device"
    except (OSError, ValueError, KeyboardInterrupt) as error:
        receipt["status"] = "failed-or-interrupted"
        receipt["error"] = str(error)
        raise
    finally:
        receipt["finishedAt"] = datetime.now(timezone.utc).isoformat()
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--locked-manifest", type=Path, required=True)
    parser.add_argument("--record-dir", type=Path, required=True, help="New directory on the build-output filesystem")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.jobs <= 128:
        parser.error("--jobs must be between 1 and 128")
    try:
        if args.record_dir.exists() or args.record_dir.is_symlink() or not args.record_dir.parent.is_dir():
            raise ValueError("Use a new record directory under an existing directory")
        root = args.source_root.resolve(strict=True)
        records = args.record_dir.resolve()
        if records.is_relative_to(root) or root.is_relative_to(records):
            raise ValueError("Build records/output must be outside the source tree")
        report = host_report(records.parent)
        if report["blockers"]:
            print(json.dumps({"mode": "blocked", "host": report, "flashReady": False}, indent=2))
            return 2
        lock_data = args.locked_manifest.read_bytes()
        root = validate_sources(root, args.locked_manifest)
        if args.locked_manifest.read_bytes() != lock_data:
            raise ValueError("Source lock changed during validation")
        if args.run:
            print(json.dumps(execute_build(root, records, args.jobs, lock_data), indent=2))
        else:
            print(json.dumps({"mode": "check-only", "host": report,
                              "target": "suiram_ctz10-userdebug", "flashReady": False}, indent=2))
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
