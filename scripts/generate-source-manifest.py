#!/usr/bin/env python3
"""Check the committed source manifest; --write explicitly regenerates it."""
import argparse
import sys
from source_manifest import RECIPE, checked_recipe, project_map, render_recipe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        if args.write:
            if RECIPE.is_symlink():
                raise ValueError("Refusing recipe symlink")
            RECIPE.write_bytes(render_recipe())
        recipe = checked_recipe()
        print("Source recipe verified: " + str(len(project_map(recipe))) + " projects; Android build untested.")
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
