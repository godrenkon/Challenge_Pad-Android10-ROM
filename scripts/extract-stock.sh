#!/usr/bin/env bash
set -euo pipefail

# Extract files locally from a mounted stock vendor/system tree.
# Usage:
#   ./scripts/extract-stock.sh /path/to/stock-root

SRC_ROOT="${1:-}"
OUT_DIR="vendor/benesse/ctz/proprietary"

if [[ -z "${SRC_ROOT}" || ! -d "${SRC_ROOT}" ]]; then
  echo "Usage: $0 /path/to/stock-root" >&2
  exit 2
fi

fingerprint_file="${SRC_ROOT}/vendor/build.prop"
if [[ ! -f "${fingerprint_file}" ]]; then
  fingerprint_file="${SRC_ROOT}/system/build.prop"
fi

if [[ ! -f "${fingerprint_file}" ]]; then
  echo "No build.prop found under ${SRC_ROOT}" >&2
  exit 3
fi

if ! grep -Eq 'TAB-A05-BA1|01\.03\.000' "${fingerprint_file}"; then
  echo "Refusing: source does not identify TAB-A05-BA1 build 01.03.000" >&2
  exit 4
fi

mkdir -p "${OUT_DIR}"
manifest="vendor/benesse/ctz/proprietary-files.txt"
if [[ ! -s "${manifest}" ]]; then
  echo "Manifest is empty; nothing to extract yet."
  exit 0
fi

while IFS= read -r entry; do
  [[ -z "${entry}" || "${entry}" == \#* ]] && continue
  src="${SRC_ROOT}/${entry%%:*}"
  dst="${OUT_DIR}/${entry##*:}"
  if [[ ! -f "${src}" ]]; then
    echo "Missing: ${src}" >&2
    exit 5
  fi
  mkdir -p "$(dirname "${dst}")"
  cp -a "${src}" "${dst}"
done < "${manifest}"

echo "Extracted local vendor files into ${OUT_DIR}"
