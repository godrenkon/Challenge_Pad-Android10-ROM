LOCAL_PATH := $(call my-dir)

# Keep the product minimal until each hardware HAL is confirmed to exist on
# the chosen Android 10 base and the exact TAB-A05-BA1 vendor image.
PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/rootdir/etc/fstab.ctz:$(TARGET_COPY_OUT_VENDOR)/etc/fstab.ctz

PRODUCT_PROPERTY_OVERRIDES += \
    ro.product.device=ctz \
    ro.product.model=TAB-A05-BA1 \
    ro.product.manufacturer=Panasonic \
    ro.hardware=mt8168
