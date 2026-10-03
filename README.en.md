# Challenge Pad NEXT Android 10 ROM

[日本語（標準）](README.md)

A public Android 10 bring-up project for **TAB-A05-BA1 / CTZ**, stock build **01.03.000**.
Japanese is the primary project language and intended final default; English is secondary.

> **Preparation tools implemented. Real-device boot is untested. No finished flashable ROM exists here yet.**

The initial route retains stock boot/kernel/vendor and evaluates an Android 10 GSI.
Public stock properties report arm64, Treble, system-as-root and VNDK 28.
The selected PHH v222 arm64-ab vanilla image is an existing upstream test base,
not an original CTZ ROM or verified bootable release. PHH's AB label does not establish physical slot layout.

## Tools

- `download-base.cmd`: fetches the upstream base to the PC, never flashes or copies to SD.
- `inspect-device.cmd`: reads authorized ADB properties, compares the exact stock profile,
  and writes a minimal JSON report without serial/MAC identifiers.
- `scripts/inspect-system-image.py`: checks raw ext4 / Android sparse geometry and optional
  measured partition fit. This does not validate filesystems, CRC, OS version, AVB or boot compatibility.

PowerShell tools default to Japanese messages; use `-Language en` for English.
PS1 source is ASCII-only; localized UTF-8 JSON is read explicitly for Windows PowerShell 5.1 compatibility.
CMD launchers pause on exit. Reports and downloads are never overwritten.

The downloader defaults to vanilla; `-Variant gapps` explicitly selects another upstream asset.
No trusted upstream SHA256 is pinned yet. Download length and XZ magic are checked;
the computed hash is a receipt, not an authenticity guarantee. No extraction happens automatically.

Tests cover offline tooling behavior, not actual upstream downloads, hardware operation or ROM boot.
Stock backup/restore, partition geometry, AVB policy, panel variation and real-device logs remain required.
`flashReady` is always false. A 1GB SD card is not assumed large enough for an expanded image.

The source-build skeleton is explicitly disabled until hardware facts are verified.
The optional manifest checks out project notes/tools at `vendor/suiram/ctz-rom`, not as a working device tree.
GMS/vendor binaries are not redistributed. Play operation and certification are not guaranteed.
Android 10 is old and does not provide current security updates.

See the Japanese-first [preparation guide](docs/preparation.ja.md),
[architecture](docs/architecture.ja.md), [device facts](docs/device-facts.md),
and [bring-up checklist](docs/bring-up.md).
