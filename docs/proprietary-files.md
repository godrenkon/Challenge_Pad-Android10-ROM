# Proprietary file policy

This repository is public. Do not commit extracted Panasonic, Benesse,
MediaTek, Google or third-party binaries unless redistribution permission is
explicitly documented.

The intended pattern is:

1. User supplies a stock image or performs a local ADB/fastboot extraction.
2. scripts/extract-stock.sh copies only the files named in the manifest.
3. The local vendor tree is used for a build.
4. CI verifies the source tree without requiring proprietary files.
5. Release artifacts include only files that are legally redistributable.

Google Mobile Services are not part of the ROM source. If a compatible package
is later documented, it must be downloaded separately by the user and kept
outside the public source repository.
