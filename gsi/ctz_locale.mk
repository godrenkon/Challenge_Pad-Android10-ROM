# Japanese-first product configuration for the reviewed Android 10 source.
# AOSP converts the first PRODUCT_LOCALES item ja_JP into ro.product.locale=ja-JP.
# English remains the secondary locale. Do not force persisted user settings.
PRODUCT_LOCALES := ja_JP en_US
# No GMS, unverified IME module, timezone override or hardware property here.
