# CUKTECH AP01 shared FDS relay

The relay lets an AP01 owner without a Xiaomi gateway perform the one-time
real-time loader installation. It is not part of normal screen delivery: after
installation, AP01 fetches `/screen.gif` directly from the owner's LAN Bridge.

## User requirements

- a powered CUKTECH AP01 paired and online in the owner's Mi Home account;
- AP01 model/firmware exactly `njcuk.enstor.ap01 / 1.0.2_0031`;
- the Controller computer and AP01 on the same non-isolated LAN;
- CUKTECH Screen Controller.

No gateway purchase, firmware file, USB data cable or command line is needed.
The app performs read-only checks and download-only validation first, then
requires explicit confirmation immediately before the Flash write.

## Trust boundary

The client sends only API version, fixed model/version, its private-LAN Bridge
URL and refresh interval. The relay never receives Mi Home credentials, AP01
DID/MAC, Claude/Codex sessions or arbitrary firmware uploads.

Server guarantees:

- stock image pinned to SHA-256
  `8a721fc8ef25458d415b2460e4a251e0503a82f7743fdff85b12612190e5c1cb`;
- only private IPv4 `http://IP:8765/screen.gif` targets;
- no arbitrary upload endpoint;
- existing Recovery CRC, changed-range, payload readback and relocation checks;
- Xiaomi OTA CDN host pinning;
- client-side BFNP, size, SHA-256 and MD5 verification;
- signed URLs excluded from normal logs;
- per-client and global rate limits with serialized builds/uploads.

## Run the origin

The operator needs a locally signed-in Mi Home account containing a real
`lumi.gateway.*` or `xiaomi.gateway.*` device, the private hash-matching stock
image, Python dependencies, and `riscv64-elf-gcc/binutils`.

```bash
python3 ap01_fds_relay_server.py \
  --stock-firmware /private/path/ap01-1.0.2_0031.bin \
  --cache-dir "$HOME/Library/Caches/CUKTECH Screen Controller/fds-relay" \
  --bind 127.0.0.1 --port 8790 --trust-proxy
```

Keep credentials, gateway identifiers, firmware and signed URLs out of Git.
Expose the loopback origin only through an HTTPS reverse proxy such as
Cloudflare Tunnel. Publish its stable URL in the maintainer's discovery JSON
(`relay-service.json` documents the format); set `enabled` to `false` during
maintenance.

On macOS, `macos/install-public-fds-relay-owner.sh` installs the origin and
discovery-updating tunnel as login services. The bundled tunnel runner removes
inherited desktop proxy variables and lets `cloudflared` select QUIC or HTTP/2
by default. Operators can set `CUKTECH_RELAY_PROTOCOL=quic` or
`CUKTECH_RELAY_PROTOCOL=http2` when their network permits only one transport;
do not pin a protocol without first checking outbound port 7844. Discovery is marked offline at
startup and exit, and is only enabled after the new public URL passes an
external `/health` probe. The probe uses DoH so a brief NXDOMAIN during Quick
Tunnel creation is not retained by the host's negative DNS cache.

Quick Tunnels are disposable development ingress and have no uptime guarantee.
Use a Cloudflare Named Tunnel on an owned hostname, or an equivalent stable
HTTPS ingress, for a long-running public relay.

If discovery says online but a `trycloudflare.com` hostname returns NXDOMAIN,
that disposable Quick Tunnel has expired. Restart the updated tunnel runner;
do not leave clients pointed at the stale URL. Repeated
transport errors against `198.18.*` identify a Fake-IP/proxy route; compare the
QUIC and HTTP/2 connectivity preflight rather than assuming one protocol works
everywhere.

The relay only builds and uploads the verified image. The owner's local Mi
Home session still sends the final OTA command to their own AP01, after the
app's explicit confirmation.

### Runtime health and discovery lease

`ap01_relay_supervisor.py` checks public health continuously, including the JSON service identity and firmware version. It withdraws discovery on a failed check, replaces the tunnel after three consecutive failures, and retries startup after 180 seconds without public readiness. Health probes support the macOS system HTTPS proxy, an explicit `CUKTECH_RELAY_HEALTH_PROXY`, and direct/DoH fallbacks.

Online discovery is renewed roughly every 90 seconds with a 240-second `expires_at` lease. Updated clients reject expired records after host sleep or total network loss; older clients remain compatible but do not enforce the lease.
