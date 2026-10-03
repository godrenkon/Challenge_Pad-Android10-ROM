# Challenge Pad NEXT Android 10 ROM

[日本語 / Japanese](README.ja.md) · [English](README.en.md)

A community open-source bring-up project for the Panasonic/Benesse Challenge Pad NEXT (TAB-A05-BA1 / CTZ), build 01.03.000.

> **Status: research / bring-up. Not a flashable ROM yet.**
>
> This repository intentionally does not ship proprietary firmware, Google Mobile Services, or extracted vendor binaries. A bootable image must not be claimed until it has been tested on the exact hardware.

## Goal

Build a clean Android 10-based system for the TAB-A05-BA1 that behaves like a normal Android tablet:

- Android 10 (AOSP / LineageOS 17.1 base)
- working display, touch, storage, Wi-Fi, audio, sensors and power management
- Japanese / English language selection
- optional separately licensed GMS package
- reproducible build and public documentation
- recovery and rollback instructions before any public release

## Hardware target

| Item | Value |
| --- | --- |
| Device | Challenge Pad NEXT |
| Model | TAB-A05-BA1 |
| Internal target | CTZ |
| SoC | MediaTek MT8168A |
| GPU | Mali-G52 MC1 |
| Stock OS | Android 9 |
| Stock build | 01.03.000 |
| Architecture | arm64 |
| Display | 1200 x 1920 |

## Current state

The public projects we found for this device are Android 9 based (including PixelTouch), GMS/system modification tools, bootloader tooling, and reverse-engineered libraries. No public, verified Android 10 image for TAB-A05-BA1 was found during the initial search. This project starts from source and keeps the proprietary extraction step separate.

## Roadmap

1. Freeze the exact stock build and partition layout.
2. Collect legally usable source and device-specific information.
3. Add the Android 10 device tree and product definition.
4. Add a matching MT8168 kernel tree and board configuration.
5. Extract vendor blobs from the user's own stock image.
6. Bring up recovery, then boot image, then system/vendor.
7. Validate hardware one subsystem at a time.
8. Build signed test packages and publish only after real-device testing.

## Important limitations

- Building the source tree does not require a USB cable.
- Extracting partitions, unlocking the bootloader, flashing and validating the tablet do require a USB data connection and a working recovery path.
- Bootloader unlocking normally wipes user data.
- Never flash an image for TAB-A05-BD, TAB-A03, or another build onto TAB-A05-BA1.
- GMS is not included in this source tree; Google packages have separate licensing and compatibility requirements.

See [docs/bring-up.md](docs/bring-up.md), [docs/build.md](docs/build.md), [docs/partition-map.md](docs/partition-map.md), and [docs/proprietary-files.md](docs/proprietary-files.md).

## License

The original source in this repository is Apache-2.0 unless a file says otherwise. Device-specific proprietary files remain the property of their respective copyright holders and must not be redistributed from this repository.
