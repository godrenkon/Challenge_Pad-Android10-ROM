# Android 10 bring-up plan

## Phase 0 — source and identity

Target is TAB-A05-BA1 / CTZ / stock build 01.03.000. Confirm the value in
Settings and record the complete build fingerprint before extraction.

The public research found Android 9-based system modifications and PixelTouch,
but no verified public Android 10 image for this exact target. This repository
therefore treats every binary as untrusted until it is matched to the target.

## Phase 1 — stock capture

Required artifacts, kept outside this repository:

- boot.img
- recovery.img
- vendor.img
- system.img or system-as-root contents
- dtbo.img
- lk.img and preloader metadata where legally available
- partition table and fstab
- getprop output and kernel config

The exact USB data path and bootloader state determine which capture method is
safe. Do not use a generic MTK scatter file or a CTX image.

## Phase 2 — recovery

Build a recovery-only image first. Validate:

- display orientation and 1200x1920 panel modes
- touch coordinates and multitouch
- internal storage and SD card
- reboot, shutdown and charger mode
- recovery logs survive reboot

A recovery that cannot mount the stock data partition is not ready for system
testing.

## Phase 3 — Android 10 system

Start with the smallest AOSP/LineageOS 17.1 system. Keep vendor HALs isolated,
then enable display, graphics, audio, Wi-Fi, Bluetooth, camera, sensors and
power one at a time. Capture logcat, dmesg and tombstones for every failure.

## Phase 4 — validation

A release candidate must pass:

- ten cold boots and ten warm reboots;
- touch across the full panel;
- Wi-Fi reconnect after suspend;
- Bluetooth pair/unpair;
- audio output and microphone recording;
- camera preview and still capture;
- charging while powered off;
- sleep/wake and battery drain observation;
- factory reset and rollback to stock.

## Release rule

Until the matrix passes on at least one exact TAB-A05-BA1, publish only as
UNTESTED source or engineering builds. Do not call it a complete ROM.
