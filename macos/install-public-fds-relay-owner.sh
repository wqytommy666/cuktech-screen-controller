#!/bin/zsh
set -euo pipefail

HERE="${0:A:h}"
ROOT="${HERE:h}"
cd "$ROOT"
STOCK="${1:-${CUKTECH_FDS_RELAY_STOCK:-}}"
GIST_ID="${CUKTECH_RELAY_DISCOVERY_GIST:-6e3d9ecbd917f0c1252caac1ad620978}"
PYTHON="$ROOT/.venv/bin/python"
SERVER_LABEL="io.github.wqytommy666.cuktech-screen-controller.fds-relay"
TUNNEL_LABEL="io.github.wqytommy666.cuktech-screen-controller.fds-relay-tunnel"
SERVER_PLIST="$HOME/Library/LaunchAgents/$SERVER_LABEL.plist"
TUNNEL_PLIST="$HOME/Library/LaunchAgents/$TUNNEL_LABEL.plist"
LOG_DIR="$HOME/Library/Logs/CUKTECH Screen Controller"
CACHE_DIR="$HOME/Library/Caches/CUKTECH Screen Controller/fds-relay"
KEYCHAIN_SERVICE="com.wqytommy.CUKTECHScreenController.mi-home-relay"
KEYCHAIN_ACCOUNT="relay"

if [[ -z "$STOCK" || ! -f "$STOCK" ]]; then
  echo "Usage: $0 /private/path/ap01-1.0.2_0031.bin" >&2
  exit 2
fi
if [[ ! -x "$PYTHON" ]]; then
  echo "Missing $PYTHON; run scripts/setup-macos.sh first" >&2
  exit 2
fi
EXPECTED="8a721fc8ef25458d415b2460e4a251e0503a82f7743fdff85b12612190e5c1cb"
ACTUAL="$(/usr/bin/shasum -a 256 "$STOCK" | /usr/bin/awk '{print $1}')"
if [[ "$ACTUAL" != "$EXPECTED" ]]; then
  echo "Stock firmware SHA-256 is not the reviewed AP01 1.0.2_0031 image" >&2
  exit 2
fi

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR" "$CACHE_DIR"
chmod 700 "$LOG_DIR" "$CACHE_DIR"
chmod +x "$HERE/run-public-fds-relay-tunnel.sh"

"$PYTHON" "$HERE/store_mi_home_keychain.py" \
  --service "$KEYCHAIN_SERVICE" --account "$KEYCHAIN_ACCOUNT"

cat > "$SERVER_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$SERVER_LABEL</string>
  <key>ProgramArguments</key><array>
    <string>$PYTHON</string><string>-u</string>
    <string>$ROOT/ap01_fds_relay_server.py</string>
    <string>--stock-firmware</string><string>$STOCK</string>
    <string>--cache-dir</string><string>$CACHE_DIR</string>
    <string>--bind</string><string>127.0.0.1</string>
    <string>--port</string><string>8790</string>
    <string>--trust-proxy</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>EnvironmentVariables</key><dict>
    <key>HOME</key><string>$HOME</string>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>CUKTECH_MI_KEYCHAIN_SERVICE</key><string>$KEYCHAIN_SERVICE</string>
    <key>CUKTECH_MI_KEYCHAIN_ACCOUNT</key><string>$KEYCHAIN_ACCOUNT</string>
  </dict>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>StandardOutPath</key><string>$LOG_DIR/fds-relay.log</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/fds-relay.error.log</string>
</dict></plist>
PLIST

cat > "$TUNNEL_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$TUNNEL_LABEL</string>
  <key>ProgramArguments</key><array><string>$HERE/run-public-fds-relay-tunnel.sh</string></array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>EnvironmentVariables</key><dict>
    <key>HOME</key><string>$HOME</string>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>CUKTECH_RELAY_DISCOVERY_GIST</key><string>$GIST_ID</string>
  </dict>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>15</integer>
  <key>StandardOutPath</key><string>$LOG_DIR/fds-relay-tunnel.log</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/fds-relay-tunnel.error.log</string>
</dict></plist>
PLIST

for label in "$TUNNEL_LABEL" "$SERVER_LABEL"; do
  /bin/launchctl bootout "gui/$UID/$label" >/dev/null 2>&1 || true
done
sleep 1
bootstrap() {
  local plist="$1"
  /bin/launchctl bootstrap "gui/$UID" "$plist" 2>/dev/null || {
    sleep 2
    /bin/launchctl bootstrap "gui/$UID" "$plist"
  }
}
bootstrap "$SERVER_PLIST"
sleep 1
bootstrap "$TUNNEL_PLIST"

echo "FDS relay and HTTPS tunnel installed. Discovery will update automatically."
