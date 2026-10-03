# Incomplete source-build notes, NOT a boot/recovery recipe.
# Refuse builds until stock geometry, kernel and rollback have been verified.
$(error CTZ source build is disabled: stock boot header, partition geometry and kernel/vendor integration are unverified. See docs/build.md)

DEVICE_PATH := device/benesse/ctz
TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-a
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_VARIANT := generic
TARGET_2ND_ARCH := arm
TARGET_2ND_ARCH_VARIANT := armv7-a
TARGET_2ND_CPU_ABI := armeabi-v7a
TARGET_2ND_CPU_ABI2 := armeabi
TARGET_2ND_CPU_VARIANT := generic
TARGET_BOARD_PLATFORM := mt8168
BOARD_MEDIATEK_PLATFORM := mt8168

# Public stock properties establish SAR and VNDK 28. A future source build
# must preserve compatibility with that vendor, not rebuild it as "current".
BOARD_BUILD_SYSTEM_ROOT_IMAGE := true
# Do not set kernel addresses, offsets, page size, command line, boot header
# version, partition sizes, dynamic partitions or A/B status by guesswork.
# Do not copy the placeholder fstab into an image.
