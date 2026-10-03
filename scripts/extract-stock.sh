#!/usr/bin/env bash
set -euo pipefail
# Local-only extraction wrapper. Requires Python 3.9+; no ADB/root/device IO.
ctz_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${ctz_script_dir}/extract-stock.py" "$@"
