#!/usr/bin/env python3
"""Validate a reviewed source subset; optionally install a Japanese CTZ GSI product."""
import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
BASE = "device/phh/treble/base.mk"
REGISTRY = "device/phh/treble/AndroidProducts.mk"
BLOCK = ("# BEGIN SUIRAM CTZ10 PRODUCT\n"
         "PRODUCT_MAKEFILES += $(LOCAL_DIR)/suiram_ctz10.mk\n"
         "COMMON_LUNCH_CHOICES += suiram_ctz10-userdebug\n"
         "# END SUIRAM CTZ10 PRODUCT\n")


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def safe_path(root, relative):
    parts = PurePosixPath(relative).parts
    if not parts or PurePosixPath(relative).is_absolute() or any(p in (".", "..") for p in parts):
        raise ValueError("Invalid source path")
    result = root
    for part in parts:
        result /= part
        if result.is_symlink():
            raise ValueError("Refusing source/output symlink: " + relative)
    if not result.resolve().is_relative_to(root):
        raise ValueError("Source path escapes root")
    return result


def security_versions(data, edits, expected_blob):
    before = data
    after = data
    states = []
    for edit in edits:
        old = edit["before"].encode("utf-8")
        new = edit["after"].encode("utf-8")
        if data.count(old) == 1 and data.count(new) == 0:
            states.append("original")
            after = after.replace(old, new, 1)
        elif data.count(old) == 0 and data.count(new) == 1:
            states.append("installed")
            before = before.replace(new, old, 1)
        else:
            raise ValueError("Unexpected security settings; refusing a speculative patch")
    if len(set(states)) != 1 or git_blob(before) != expected_blob:
        raise ValueError("base.mk differs from reviewed original or exact installed patch")
    return before, after


def make_plan(source_root, profile=None):
    root = Path(source_root).resolve(strict=True)
    if not root.is_dir() or root == Path(root.anchor):
        raise ValueError("Use a dedicated Android source directory, not a filesystem root")
    if root == ROOT or ROOT.is_relative_to(root):
        raise ValueError("Do not apply this to the project or its parent workspace")
    if profile is None:
        profile = json.loads((ROOT / "config/source-profile.json").read_text(encoding="utf-8"))
    observed = {}
    base_before = base_after = None
    for relative, expected in profile["requiredFiles"].items():
        path = safe_path(root, relative)
        data = path.read_bytes()
        observed[relative] = data
        if relative == BASE:
            base_before, base_after = security_versions(data, profile["securityEdits"], expected)
        elif git_blob(data) != expected:
            raise ValueError("Unreviewed source file: " + relative)
    for relative in profile["additionalRequiredPaths"]:
        path = safe_path(root, relative)
        if not path.is_file():
            raise ValueError("Missing build dependency: " + relative)
        observed[relative] = path.read_bytes()
    if base_before is None:
        raise ValueError("Profile did not validate the security patch input")

    changes = []
    def propose(relative, desired, replace=False):
        path = safe_path(root, relative)
        current = path.read_bytes() if path.exists() else None
        if current == desired:
            return
        if current is not None and not replace:
            raise ValueError("Refusing to overwrite a different existing file: " + relative)
        changes.append({"path": relative, "before": current, "after": desired})

    # Backups are immutable. All validation occurs before the first write.
    propose(BASE + ".ctz-original", base_before)
    propose("vendor/suiram/ctz/ctz_locale.mk", (ROOT / "gsi/ctz_locale.mk").read_bytes())
    propose("device/phh/treble/suiram_ctz10.mk", (ROOT / "gsi/suiram_ctz10.mk").read_bytes())

    registry_path = safe_path(root, REGISTRY)
    registry = registry_path.read_bytes() if registry_path.exists() else b""
    if registry_path.exists():
        observed[REGISTRY] = registry
    registry_text = registry.decode("utf-8")
    if "# BEGIN SUIRAM CTZ10 PRODUCT" in registry_text or "# END SUIRAM CTZ10 PRODUCT" in registry_text:
        if registry_text.count(BLOCK) != 1:
            raise ValueError("Modified or duplicate CTZ product registration")
        # Preserve the exact initial file via its immutable backup.
        backup = safe_path(root, REGISTRY + ".ctz-original")
        if not backup.is_file():
            raise ValueError("Installed registration is missing its original backup")
        original_bytes = backup.read_bytes()
        observed[REGISTRY + ".ctz-original"] = original_bytes
        expected_original = original_bytes.decode("utf-8")
        separator = "" if not expected_original or expected_original.endswith("\n") else "\n"
        if registry_text != expected_original + separator + BLOCK:
            raise ValueError("Registry changed after installation; review its diff manually")
    else:
        if "suiram_ctz10" in registry_text:
            raise ValueError("CTZ product already registered outside the managed block")
        propose(REGISTRY + ".ctz-original", registry)
        separator = "" if not registry_text or registry_text.endswith("\n") else "\n"
        propose(REGISTRY, (registry_text + separator + BLOCK).encode("utf-8"), replace=True)
    propose(BASE, base_after, replace=True)
    return root, observed, changes


def apply_plan(root, observed, changes):
    # Recheck every source/dependency and every target before any write.
    for relative, data in observed.items():
        if safe_path(root, relative).read_bytes() != data:
            raise ValueError("Source changed after validation: " + relative)
    for change in changes:
        path = safe_path(root, change["path"])
        now = path.read_bytes() if path.exists() else None
        if now != change["before"]:
            raise ValueError("Target changed after validation: " + change["path"])
    for change in changes:
        path = safe_path(root, change["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        if change["before"] is None:
            with path.open("xb") as stream:
                stream.write(change["after"])
        else:
            if path.read_bytes() != change["before"]:
                raise ValueError("Target changed during application: " + change["path"])
            # Atomic file replacement; preserve the existing source file mode.
            mode = path.stat().st_mode & 0o777
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".ctz-edit-", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(change["after"])
                stream.flush()
                os.fsync(stream.fileno())
            temporary.chmod(mode)
            os.replace(temporary, path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--apply", action="store_true", help="Explicitly write the preflighted source changes")
    args = parser.parse_args(argv)
    try:
        root, observed, changes = make_plan(args.source_root)
        if args.apply:
            apply_plan(root, observed, changes)
        print(json.dumps({"mode": "applied" if args.apply else "check-only",
                          "validated": "reviewed-source-subset-only",
                          "target": "suiram_ctz10-userdebug", "flashReady": False,
                          "changes": [{"path": item["path"],
                                       "beforeBlob": None if item["before"] is None else git_blob(item["before"]),
                                       "afterBlob": git_blob(item["after"])} for item in changes],
                          "fullAndroidBuildTested": False}, indent=2))
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
