LOCAL_PATH := $(call my-dir)

# Device-specific packages will be added only after they are rebuilt or
# verified against Android 10. Do not copy Android 9 system APKs blindly.
PRODUCT_PACKAGES += \
    android.hardware.audio@2.0-impl \
    android.hardware.audio@2.0-service \
    android.hardware.bluetooth@1.0-service \
    android.hardware.camera.provider@2.4-service \
    android.hardware.configstore@1.1-service \
    android.hardware.drm@1.0-service \
    android.hardware.graphics.allocator@2.0-service \
    android.hardware.graphics.composer@2.1-service \
    android.hardware.health@2.0-service \
    android.hardware.power@1.0-service \
    android.hardware.sensors@1.0-service \
    android.hardware.wifi@1.0-service

PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/rootdir/etc/fstab.ctz:$(TARGET_COPY_OUT_VENDOR)/etc/fstab.ctz

PRODUCT_PROPERTY_OVERRIDES += \
    ro.product.device=ctz \
    ro.product.model=TAB-A05-BA1 \
    ro.product.manufacturer=Panasonic \
    ro.hardware=mt8168
