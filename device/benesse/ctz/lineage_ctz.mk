$(call inherit-product, device/benesse/ctz/device.mk)
$(call inherit-product, vendor/benesse/ctz/ctz-vendor.mk)

PRODUCT_NAME := lineage_ctz
PRODUCT_DEVICE := ctz
PRODUCT_BRAND := Benesse
PRODUCT_MODEL := TAB-A05-BA1
PRODUCT_MANUFACTURER := Panasonic

# Keep both locales in the product's initial locale list.
PRODUCT_LOCALES := ja_JP en_US

PRODUCT_GMS_CLIENTID_BASE := android-benesse
