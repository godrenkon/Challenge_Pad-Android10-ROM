"""Canonical source recipe and local Git verification for the CTZ engineering GSI."""
import copy
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "manifest/ctz-android10.xml"
SHA = re.compile(r"^[0-9a-f]{40}$")
TAG = "refs/tags/android-10.0.0_r41"


def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def parse_xml(data):
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("DTD/entities are not allowed in source manifests")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        raise ValueError("Malformed source manifest") from error
    if root.tag != "manifest":
        raise ValueError("Expected a repo manifest")
    return root


def xml_bytes(root):
    tree = copy.deepcopy(root)
    ET.indent(tree, space="  ")
    return ET.tostring(tree, encoding="utf-8", xml_declaration=True) + b"\n"


def project_map(root):
    projects = {}
    names = set()
    if any(x.tag not in {"remote", "default", "project"} for x in root):
        raise ValueError("Only flat remote/default/project manifest elements are supported")
    for p in root.findall("project"):
        path = p.get("path")
        name = p.get("name")
        if not path or not name or "\\" in path:
            raise ValueError("Project path/name is missing or invalid")
        parts = path.split("/")
        if any(x in {"", ".", ".."} for x in parts) or PurePosixPath(path).is_absolute():
            raise ValueError("Unsafe project path: " + path)
        if path in projects or name in names:
            raise ValueError("Duplicate project path/name: " + path)
        if any(x.tag not in {"copyfile", "linkfile"} for x in p):
            raise ValueError("Unexpected project child: " + path)
        projects[path] = p
        names.add(name)
    if not projects:
        raise ValueError("Empty source manifest")
    return projects


def render_recipe():
    provenance = json.loads((ROOT / "config/source-provenance.json").read_text(encoding="utf-8"))
    raw = (ROOT / "manifest/upstream/aosp-default.xml").read_bytes()
    if blob_sha(raw) != provenance["aosp"]["defaultXmlBlob"]:
        raise ValueError("AOSP manifest input differs from reviewed blob")
    base = parse_xml(raw)
    original = {p.get("path"): p for p in base.findall("project")}
    replacement_raw = (ROOT / "manifest/upstream/phh-replace.xml").read_bytes()
    if blob_sha(replacement_raw) != provenance["phh"]["replaceXmlBlob"]:
        raise ValueError("PHH replacement input differs from reviewed blob")
    replace = parse_xml(replacement_raw)
    replacements = {p.get("path"): p for p in replace.findall("project")}
    removals = {p.get("name") for p in replace.findall("remove-project")}
    if {original[path].get("name") for path in replacements} != removals:
        raise ValueError("PHH replacements do not match AOSP project removals")
    result = ET.Element("manifest")
    ET.SubElement(result, "remote", name="aosp", fetch=provenance["aosp"]["fetch"])
    ET.SubElement(result, "remote", name="phh", fetch="https://github.com/phhusson/")
    ET.SubElement(result, "remote", name="relan", fetch="https://github.com/relan/")
    ET.SubElement(result, "default", revision=TAG, remote="aosp", **{"sync-j": "4"})
    pins = {p["path"]: p for p in provenance["phh"]["projects"]}
    if len(pins) != len(provenance["phh"]["projects"]) or not set(replacements).issubset(pins):
        raise ValueError("Incomplete or duplicate PHH pins")
    for path, p in original.items():
        item = copy.deepcopy(replacements.get(path, p))
        if path in pins:
            pin = pins[path]
            if not SHA.fullmatch(pin["sha"]) or pin["repo"] != "phhusson/" + item.get("name"):
                raise ValueError("Replacement pin mismatch: " + path)
            item.set("revision", pin["sha"])
        result.append(item)
    for path, pin in pins.items():
        if path in original:
            continue
        owner, name = pin["repo"].split("/", 1)
        if owner not in {"phhusson", "relan"} or not SHA.fullmatch(pin["sha"]):
            raise ValueError("Unsupported addition: " + path)
        ET.SubElement(result, "project", path=path, name=name,
                      remote="phh" if owner == "phhusson" else "relan", revision=pin["sha"])
    project_map(result)
    return xml_bytes(result)


def checked_recipe():
    expected = render_recipe()
    if RECIPE.read_bytes() != expected:
        raise ValueError("Committed source recipe is stale or modified; review the diff")
    return parse_xml(expected)


def project_path(root, relative):
    path = root
    for part in relative.split("/"):
        path /= part
        if path.is_symlink():
            raise ValueError("Refusing source project symlink: " + relative)
    if not path.is_dir() or not path.resolve().is_relative_to(root):
        raise ValueError("Missing source project: " + relative)
    return path


