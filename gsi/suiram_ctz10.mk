# Engineering GSI product, derived from the reviewed PHH arm64/AB/vanilla/N recipe.
# AB is the generic SAR build layout, NOT a declaration about CTZ slot names.
TARGET_GAPPS_ARCH := arm64
$(call inherit-product, device/phh/treble/base-pre.mk)
include build/make/target/product/aosp_arm64_ab.mk
$(call inherit-product, vendor/vndk/vndk.mk)
$(call inherit-product, device/phh/treble/base.mk)
$(call inherit-product, vendor/suiram/ctz/ctz_locale.mk)

PRODUCT_NAME := suiram_ctz10
# Keep the generic board identity so the PHH arm64/SAR BoardConfig is selected.
PRODUCT_DEVICE := phhgsi_arm64_ab
PRODUCT_BRAND := Suiram
PRODUCT_MODEL := TAB-A05-BA1
PRODUCT_MANUFACTURER := Panasonic
PRODUCT_CHARACTERISTICS := tablet

# Deliberately do not add phh-su, me.phh.superuser or GApps.
# userdebug still has development capabilities; this is NOT a certified release.
# No stock fingerprint spoof, kernel replacement, partition sizing or HAL override.
