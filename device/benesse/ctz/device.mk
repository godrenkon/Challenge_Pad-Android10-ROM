LOCAL_PATH := $(call my-dir)

# Disabled source-build skeleton. The first bring-up uses stock boot/vendor
# with a separately obtained Android 10 GSI, NOT a generated vendor image.
# Never overwrite stock fstab or ro.hardware from an inferred platform name.
# Product identity is declared in lineage_ctz.mk, not duplicate properties.
