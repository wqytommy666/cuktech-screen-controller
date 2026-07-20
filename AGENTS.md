# CUKTECH Screen Controller — Agent operating guide

This repository controls a CUKTECH AP01 detachable display.  Treat the two
operations below as different workflows:

- **Daily screen refresh:** serve a 320×240 GIF over the LAN.  The AP01 writes
  it to rotating `/tmp/.ap01q*.gif` RAM slots.  This is the normal path.
- **One-time real-time loader installation:** modify and install firmware for
  the exact supported model/build.  This writes Flash and requires explicit
  user confirmation.

## Start here on every new Mac

1. Read `README.zh-CN.md` (or `README.md`) and
   `skills/cuktech-ap01-screen-kit/SKILL.md`.
2. Run only read-only checks first:

   ```bash
   ./macos/diagnose.sh
   ```

   A non-zero result before installation simply means prerequisites are still
   missing; read the printed checklist and continue with the applicable setup.

3. Confirm all of the following with the user:
   - macOS 14+ and Apple Silicon for the packaged app;
   - Mac and AP01 are on the same Wi-Fi without client/AP isolation;
   - Claude Desktop and the official Codex/ChatGPT app are installed and
     signed in when quota display is requested;
   - whether this AP01 already requests `GET /screen.gif` from the Mac;
   - exact AP01 model and firmware before any loader work.
4. For a source/agent installation, run:

   ```bash
   ./scripts/setup-macos.sh
   ```

5. Verify both endpoints and the device request:

   ```bash
   curl --noproxy '*' http://127.0.0.1:8765/health
   curl --noproxy '*' -I http://127.0.0.1:8765/screen.gif
   ./macos/diagnose.sh
   ```

## Choose the smallest workflow

- Already sees AP01 `GET /screen.gif`: do **not** perform OTA.  Configure quota
  mode or convert custom artwork and restart the Bridge.
- No real-time loader: verify exact model `njcuk.enstor.ap01` and firmware
  `1.0.2_0031`, then follow
  `skills/cuktech-ap01-screen-kit/references/realtime-firmware.md`.
- Custom image: follow
  `skills/cuktech-ap01-screen-kit/references/custom-content.md`.
- Claude/Codex quota panel: follow
  `skills/cuktech-ap01-screen-kit/references/quota-dashboard.md`.
- Network/startup issue: follow
  `skills/cuktech-ap01-screen-kit/references/network-operations.md`.

## Non-negotiable checks

- Never guess firmware offsets or reuse the patch on another build.
- Never OTA an already real-time-patched image through `ap01_custom_ota.py`.
- Never run OTA merely to update artwork or quota values.
- Never commit cookies, Xiaomi credentials, device IDs, signed OTA URLs,
  firmware binaries, or generated `artifacts/`.
- Require the user's explicit confirmation immediately before a one-time
  firmware installation.
- A successful handoff includes `/health`, a valid GIF89a, and a logged AP01
  `GET /screen.gif 200` request.