def git(path, *args):
    try:
        result = subprocess.run(["git", "-c", "core.fsmonitor=false", "-C", str(path), *args],
                                capture_output=True, timeout=30, check=False)
    except subprocess.TimeoutExpired as error:
        raise ValueError("Git inspection timed out: " + str(path)) from error
    if result.returncode:
        raise ValueError("Git inspection failed in " + str(path) + ": " + result.stderr.decode("utf-8", "replace").strip())
    return result.stdout


def status_paths(data):
    paths = set()
    for item in data.split(b"\0"):
        if not item:
            continue
        if len(item) < 4 or item[2:3] != b" " or b"R" in item[:2] or b"C" in item[:2]:
            raise ValueError("Unsupported Git change/rename in source tree")
        paths.add(item[3:].decode("utf-8", "strict"))
    return paths


def assert_clear_index(path):
    # These flags hide modified files from Git status/diff without changing the files.
    for entry in git(path, "ls-files", "-v", "-z").split(b"\0"):
        if entry and (entry[:1] == b"S" or entry[:1].islower()):
            raise ValueError("Hidden-change index flag in source project: " + str(path))


def inspect_sources(root, recipe=None, expected_heads=None, allowed_changes=None):
    root = Path(root).resolve(strict=True)
    if not root.is_dir() or root == Path(root.anchor):
        raise ValueError("Use a dedicated Android source directory")
    recipe = checked_recipe() if recipe is None else recipe
    remotes = {r.get("name"): r.get("fetch") for r in recipe.findall("remote")}
    default = recipe.find("default")
    if default is None:
        raise ValueError("Manifest default is missing")
    heads = {}
    for relative, p in project_map(recipe).items():
        path = project_path(root, relative)
        top = git(path, "rev-parse", "--show-toplevel").decode().strip()
        if Path(top).resolve() != path.resolve():
            raise ValueError("Project is not its own Git checkout: " + relative)
        remote = p.get("remote") or default.get("remote")
        if remote not in remotes:
            raise ValueError("Unknown source remote: " + relative)
        remote_url = git(path, "config", "--get", "remote." + remote + ".url").decode().strip()
        expected_url = remotes[remote].rstrip("/") + "/" + p.get("name")
        if remote_url.rstrip("/").removesuffix(".git") != expected_url:
            raise ValueError("Source remote differs from recipe: " + relative)
        head = git(path, "rev-parse", "--verify", "HEAD").decode().strip()
        if not SHA.fullmatch(head):
            raise ValueError("Invalid Git HEAD: " + relative)
        revision = p.get("revision") or default.get("revision", "")
        if SHA.fullmatch(revision):
            expected = revision
        elif revision == TAG:
            expected = git(path, "rev-parse", "--verify", TAG + "^{commit}").decode().strip()
        else:
            raise ValueError("Unpinned source revision: " + relative)
        if head != expected or (expected_heads is not None and head != expected_heads[relative]):
            raise ValueError("Source commit differs from recipe/lock: " + relative)
        assert_clear_index(path)
        # Include ignored files: an ignored Android.mk/Android.bp can still affect the build.
        status = git(path, "status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching", "-z")
        if status_paths(status) - (allowed_changes or {}).get(relative, set()):
            raise ValueError("Unrecorded source changes/ignored files: " + relative)
        heads[relative] = head
    return heads


def locked_bytes(recipe, heads):
    result = copy.deepcopy(recipe)
    for path, p in project_map(result).items():
        if not SHA.fullmatch(heads[path]):
            raise ValueError("Invalid locked commit")
        p.set("revision", heads[path])
    return xml_bytes(result)


def read_lock(path, recipe=None):
    recipe = checked_recipe() if recipe is None else recipe
    locked = parse_xml(Path(path).read_bytes())
    expected = project_map(recipe)
    actual = project_map(locked)
    if set(expected) != set(actual):
        raise ValueError("Locked project set differs from recipe")
    # Only project revision may change. Remotes, copies, links and groups must match.
    canonical = copy.deepcopy(locked)
    heads = {}
    for relative, p in project_map(canonical).items():
        heads[relative] = p.get("revision", "")
        if not SHA.fullmatch(heads[relative]):
            raise ValueError("Lock contains a branch/tag rather than a commit")
        original_revision = expected[relative].get("revision")
        if original_revision is None:
            p.attrib.pop("revision", None)
        else:
            if SHA.fullmatch(original_revision) and heads[relative] != original_revision:
                raise ValueError("Lock changed a PHH pin: " + relative)
            p.set("revision", original_revision)
    if xml_bytes(canonical) != xml_bytes(recipe):
        raise ValueError("Lock changed source metadata outside project revisions")
    return heads
