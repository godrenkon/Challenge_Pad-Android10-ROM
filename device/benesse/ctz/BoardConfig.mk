DEVICE_PATH := device/benesse/ctz

# Target identity
TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-a
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_ABI2 := armeabi-v7a
TARGET_CPU_VARIANT := generic
TARGET_2ND_ARCH := arm
TARGET_2ND_ARCH_VARIANT := armv7-a
TARGET_2ND_CPU_ABI := armeabi-v7a
TARGET_2ND_CPU_ABI2 := armeabi
TARGET_2ND_CPU_VARIANT := generic

# MediaTek MT8168 family
BOARD_MEDIATEK_PLATFORM := mt8168
TARGET_BOARD_PLATFORM := mt8168
TARGET_NO_BOOTLOADER := true
TARGET_BOOTLOADER_BOARD_NAME := ctz

# Android 10 / system-as-root. These values are placeholders until the
# exact stock partition table is captured from a TAB-A05-BA1 01.03.000 unit.
BOARD_BUILD_SYSTEM_ROOT_IMAGE := true
BOARD_FLASH_BLOCK_SIZE := 131072

# Kernel and boot image. Fill in after the stock boot image is extracted.
BOARD_KERNEL_IMAGE_NAME := Image.gz
BOARD_KERNEL_CMDLINE := console=tty0
BOARD_KERNEL_PAGESIZE := 2048
BOARD_KERNEL_BASE := 0x40078000
BOARD_RAMDISK_OFFSET := 0x07c08000
BOARD_TAGS_OFFSET := 0x0e000000
BOARD_MKBOOTIMG_ARGS += --header_version 1

# Recovery will be brought up before a full system image.
TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/rootdir/etc/fstab.ctz

# Partitions must be replaced with measured values; never flash while these
# are still placeholders.
# BOARD_BOOTIMAGE_PARTITION_SIZE := 0x00000000
# BOARD_RECOVERYIMAGE_PARTITION_SIZE := 0x00000000
# BOARD_SYSTEMIMAGE_PARTITION_SIZE := 0x00000000
# BOARD_VENDORIMAGE_PARTITION_SIZE := 0x00000000

# Treble / vendor split
PRODUCT_USE_DYNAMIC_PARTITIONS := false
BOARD_VNDK_VERSION := current
