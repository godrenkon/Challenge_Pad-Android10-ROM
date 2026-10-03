#!/usr/bin/env python3
"""Extract an explicit local manifest from exact stock; never access a device."""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def stock_properties(source):
    for name in ("system/build.prop", "system/system/build.prop", "build.prop"):
        candidate = (source / name).resolve()
        if not candidate.is_relative_to(source):
            raise ValueError("build.prop escapes source root")
        if not candidate.is_file():
            continue
        result = {}
        for line in candidate.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if not separator:
                raise ValueError("Malformed build.prop")
            if key in result and result[key] != value:
                raise ValueError("Conflicting build.prop property: " + key)
            result[key] = value
        return result
    raise ValueError("No system build.prop found (including SAR system/system)")


def relative_path(text):
    if not text or "\\" in text or ":" in text or "\x00" in text:
        raise ValueError("Manifest paths must be nonempty relative POSIX paths")
    path = PurePosixPath(text)
    if path.is_absolute() or any(part in (".", "..", "") for part in text.split("/")):
        raise ValueError("Unsafe manifest path: " + text)
    if not re.fullmatch(r"[A-Za-z0-9_./+@-]+", text):
        raise ValueError("Unsupported characters in manifest path")
    return Path(*path.parts)


def extract(source, manifest, output):
    source = Path(source).resolve(strict=True)
    output = Path(output).resolve()
    if not source.is_dir():
        raise ValueError("Source must be a mounted/extracted stock directory")
    # Never place extraction output inside stock or stock inside output.
    if output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("Stock source and output must not overlap")
    profile = json.loads((ROOT / "config/ctz-stock.json").read_text(encoding="utf-8"))
    props = stock_properties(source)
    for key in ("ro.product.model", "ro.build.id", "ro.build.version.release", "ro.build.fingerprint"):
        if props.get(key) != profile["required"][key]:
            raise ValueError("Refusing nonmatching stock: " + key)
    planned = []
    destinations = set()
    for line in Path(manifest).read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(":")
        if len(parts) > 2:
            raise ValueError("Manifest supports source or source:destination only")
        src = (source / relative_path(parts[0])).resolve(strict=True)
        destination_path = output / relative_path(parts[-1])
        if destination_path.exists() or destination_path.is_symlink():
            raise ValueError("Refusing existing destination: " + str(destination_path))
        dst = destination_path.resolve()
        if not src.is_relative_to(source) or not dst.is_relative_to(output):
            raise ValueError("Manifest or symlink escapes its root")
        if not src.is_file():
            raise ValueError("Source is not a regular file: " + str(src))
        if dst.exists() or dst.is_symlink() or dst in destinations:
            raise ValueError("Refusing existing or duplicate destination: " + str(dst))
        destinations.add(dst)
        planned.append((src, dst))
    # Preflight the entire manifest before creating any extraction output.
    for src, dst in planned:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.parent.resolve().is_relative_to(output):
            raise ValueError("Output parent changed outside root")
        with src.open("rb") as reader, dst.open("xb") as writer:
            shutil.copyfileobj(reader, writer)
    return len(planned)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stock_root", type=Path)
    parser.add_argument("--manifest", type=Path, default=ROOT / "vendor/benesse/ctz/proprietary-files.txt")
    parser.add_argument("--output", type=Path, default=ROOT / "vendor/benesse/ctz/proprietary")
    args = parser.parse_args(argv)
    try:
        count = extract(args.stock_root, args.manifest, args.output)
        print(f"Extracted {count} explicitly listed local files. No device accessed.")
        return 0
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
