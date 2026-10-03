# Challenge Pad NEXT Android 10 ROM

[日本語（標準）](README.md)

A public Android 10 bring-up project for **TAB-A05-BA1 / CTZ**, stock build **01.03.000**.
Japanese is the primary project language and intended final default; English is secondary.

> **Preparation tools and a Japanese-first GSI source recipe are implemented. Full compilation and real-device boot are untested. No finished flashable ROM exists here yet.**

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
- `scripts/prepare-gsi-source.py`: check-only by default; explicit `--apply` installs the
  `suiram_ctz10-userdebug` product into a separate matching Android source tree.

The new recipe selects Japanese first and English second, keeps the generic PHH board,
and adds neither GApps nor the PHH superuser applications. It patches the shared PHH base to
request authenticated ADB and MTP as the default USB configuration, affecting other PHH products
in that tree too. Use a dedicated source tree. Userdebug remains an engineering build.
The tool checks nine pinned input blobs, retains backups, refuses conflicts, and is idempotent.
It does not patch the downloaded GSI, sync the whole source tree, build Android or operate the tablet.
The component snapshot is not a complete release manifest or proof of v222 binary reproducibility.
Japanese input-method integration and real-device locale behavior remain unverified.
See the Japanese-first [source recipe guide](docs/source-product.ja.md).

The [integrated manifest](manifest/ctz-android10.xml) contains 762 projects: AOSP is pinned to
`android-10.0.0_r41`, while 27 PHH/additional components use fixed commits.
`lock-source.py` inspects local Git checkouts and writes a full commit manifest before patching.
`build-ctz.py` checks that lock and the approved patch, then builds only with explicit `--run`.
It uses a new output directory and records logs, failures, image geometry and SHA256.
Full sync and real Android compilation have not been performed; the current host has only about
28GB free. The wrapper's conservative policy requires 150GiB free for output and 8GiB effective memory,
separate from source storage; these are project checks, not official minimum requirements.
See the Japanese-first [source build guide](docs/source-build.ja.md). Offline wrapper tests use fake
build commands and do not demonstrate Android compilation or device compatibility.

PowerShell tools default to Japanese messages; use `-Language en` for English.
PS1 source is ASCII-only; localized UTF-8 JSON is read explicitly for Windows PowerShell 5.1 compatibility.
CMD launchers pause on exit. Reports and downloads are never overwritten.

The downloader defaults to vanilla; `-Variant gapps` explicitly selects another upstream asset.
No trusted upstream SHA256 is pinned yet. Download length and XZ magic are checked;
the computed hash is a receipt, not an authenticity guarantee. No extraction happens automatically.

Tests cover offline tooling behavior, not actual upstream downloads, hardware operation or ROM boot.
Stock backup/restore, partition geometry, AVB policy, panel variation and real-device logs remain required.
`flashReady` is always false. A 1GB SD card is not assumed large enough for an expanded image.

The device-specific `device/benesse/ctz` skeleton is explicitly disabled until hardware facts are verified;
the separate generic GSI source recipe is experimental and has not been compiled.
The optional manifest checks out project notes/tools at `vendor/suiram/ctz-rom`, not as a working device tree.
GMS/vendor binaries are not redistributed. Play operation and certification are not guaranteed.
Android 10 is old and does not provide current security updates.

See the Japanese-first [preparation guide](docs/preparation.ja.md),
[architecture](docs/architecture.ja.md), [device facts](docs/device-facts.md),
and [bring-up checklist](docs/bring-up.md).
