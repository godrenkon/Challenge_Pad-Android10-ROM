# CTZ vendor files

Vendor blobs are deliberately not included in this public repository. The
extraction script reads the user's own stock partitions or a legally obtained
firmware package and writes local output under
vendor/benesse/ctz/proprietary/.

Before adding any file to the manifest:

- record its source partition and build fingerprint;
- verify its architecture and Android linker dependencies;
- check whether redistribution is permitted;
- test it on TAB-A05-BA1, not just a related CTX device.
