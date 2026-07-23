#!/bin/zsh
set -euo pipefail

ORIGIN="${CUKTECH_FDS_RELAY_ORIGIN:-http://127.0.0.1:8790}"
GIST_ID="${CUKTECH_RELAY_DISCOVERY_GIST:-}"
CLOUDFLARED="${CUKTECH_CLOUDFLARED:-$HOME/.local/bin/cloudflared}"
GH="${CUKTECH_GH:-/opt/homebrew/bin/gh}"
STATE="$HOME/Library/Application Support/CUKTECH Screen Controller/fds-relay"
DISCOVERY="$STATE/cuktech-relay-service.json"

if [[ -z "$GIST_ID" ]]; then
  echo "CUKTECH_RELAY_DISCOVERY_GIST is required" >&2
  exit 2
fi
if [[ ! -x "$CLOUDFLARED" || ! -x "$GH" ]]; then
  echo "cloudflared and gh are required" >&2
  exit 2
fi

mkdir -p "$STATE"
chmod 700 "$STATE"

for _ in {1..60}; do
  if /usr/bin/curl --noproxy '*' -fsS --max-time 2 "$ORIGIN/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
/usr/bin/curl --noproxy '*' -fsS --max-time 3 "$ORIGIN/health" >/dev/null

PUBLISHED=""
"$CLOUDFLARED" tunnel --no-autoupdate --url "$ORIGIN" 2>&1 | while IFS= read -r line; do
  print -r -- "$line"
  URL="$(print -r -- "$line" | /usr/bin/grep -Eo 'https://[-a-z0-9]+\.trycloudflare\.com' | /usr/bin/tail -1 || true)"
  if [[ -n "$URL" && "$URL" != "$PUBLISHED" ]]; then
    cat > "$DISCOVERY" <<JSON
{
  "enabled": true,
  "url": "$URL",
  "api_version": 1,
  "message": "Gateway-free AP01 onboarding relay is online"
}
JSON
    chmod 600 "$DISCOVERY"
    "$GH" gist edit "$GIST_ID" --filename cuktech-relay-service.json "$DISCOVERY" >/dev/null
    PUBLISHED="$URL"
    echo "Relay discovery updated: $URL"
  fi
done
