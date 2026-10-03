# Partition map worksheet

This file is intentionally a worksheet. Values must be copied from an exact
TAB-A05-BA1 01.03.000 capture, not guessed from TAB-A05-BD or another MT8168
tablet.

| Name | Start | Size | Source / notes |
| --- | ---: | ---: | --- |
| preloader | unknown | unknown | stock only; do not redistribute |
| lk | unknown | unknown | bootloader component |
| boot | unknown | unknown | kernel + ramdisk |
| recovery | unknown | unknown | recovery image |
| vendor | unknown | unknown | vendor HALs and firmware |
| system | unknown | unknown | Android framework |
| dtbo | unknown | unknown | device tree overlays |
| userdata | unknown | unknown | user data |
| cache | unknown | unknown | may be absent |

When values are known, add the capture date, build fingerprint and SHA-256 of
the source image. Never publish a flash command using unknown values.
