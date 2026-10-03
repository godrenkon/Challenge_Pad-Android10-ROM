# Challenge Pad NEXT Android 10 ROM

A public bring-up project to port Android 10 to the Panasonic/Benesse **Challenge Pad NEXT (TAB-A05-BA1 / CTZ)** and make it usable as a normal Android tablet.

[日本語 README](README.ja.md)

> **Status: research and bring-up. This is not a flashable finished ROM yet.**

## Goals

- Android 10 based on AOSP / LineageOS 17.1
- Working display, touch, storage, Wi-Fi, audio, sensors and power management
- Japanese / English language selection
- GMS handled as a separate, properly licensed package
- Reproducible builds and public documentation
- Safe release process with recovery instructions

## Target

| Item | Value |
| --- | --- |
| Device | Challenge Pad NEXT |
| Model | TAB-A05-BA1 |
| Internal target | CTZ |
| SoC | MediaTek MT8168A |
| GPU | Mali-G52 MC1 |
| Stock OS | Android 9 |
| Stock build | 01.03.000 |
| CPU ABI | arm64 |
| Display | 1200 x 1920 |

## Current state

The public Next projects found during the initial search are Android 9-based projects such as PixelTouch. No verified public Android 10 image for TAB-A05-BA1 was found. This repository keeps source code and extraction steps separate and does not redistribute stock files.

## Important

- USB is not required just to work on or read the source tree.
- USB data access is required to capture stock partitions, unlock the bootloader, flash images and test the device.
- Bootloader unlocking normally wipes user data.
- Never flash an image for TAB-A05-BD, TAB-A03 or another build onto TAB-A05-BA1.
- GMS and stock vendor binaries are not included in this public source tree.

See [bring-up plan](docs/bring-up.md), [build instructions](docs/build.md), and [partition worksheet](docs/partition-map.md).
