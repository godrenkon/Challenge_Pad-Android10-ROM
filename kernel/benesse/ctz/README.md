# CTZ kernel

The target uses the MediaTek MT8168 family and a Linux 4.14-era stock kernel.
The exact Panasonic/Benesse source revision is not yet present in this
repository.

A compatible kernel cannot be inferred safely from a different tablet. The
bring-up process must capture the stock boot image, identify the kernel
config and DTB, then either:

- build the corresponding published source revision; or
- maintain a cleanly documented downstream patch set against the closest
legally usable MT8168 4.14 source.

Do not publish a boot image until the kernel, DTB and ramdisk have been tested
on the exact TAB-A05-BA1 hardware.
