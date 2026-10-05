import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ctz_source", ROOT / "scripts/prepare-gsi-source.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SourceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "android"
        self.root.mkdir()
        self.profile = json.loads((ROOT / "config/source-profile.json").read_text())
        self.base_original = (b"# synthetic offline fixture, not an Android tree\n"
                              b"PRODUCT_SYSTEM_DEFAULT_PROPERTIES += \\\n"
                              b"\tro.adb.secure=0 \\\n"
                              b"\tpersist.sys.usb.config=adb \\\n"
                              b"\tro.logd.auditd=true\n")
        self.base_original += self.profile['securityEdits'][2]['before'].encode()
        self.files = {}
        self.system_original = b"ro.adb.secure=0\nro.sys.sdcardfs=0\n# synthetic offline fixture\n"
        for relative in self.profile["requiredFiles"]:
            data = {MODULE.BASE: self.base_original, MODULE.SYSTEM_PROP: self.system_original}.get(
                relative, b"# synthetic reviewed fixture\n")
            if relative in self.profile.get("buildEdits", {}):
                data = self.profile["buildEdits"][relative][0]["before"].encode()
                data += b"\ttreble-overlay-mtk-ims \\\n\tOtherPackage\n"
            self.write(relative, data)
            self.files[relative] = data
            self.profile["requiredFiles"][relative] = MODULE.git_blob(data)
        for relative in self.profile["additionalRequiredPaths"]:
            self.write(relative, b"# synthetic build dependency fixture\n")
        self.registry = b"# user comment must survive\nPRODUCT_MAKEFILES := existing.mk\n"
        self.write(MODULE.REGISTRY, self.registry)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file()}

    def plan(self):
        return MODULE.make_plan(self.root, self.profile)

    def apply(self):
        root, observed, changes = self.plan()
        MODULE.apply_plan(root, observed, changes)
        return changes

    def test_default_plan_does_not_write(self):
        before = self.snapshot()
        _, _, changes = self.plan()
        self.assertTrue(changes)
        self.assertEqual(before, self.snapshot())

    def test_apply_and_reapply_is_noop(self):
        self.apply()
        after = self.snapshot()
        self.assertEqual(self.apply(), [])
        self.assertEqual(after, self.snapshot())

    def test_security_changes_and_backups(self):
        self.apply()
        base = (self.root / MODULE.BASE).read_bytes()
        self.assertIn(b"ro.adb.secure=1", base)
        self.assertIn(b"persist.sys.usb.config=mtp", base)
        self.assertNotIn(b"ro.adb.secure=0", base)
        self.assertNotIn(b"device/phh/treble/remote/", base)
        self.assertEqual((self.root / (MODULE.BASE + ".ctz-original")).read_bytes(), self.base_original)
        self.assertEqual((self.root / MODULE.SYSTEM_PROP).read_bytes(),
                         self.system_original.replace(b"ro.adb.secure=0", b"ro.adb.secure=1"))
        self.assertEqual((self.root / (MODULE.SYSTEM_PROP + ".ctz-original")).read_bytes(), self.system_original)
        registry = (self.root / MODULE.REGISTRY).read_bytes()
        self.assertTrue(registry.startswith(self.registry))
        self.assertEqual((self.root / (MODULE.REGISTRY + ".ctz-original")).read_bytes(), self.registry)

    def test_unknown_source_refused_before_writes(self):
        self.write("build/make/core/Makefile", b"# user-edited\n")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.apply()
        self.assertEqual(before, self.snapshot())

    def test_qti_omission_preserves_mtk_and_shared_helpers(self):
        self.apply()
        relative = "vendor/hardware_overlay/overlay.mk"
        overlay = (self.root / relative).read_bytes()
        self.assertNotIn(b"\tQtiAudio ", overlay)
        for package in (b"HardwareOverlayPicker", b"TrebleApp", b"treble-overlay-mtk-ims", b"OtherPackage"):
            self.assertIn(package, overlay)
        self.assertEqual((self.root / (relative + ".ctz-original")).read_bytes(), self.files[relative])
        self.assertEqual(self.apply(), [])

    def test_modified_overlay_refused_before_writes(self):
        relative = "vendor/hardware_overlay/overlay.mk"
        self.write(relative, self.files[relative] + b"# unexpected change\n")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.apply()
        self.assertEqual(before, self.snapshot())

    def test_missing_build_edit_validation_refused(self):
        del self.profile["requiredFiles"]["vendor/hardware_overlay/overlay.mk"]
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "every reviewed build edit"):
            self.apply()
        self.assertEqual(before, self.snapshot())

    @unittest.skipUnless(shutil.which("make"), "GNU Make needed for package expansion")
    def test_effective_overlay_packages_preserved_without_qti(self):
        self.apply()
        makefile = ("include vendor/hardware_overlay/overlay.mk\nall:\n\t@echo $(PRODUCT_PACKAGES)\n")
        result = subprocess.run(["make", "-f", "-", "--no-print-directory"], cwd=self.root,
                                input=makefile, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip().split(),
                         ["HardwareOverlayPicker", "TrebleApp", "treble-overlay-mtk-ims", "OtherPackage"])

    def test_partial_security_patch_refused(self):
        self.write(MODULE.BASE, self.base_original.replace(b"ro.adb.secure=0", b"ro.adb.secure=1"))
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.apply()
        self.assertEqual(before, self.snapshot())

    def test_unknown_system_properties_refused_before_any_write(self):
        self.write(MODULE.SYSTEM_PROP, self.system_original + b"ro.product.model=unexpected\n")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.apply()
        self.assertEqual(before, self.snapshot())

    def test_interrupted_install_between_property_files_can_complete(self):
        patched = self.base_original.replace(b"ro.adb.secure=0", b"ro.adb.secure=1") \
            .replace(b"persist.sys.usb.config=adb", b"persist.sys.usb.config=mtp") \
            .replace(self.profile['securityEdits'][2]['before'].encode(),
                     self.profile['securityEdits'][2]['after'].encode())
        self.write(MODULE.BASE, patched)
        self.write(MODULE.BASE + ".ctz-original", self.base_original)
        self.apply()
        self.assertIn(b"ro.adb.secure=1\n", (self.root / MODULE.SYSTEM_PROP).read_bytes())
        self.assertEqual(self.apply(), [])

    def test_missing_second_property_validation_refused(self):
        del self.profile["requiredFiles"][MODULE.SYSTEM_PROP]
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'both ADB property inputs'):
            self.apply()
        self.assertEqual(before, self.snapshot())

    def test_missing_dependency_refused(self):
        (self.root / "vendor/vndk/vndk.mk").unlink()
        before = self.snapshot()
        with self.assertRaises(OSError):
            self.apply()
        self.assertEqual(before, self.snapshot())

    def test_modified_dependency_refused(self):
        self.write("vendor/vndk/vndk.mk", b"# different dependency\n")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.apply()
        self.assertEqual(before, self.snapshot())

    def test_existing_different_product_not_overwritten(self):
        self.write("device/phh/treble/suiram_ctz10.mk", b"# user content")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.apply()
        self.assertEqual(before, self.snapshot())

    def test_existing_backup_not_overwritten(self):
        self.write(MODULE.BASE + ".ctz-original", b"# earlier backup")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.apply()
        self.assertEqual(before, self.snapshot())

    def test_registry_changed_after_install_refused(self):
        self.apply()
        path = self.root / MODULE.REGISTRY
        path.write_bytes(path.read_bytes() + b"# subsequent user edit\n")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.apply()
        self.assertEqual(before, self.snapshot())

    def test_duplicate_registration_refused(self):
        self.write(MODULE.REGISTRY, MODULE.BLOCK.encode() * 2)
        with self.assertRaises(ValueError):
            self.apply()

    def test_new_registry_when_not_generated(self):
        (self.root / MODULE.REGISTRY).unlink()
        self.apply()
        self.assertEqual((self.root / MODULE.REGISTRY).read_text(), MODULE.BLOCK)
        self.assertEqual(self.apply(), [])

    def test_registry_without_final_newline_preserved(self):
        self.write(MODULE.REGISTRY, b"PRODUCT_MAKEFILES := user.mk")
        self.apply()
        self.assertEqual(self.apply(), [])
        self.assertEqual((self.root / (MODULE.REGISTRY + ".ctz-original")).read_bytes(), b"PRODUCT_MAKEFILES := user.mk")

    def test_changes_after_check_refused(self):
        root, observed, changes = self.plan()
        self.write(MODULE.REGISTRY, b"# concurrent edit\n")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            MODULE.apply_plan(root, observed, changes)
        self.assertEqual(before, self.snapshot())

    def test_symlink_output_refused(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (self.root / "vendor/suiram").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.apply()
        self.assertEqual(list(outside.iterdir()), [])

    @unittest.skipUnless(shutil.which("make"), "GNU Make needed for recipe expansion test")
    def test_recipe_locale_and_board_expansion_not_full_android_build(self):
        self.apply()
        self.write("device/phh/treble/base-pre.mk", b"# empty dependency fixture\n")
        # This small harness checks recipe expressions only, not AOSP inheritance or compilation.
        makefile = ("inherit-product = $(eval include $(1))\n"
                    "define get-default-product-locale\n"
                    "$(strip $(subst _,-, $(firstword $(1))))\n"
                    "endef\n"
                    "include device/phh/treble/suiram_ctz10.mk\n"
                    "all:\n"
                    "\t@echo locale=$(call get-default-product-locale,$(PRODUCT_LOCALES))\n"
                    "\t@echo locales=$(PRODUCT_LOCALES)\n"
                    "\t@echo board=$(PRODUCT_DEVICE)\n"
                    "\t@echo packages=$(PRODUCT_PACKAGES)\n"
                    "\t@echo properties=$(PRODUCT_SYSTEM_DEFAULT_PROPERTIES)\n")
        result = subprocess.run(["make", "-f", "-", "--no-print-directory"], cwd=self.root,
                                input=makefile, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("locale=ja-JP", result.stdout)
        self.assertIn("locales=ja_JP en_US", result.stdout)
        self.assertIn("board=phhgsi_arm64_ab", result.stdout)
        self.assertIn("properties=ro.adb.secure=1 persist.sys.usb.config=mtp", result.stdout)
        self.assertNotIn("phh-su", result.stdout)


if __name__ == "__main__":
    unittest.main()
