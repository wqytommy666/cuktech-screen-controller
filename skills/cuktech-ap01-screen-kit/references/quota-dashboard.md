# Claude and Codex quota dashboard

## Data sources

The bundled automatic account collector supports macOS and Windows. macOS
reads Claude Desktop's cookie store and Claude Safe Storage through Keychain.
Windows copies the current user's Electron cookie database, unwraps its key
with DPAPI, and decrypts supported Chromium cookie records in memory.

- Query Codex through the signed-in official `codex app-server` API.
- Query Claude through Claude Desktop's encrypted Electron cookies and the
  official Claude usage endpoint.
- Keep credentials and session cookies in memory. Write only sanitized quota
  values and rendered images.
- On Windows, look for the official Codex executable or CLI; use
  `CUKTECH_CODEX_BIN` only for a non-standard installation.

The bundled renderer supports Claude 5-hour, weekly, and Fable 5 windows plus
Codex 5-hour and weekly windows. A missing Codex 5-hour window is rendered as
the promotional/inactive state rather than as an API error.

## Render and preview

```bash
.venv/bin/python quota_dashboard.py
.venv/bin/python -m unittest -v test_quota_dashboard.py
```

Windows PowerShell uses `.\.venv\Scripts\python.exe` in place of
`.venv/bin/python`.

Outputs live in `artifacts/`:

- `quota-dashboard-master.png`: 1280x960 design master.
- `quota-dashboard@2x.png`: 640x480 preview.
- `quota-dashboard.png`: 320x240 frame.
- `quota-dashboard.gif`: lightweight four-frame GIF89a with subtle rail glints.
- `quota-current.json`: sanitized values.

## Customize the UI

Edit design tokens and geometry inside `render_master()` in
`quota_dashboard.py`. Preserve these invariants:

1. Keep rows `0..39` empty for the AP01 clock/date overlay.
2. Keep the device output exactly 320x240.
3. Keep large numbers visually centered inside their rings.
4. Use near-black surfaces on panels that lift blacks or look washed out.
5. Export at least two slow frames; one-frame GIFs may render black.
6. Keep the GIF under 90 KB for smooth playback when practical.

Run the tests after every layout change and inspect the 2x preview before
serving it.

## Run the live bridge

```bash
.venv/bin/python -u ap01_wifi_bridge.py \
  --bind 0.0.0.0 --port 8765 --interval 300
```

Verify:

```bash
curl --noproxy '*' http://127.0.0.1:8765/health
```

The bridge regenerates the dashboard every five minutes. A log entry from the
AP01 LAN IP requesting `/screen.gif` confirms end-to-end delivery.

## Partial collection failures

Each official account is collected independently. If one fails, its panel shows unavailable values while the other continues to refresh. `/health` reports `status: "partial"` and `provider_errors`; `connected` describes quota collection, not physical AP01 delivery. Only a recent request from the AP01 proves display delivery. If both accounts fail or the snapshot ages out, the full disconnected fallback remains active.
