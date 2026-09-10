# AP01 firmware compatibility status

> Verified 2026-09-10 for model `njcuk.enstor.ap01`.

## Compatibility matrix

| Device state | Current support |
| --- | --- |
| Stock `1.0.2_0031` | One-time realtime Loader installation is supported |
| Patched `1.0.2_0031` | Keep using LAN/RAM refreshes; do not repeat OTA |
| Stock or upgraded `1.0.2_0041` | Third-party Loader installation is not currently supported |
| Downgrade `0041` to `0031` | Not supported by the known Mi Home `miIO.ota` path |

Owners who still need a custom screen and remain on `1.0.2_0031` should not
install `1.0.2_0041`. An already-patched `0031` display does not need the relay
for daily content updates; its GIF slots are RAM-backed.

## Verified `1.0.2_0041` behavior

The current Xiaomi OTA artifact is 6,769,704 bytes with MD5
`3c2d962be82c73860daff903178d9b9e` and SHA-256
`972db4c136c7ed9e24a83c07c1a7fd62040ca018b08ca285216d26b1fee3c6b9`.
It was published on 2026-08-13 16:38:14 Asia/Shanghai.

Static comparison of the official images confirms that `0041` adds an OTA
branch which logs `unsigned app firmware rejected for security` and returns an
error when `signed_file` is false. The corresponding `0031` path continues to
process unsigned application firmware. `0041` also retains downgrade blocking.

The current patch is deliberately build-specific. Stock `0031` is 6,804,520
bytes, while `0041` has a different size, layout and function addresses. The
patcher rejects it with `unexpected firmware size: 6769704`. Relocating the
hooks alone would still leave the modified image blocked by the new OTA
signature gate.

## Relay availability is a separate concern

The gateway-free relay uploads the reviewed `0031` Loader to Xiaomi FDS and
returns a short-lived download ticket. It does not possess a vendor signing key
and cannot turn a modified image into a CUKTECH/Xiaomi-signed image.

A read-only/local test on 2026-09-10 confirmed that the relay origin, reviewed
`0031` build, Xiaomi FDS upload, and CDN readback all work. The public button is
currently offline at the Quick Tunnel ingress. Restoring that ingress or using
an FDS-capable gateway can restore `0031` delivery, but neither can make an
`0041` device accept the unsigned Loader.

Do not disguise an old BIN as a newer version or repeatedly retry OTA on an
`0041` device. A future `0041` solution requires a verified vendor-signed path,
an officially authorized downgrade, or a separately validated recovery/
bootloader installation route. Existing Pogo/UART research is not yet such a
route.
