#!/usr/bin/env python3
"""Inspect every source checkout; --output explicitly saves a full commit manifest."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from source_manifest import checked_recipe, inspect_sources, locked_bytes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        root = args.source_root.resolve(strict=True)
        if args.output and args.output.resolve().is_relative_to(root):
            raise ValueError("Keep the source lock outside the source tree")
        if args.output and (args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir()):
            raise ValueError("Use a new manifest filename in an existing directory")
        recipe = checked_recipe()
        heads = inspect_sources(root, recipe)
        data = locked_bytes(recipe, heads)
        if args.output:
            with args.output.open("xb") as stream:
                stream.write(data)
        print(json.dumps({"mode": "locked" if args.output else "check-only", "projects": len(heads),
                          "manifestSHA256": hashlib.sha256(data).hexdigest(),
                          "flashReady": False, "fullAndroidBuildTested": False}, indent=2))
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
