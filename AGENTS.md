# CUKTECH AP01 agent guide

## Choose the smallest workflow

- **Daily refresh:** serve a 320×240 GIF over LAN; the patched AP01 uses rotating `/tmp/.ap01q*.gif` RAM slots. Do not use firmware installation to refresh artwork or quota values.
- **First real-time loader:** a model/build-specific firmware installation writes Flash and requires explicit confirmation immediately before installation.
- Detect the host OS and relevant local bridge state with read-only checks. Use known facts and diagnostics rather than repeating questions the computer can answer.
- For a new host, missing prerequisites or a first loader, follow [first-install setup](docs/agent-first-install.md). Do not run setup or require all setup documents for an ordinary content edit.
- The first-install runbook is the shared entry for Codex and WorkBuddy. Use a clean clone and the owner's local accounts/network; a preinstalled Skill or maintainer-specific files must not be prerequisites. Report Windows Mi Home login and relay availability blockers explicitly.

## Route by the requested change

- Existing AP01 `GET /screen.gif`: use the content/quota workflow; no OTA.
- Custom image: `skills/cuktech-ap01-screen-kit/references/custom-content.md`.
- Quota panel: `skills/cuktech-ap01-screen-kit/references/quota-dashboard.md`.
- LAN, IP or startup failure: `skills/cuktech-ap01-screen-kit/references/network-operations.md`.
- First loader: verify the exact model/build, then use `skills/cuktech-ap01-screen-kit/references/realtime-firmware.md`.

Already-patched local artwork needs a working LAN, not internet or USB data transport. Automatic quota refresh needs internet on the host; a first loader needs the device and installation environment online. Keep the detailed address-reservation and network preconditions in the first-install/network guides.

## Non-negotiable checks

- Never guess firmware offsets or reuse the patch on another build.
- Treat `1.0.2_0041` as unsupported: it rejects the current unsigned Loader
  and the known Mi Home OTA path cannot downgrade it. FDS transport does not
  bypass firmware signing. Stop before build or delivery on that version.
- Never OTA an already real-time-patched image through `ap01_custom_ota.py`.
- Never run OTA merely to update artwork or quota values.
- Never force an old IP onto the Bridge until the router client/DHCP tables
  prove it is free; a failed ping is not sufficient evidence.
- When `GET /screen.gif` disappears after a host-address change, restore the
  embedded old IP first without OTA. Rebuild/reinstall only when the old
  address cannot be recovered, and reserve the new address before building.
- Never commit cookies, Xiaomi credentials, device IDs, signed OTA URLs,
  firmware binaries, or generated `artifacts/`.
- Require the user's explicit confirmation immediately before a one-time
  firmware installation.
- A successful handoff includes `/health`, a valid GIF89a, and a logged AP01
  `GET /screen.gif 200` request.

## Verify the requested deliverable

- Artwork: inspect the preview and validate 320×240 dimensions, GIF89a, frame count and size.
- Bridge/rendering code: run affected existing tests and check relevant service behavior.
- Deployment: verify `/health`, a valid GIF and a logged AP01 `GET /screen.gif 200`; do not claim device delivery from a local preview alone.
- Firmware build: retain all existing manifest, checksum, hook-target and payload-readback checks. A successful build does not authorize installation.
- Offline design-only requests can be delivered with local validation; state that device delivery was not tested rather than initiating a device operation.

Preserve unrelated working-tree files. Reuse still-valid evidence and repeat checks only when related changes or failures require it.
