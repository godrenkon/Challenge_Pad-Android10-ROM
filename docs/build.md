# Build environment

This project is source-only until the target-specific kernel, vendor files and
partition values are verified.

## Host

A Linux x86_64 machine with at least 16 GB RAM, 200 GB free storage and a
stable network is recommended. The Windows PC can prepare files and run ADB,
but a full Android 10 build is normally done in Linux or a Linux VM.

## Sync a LineageOS 17.1 tree

    repo init -u https://github.com/LineageOS/android.git -b lineage-17.1 --git-lfs
    mkdir -p .repo/local_manifests
    curl -L https://raw.githubusercontent.com/godrenkon/Challenge_Pad-Android10-ROM/main/manifest/local_manifests/ctz.xml \
      -o .repo/local_manifests/ctz.xml
    repo sync -c --no-clone-bundle --no-tags -j$(nproc)

The manifest adds this repository at device/benesse/ctz. Vendor files and a
kernel project will be added only after their exact source and license are
confirmed.

## First source-only check

    source build/envsetup.sh
    lunch lineage_ctz-userdebug

A complete build is intentionally not promised at this stage. It should fail
with a clear missing-kernel or missing-vendor message rather than producing an
image that could be mistaken for a working ROM.

## Build after bring-up prerequisites are complete

    mka bacon

Never flash a generated image until the release checklist in docs/bring-up.md
passes on the exact TAB-A05-BA1.
