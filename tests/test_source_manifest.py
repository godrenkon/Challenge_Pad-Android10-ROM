"""Offline source-lock tests. Tiny local repositories are not Android checkouts."""
import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import source_manifest as SM


class RecipeTest(unittest.TestCase):
    def test_committed_recipe_and_pins(self):
        root = SM.checked_recipe()
        projects = SM.project_map(root)
        self.assertEqual(len(projects), 762)
        pinned = [p for p in projects.values() if SM.SHA.fullmatch(p.get("revision", ""))]
        self.assertEqual(len(pinned), 27)
        self.assertEqual(root.find("default").get("revision"), SM.TAG)
        self.assertEqual(projects["build/make"].find("copyfile").get("dest"), "Makefile")
        self.assertIsNone(root.find("repo-hooks"))
        for name in ("vendor/magisk", "vendor/gapps", "vendor/foss", "vendor/gapps-go"):
            self.assertNotIn(name, projects)

    def test_cached_manifest_edit_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "config").mkdir()
            (root / "manifest/upstream").mkdir(parents=True)
            (root / "config/source-provenance.json").write_bytes((ROOT / "config/source-provenance.json").read_bytes())
            (root / "manifest/upstream/aosp-default.xml").write_bytes(b"<manifest/>\n")
            with patch.object(SM, "ROOT", root), self.assertRaises(ValueError):
                SM.render_recipe()

    def test_bad_xml_and_unsafe_project_paths_refused(self):
        for data in (b"<manifest", b"<!DOCTYPE manifest><manifest/>", b"<other/>"):
            with self.assertRaises(ValueError):
                SM.parse_xml(data)
        for path in ("../escape", "/absolute", "a//b", "a\\b", "a/./b"):
            with self.assertRaises(ValueError):
                SM.project_map(SM.parse_xml(f'<manifest><project path="{path}" name="x"/></manifest>'.encode()))


class CheckoutTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "android"
        self.root.mkdir()
        self.repo = self.root / "frameworks/example"
        self.repo.mkdir(parents=True)
        self.cmd("init", "-q")
        self.cmd("config", "user.name", "Offline fixture")
        self.cmd("config", "user.email", "fixture@example.invalid")
        self.cmd("remote", "add", "aosp", "https://android.googlesource.com/platform/example")
        (self.repo / "tracked.txt").write_text("fixture\n")
        (self.repo / ".gitignore").write_text("ignored/\n")
        self.cmd("add", ".")
        self.cmd("commit", "-qm", "Synthetic fixture")
        self.cmd("tag", SM.TAG.removeprefix("refs/tags/"))
        self.head = self.cmd("rev-parse", "HEAD").strip()
        self.recipe = SM.parse_xml(('<manifest><remote name="aosp" fetch="https://android.googlesource.com/"/>'
                                    f'<default remote="aosp" revision="{SM.TAG}"/>'
                                    '<project path="frameworks/example" name="platform/example"/></manifest>').encode())

    def tearDown(self):
        self.temp.cleanup()

    def cmd(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True,
                              capture_output=True, text=True).stdout

    def inspect(self, **kwargs):
        return SM.inspect_sources(self.root, self.recipe, **kwargs)

    def test_clean_local_checkout_locks_and_verifies(self):
        heads = self.inspect()
        self.assertEqual(heads, {"frameworks/example": self.head})
        lock = Path(self.temp.name) / "lock.xml"
        lock.write_bytes(SM.locked_bytes(self.recipe, heads))
        self.assertEqual(SM.read_lock(lock, self.recipe), heads)
        self.assertEqual(self.inspect(expected_heads=heads), heads)

    def test_wrong_head_or_lock_refused(self):
        with self.assertRaises(ValueError):
            self.inspect(expected_heads={"frameworks/example": "0" * 40})
        (self.repo / "tracked.txt").write_text("second\n")
        self.cmd("commit", "-qam", "Different commit")
        with self.assertRaises(ValueError):
            self.inspect()

    def test_wrong_remote_refused(self):
        self.cmd("remote", "set-url", "aosp", "https://example.invalid/platform/example")
        with self.assertRaises(ValueError):
            self.inspect()

    def test_annotated_tag_resolves_to_commit(self):
        tag = SM.TAG.removeprefix("refs/tags/")
        self.cmd("tag", "-d", tag)
        self.cmd("tag", "-am", "Annotated fixture tag", tag)
        self.assertNotEqual(self.cmd("rev-parse", SM.TAG).strip(), self.head)
        self.assertEqual(self.inspect(), {"frameworks/example": self.head})

    def test_dirty_tracked_untracked_and_ignored_refused(self):
        for filename in ("tracked.txt", "new.txt", "ignored/Android.bp"):
            path = self.repo / filename
            path.parent.mkdir(exist_ok=True)
            path.write_text("changed\n")
            with self.assertRaises(ValueError):
                self.inspect()
            if filename == "tracked.txt":
                self.cmd("checkout", "--", filename)
            else:
                path.unlink()
                if filename.startswith("ignored/"):
                    path.parent.rmdir()

    def test_assume_unchanged_and_skip_worktree_refused(self):
        for flag in ("--assume-unchanged", "--skip-worktree"):
            self.cmd("update-index", flag, "tracked.txt")
            (self.repo / "tracked.txt").write_text("hidden source change\n")
            self.assertEqual(self.cmd("status", "--porcelain"), "")
            with self.assertRaises(ValueError):
                self.inspect()
            self.cmd("update-index", "--no-assume-unchanged", "tracked.txt")
            self.cmd("update-index", "--no-skip-worktree", "tracked.txt")
            self.cmd("checkout", "--", "tracked.txt")

    def test_allowed_patch_paths_only(self):
        (self.repo / "approved.mk").write_text("fixture patch\n")
        self.assertEqual(self.inspect(allowed_changes={"frameworks/example": {"approved.mk"}}),
                         {"frameworks/example": self.head})
        (self.repo / "other.mk").write_text("unrecorded\n")
        with self.assertRaises(ValueError):
            self.inspect(allowed_changes={"frameworks/example": {"approved.mk"}})

    def test_project_symlink_refused(self):
        outside = Path(self.temp.name) / "elsewhere"
        self.repo.rename(outside)
        self.repo.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.inspect()

    def test_lock_metadata_changes_refused(self):
        lock = Path(self.temp.name) / "lock.xml"
        data = SM.locked_bytes(self.recipe, self.inspect())
        for modified in (data.replace(b"android.googlesource.com", b"example.invalid"),
                         data.replace(self.head.encode(), b"refs/heads/main"),
                         data.replace(b"platform/example", b"platform/wrong")):
            lock.write_bytes(modified)
            with self.assertRaises(ValueError):
                SM.read_lock(lock, self.recipe)

    def test_lock_cannot_change_fixed_commit(self):
        recipe = copy.deepcopy(self.recipe)
        recipe.find("project").set("revision", self.head)
        lock = Path(self.temp.name) / "lock.xml"
        lock.write_bytes(SM.locked_bytes(recipe, {"frameworks/example": "0" * 40}))
        with self.assertRaises(ValueError):
            SM.read_lock(lock, recipe)

    def test_rename_is_not_treated_as_allowed_file(self):
        self.cmd("mv", "tracked.txt", "renamed.txt")
        with self.assertRaises(ValueError):
            self.inspect(allowed_changes={"frameworks/example": {"tracked.txt", "renamed.txt"}})


if __name__ == "__main__":
    unittest.main()
