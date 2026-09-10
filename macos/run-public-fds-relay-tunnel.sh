#!/bin/zsh
set -euo pipefail

ORIGIN="${CUKTECH_FDS_RELAY_ORIGIN:-http://127.0.0.1:8790}"
GIST_ID="${CUKTECH_RELAY_DISCOVERY_GIST:-}"
CLOUDFLARED="${CUKTECH_CLOUDFLARED:-$HOME/.local/bin/cloudflared}"
GH="${CUKTECH_GH:-/opt/homebrew/bin/gh}"
DOH_URL="${CUKTECH_RELAY_DOH_URL:-https://cloudflare-dns.com/dns-query}"
TUNNEL_PROTOCOL="${CUKTECH_RELAY_PROTOCOL:-auto}"
STATE="$HOME/Library/Application Support/CUKTECH Screen Controller/fds-relay"
DISCOVERY="$STATE/cuktech-relay-service.json"

publish_discovery() {
  local enabled="$1"
  local url="$2"
  local message="$3"

  cat > "$DISCOVERY" <<JSON
{
  "enabled": $enabled,
  "url": "$url",
  "api_version": 1,
  "message": "$message"
}
JSON
  chmod 600 "$DISCOVERY"
  "$GH" gist edit "$GIST_ID" --filename cuktech-relay-service.json "$DISCOVERY" >/dev/null
}

mark_offline() {
  publish_discovery false "" \
    "Gateway-free AP01 onboarding relay is temporarily offline; please retry later" || true
}

public_health() {
  local url="$1"

  # A just-created Quick Tunnel can briefly return NXDOMAIN.  macOS and some
  # proxy clients cache that negative answer after Cloudflare has published the
  # hostname, so resolve the probe through DoH.  Fall back for older curl builds.
  /usr/bin/curl --noproxy '*' --doh-url "$DOH_URL" \
    -fsS --connect-timeout 5 --max-time 8 "$url/health" >/dev/null 2>&1 ||
    /usr/bin/curl --noproxy '*' \
      -fsS --connect-timeout 5 --max-time 8 "$url/health" >/dev/null 2>&1
}

if [[ -z "$GIST_ID" ]]; then
  echo "CUKTECH_RELAY_DISCOVERY_GIST is required" >&2
  exit 2
fi
if [[ ! -x "$CLOUDFLARED" || ! -x "$GH" ]]; then
  echo "cloudflared and gh are required" >&2
  exit 2
fi
if [[ "$TUNNEL_PROTOCOL" != "auto" && "$TUNNEL_PROTOCOL" != "quic" && "$TUNNEL_PROTOCOL" != "http2" ]]; then
  echo "CUKTECH_RELAY_PROTOCOL must be auto, quic, or http2" >&2
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

# A Quick Tunnel URL is disposable.  Never leave yesterday's hostname marked
# online while a replacement connection is still starting or has exited.
mark_offline
trap mark_offline EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

PUBLISHED=""
# Proxy clients commonly synthesize 198.18.0.0/15 Fake-IP answers.  Older
# cloudflared/proxy combinations could leave QUIC alive without reaching an
# edge, but forcing HTTP/2 breaks networks that block outbound TCP 7844 while
# still routing UDP 7844 correctly.  Let cloudflared's connectivity preflight
# choose by default; operators can pin quic/http2 with CUKTECH_RELAY_PROTOCOL.
# Do not inherit desktop proxy variables here because cloudflared establishes
# its own edge connection through the active system route.
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
    -u http_proxy -u https_proxy -u all_proxy \
  "$CLOUDFLARED" tunnel --protocol "$TUNNEL_PROTOCOL" --no-autoupdate --url "$ORIGIN" 2>&1 | \
while IFS= read -r line; do
  print -r -- "$line"
  URL="$(print -r -- "$line" | /usr/bin/grep -Eo 'https://[-a-z0-9]+\.trycloudflare\.com' | /usr/bin/tail -1 || true)"
  if [[ -n "$URL" && "$URL" != "$PUBLISHED" ]]; then
    READY=false
    for _ in {1..30}; do
      if public_health "$URL"; then
        READY=true
        break
      fi
      sleep 1
    done
    if [[ "$READY" != true ]]; then
      echo "Tunnel URL did not pass its public health check; discovery remains offline" >&2
      continue
    fi
    publish_discovery true "$URL" \
      "Gateway-free AP01 onboarding relay is online"
    PUBLISHED="$URL"
    echo "Relay discovery updated: $URL"
  fi
done
