#!/bin/zsh
set -u

HERE="${0:A:h}"
ROOT="${HERE:h}"
ARTIFACTS="$ROOT/artifacts"
LABEL="io.github.wqytommy666.cuktech-screen-controller.bridge"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

PASS=0
WARN=0
FAIL=0

ok()   { PASS=$((PASS + 1)); printf '✅ %-16s %s\n' "$1" "$2"; }
warn() { WARN=$((WARN + 1)); printf '⚠️  %-16s %s\n' "$1" "$2"; }
bad()  { FAIL=$((FAIL + 1)); printf '❌ %-16s %s\n' "$1" "$2"; }

echo "CUKTECH Screen Controller · 只读诊断"
echo "======================================"

if [[ "$(uname -s)" == "Darwin" ]]; then
    ok "系统" "macOS $(sw_vers -productVersion) · $(uname -m)"
else
    warn "系统" "当前不是 macOS；只能进行仓库与图片测试"
fi

if [[ -x "$ROOT/.venv/bin/python" ]]; then
    VERSION="$($ROOT/.venv/bin/python --version 2>&1)"
    if "$ROOT/.venv/bin/python" -c 'import PIL, requests, cryptography' >/dev/null 2>&1; then
        ok "运行环境" "$VERSION · 依赖已就绪"
    else
        bad "运行环境" "$VERSION · Python 依赖不完整"
    fi
else
    bad "运行环境" "缺少 $ROOT/.venv；请运行 scripts/setup-macos.sh"
fi

if [[ -d /Applications/Claude.app || -d "$HOME/Applications/Claude.app" ]]; then
    ok "Claude" "已安装；请确认软件内已经登录"
else
    warn "Claude" "未发现 Claude Desktop；自定义图片模式不受影响"
fi

CODEX=""
for candidate in \
    "$(command -v codex 2>/dev/null || true)" \
    /Applications/ChatGPT.app/Contents/Resources/codex \
    /Applications/Codex.app/Contents/Resources/codex \
    "$HOME/Applications/ChatGPT.app/Contents/Resources/codex" \
    "$HOME/Applications/Codex.app/Contents/Resources/codex"; do
    if [[ -n "$candidate" && -x "$candidate" ]]; then CODEX="$candidate"; break; fi
done
if [[ -n "$CODEX" ]]; then
    ok "Codex" "已发现 $CODEX；请确认账户已经登录"
else
    warn "Codex" "未发现官方 App/CLI；自定义图片模式不受影响"
fi

if [[ -f "$PLIST" ]]; then
    ok "登录自启" "已安装 $LABEL"
else
    bad "登录自启" "未安装；请运行 macos/install-launch-agent.sh"
fi

HEALTH="$(/usr/bin/curl --noproxy '*' -sS --max-time 3 http://127.0.0.1:8765/health 2>/dev/null || true)"
if [[ "$HEALTH" == \{* ]]; then
    ok "后台服务" "$HEALTH"
else
    bad "后台服务" "无法访问 http://127.0.0.1:8765/health"
fi

LAN_IP=""
for interface in en0 en1; do
    LAN_IP="$(/usr/sbin/ipconfig getifaddr "$interface" 2>/dev/null || true)"
    [[ -n "$LAN_IP" ]] && break
done
if [[ -n "$LAN_IP" ]]; then
    ok "局域网地址" "http://$LAN_IP:8765/screen.gif"
else
    warn "局域网地址" "未找到 Wi-Fi IPv4；请连接与 AP01 相同的 Wi-Fi"
fi

if [[ -f "$ARTIFACTS/quota-dashboard.gif" || -f "$ARTIFACTS/custom-screen.gif" ]]; then
    ok "屏幕文件" "已生成 GIF"
else
    warn "屏幕文件" "等待首次生成"
fi

LOG="$ARTIFACTS/ap01_launchd.log"
if [[ -f "$LOG" ]]; then
    REQUEST="$(grep 'GET /screen.gif' "$LOG" 2>/dev/null | tail -1 || true)"
    if [[ -n "$REQUEST" ]]; then
        ok "AP01 请求" "$REQUEST"
    else
        warn "AP01 请求" "日志中还没有 GET /screen.gif；检查 Wi-Fi 或实时加载器"
    fi
else
    warn "AP01 请求" "尚未生成 Bridge 日志"
fi

echo "--------------------------------------"
echo "结果：$PASS 项正常 · $WARN 项待确认 · $FAIL 项需要处理"
echo "本诊断不会读取或输出账号 Cookie、密码、OTA 签名链接。"

(( FAIL == 0 ))
