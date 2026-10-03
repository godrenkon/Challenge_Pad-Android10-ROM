# Future source-build skeleton only. BoardConfig.mk intentionally blocks it.
$(call inherit-product, device/benesse/ctz/device.mk)

PRODUCT_NAME := lineage_ctz
PRODUCT_DEVICE := ctz
PRODUCT_BRAND := Suiram
PRODUCT_MODEL := TAB-A05-BA1
PRODUCT_MANUFACTURER := Panasonic
PRODUCT_CHARACTERISTICS := tablet

# Japanese is primary; English remains available as a secondary locale.
PRODUCT_LOCALES := ja_JP en_US
# This file does not alter an already-built upstream GSI's default language.
# No invented Google client ID or bundled GMS.
