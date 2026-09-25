# Connectivity repair — September 25, 2026

The old Quick Tunnel hostname returned NXDOMAIN while discovery still advertised
it as online. Startup-only health checks failed to withdraw an address after a
running tunnel lost connectivity.

`ap01_relay_supervisor.py` now checks the public endpoint continuously, validates
its service identity, withdraws failed endpoints and replaces persistently failed
tunnels. Online discovery has a renewable 240-second lease. Updated source clients
reject expired discovery; existing released clients still accept the URL format.
Health probes support the maintenance computer's system HTTPS proxy.

The public workflow passed ticket issuance, download from Xiaomi's OTA CDN and
container/length/hash verification for a 6,804,520-byte image. No download or
installation command was sent to an AP01 during this test.

Quick Tunnels still depend on the maintenance computer and its network. A stable
HTTPS endpoint on an always-on host remains the recommended long-term deployment;
see the [operator guide](FDS_RELAY_OPERATOR.md).

Daily display refresh does not use this shared relay. The Loader requests the
computer address embedded at installation. When DHCP changes that address,
inspect the router's client/lease tables before restoring it. A failed ping alone
does not prove an address is free. The tested AP01 could send a diagnostic packet
to the computer. Follow-up router inspection found an outdated reservation for
the Mac's previous Wi-Fi MAC address. After checking that the Loader's embedded
address was unused, the reservation was updated to the Mac's current fixed
private address and its DHCP lease was renewed. The AP01 resumed HTTP 200 image
requests at 15:22, then downloaded the Antigravity/Codex dashboard at 15:27
(host local time). This repair did not use OTA or modify the display firmware.

Quota collection now handles Claude and Codex independently. A missing Claude
Desktop session no longer hides working Codex data. Unavailable provider values
are null and the panel is marked disconnected; `/health` reports `partial` and
`provider_errors`. If both providers fail or the data expires, the complete
offline screen remains active. `connected` describes quota collection, not
physical display delivery: a recent AP01 image request is still required.

Mac and Windows status text and Mac diagnostics were updated accordingly. App
source changes do not imply that new installers have been released.

Firmware support remains limited to `njcuk.enstor.ap01 / 1.0.2_0031`.
The `0041` signature restriction is unchanged.
