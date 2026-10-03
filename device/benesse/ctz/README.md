# CTZ device tree

This directory is the Android 10 device tree for Challenge Pad NEXT
(TAB-A05-BA1 / CTZ).

## What is known

- SoC: MediaTek MT8168A
- Stock Android: 9
- Stock build: 01.03.000
- Target architecture: arm64
- Bootloader target: ctz

## What is not known yet

The exact partition sizes, boot image header details, kernel source revision,
device-tree blob, panel/touch configuration, Wi-Fi firmware and vendor HAL
compatibility must be measured from a stock unit. Files containing guessed
values are marked as placeholders and must not be flashed.

## Bring-up order

1. Boot an unpacked/repacked recovery.
2. Confirm display and touch.
3. Mount stock vendor and verify linker/HAL compatibility.
4. Boot a minimal Android 10 system.
5. Add hardware HALs one at a time.
6. Run the validation matrix in docs/bring-up.md.
