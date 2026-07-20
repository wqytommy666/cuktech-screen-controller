#!/bin/zsh
set -euo pipefail

ROOT="${0:A:h:h}"
cd "$ROOT"

echo "CUKTECH Screen Controller · Agent 一键配置"
echo "==========================================="

PYTHON=""
for candidate in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
    if [[ -x "$candidate" ]] && "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 9))' 2>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done
if [[ -z "$PYTHON" ]]; then
    echo "[失败] 需要 Python 3.9 或更高版本。"
    echo "安装后重新运行本脚本：https://www.python.org/downloads/macos/"
    exit 1
fi

echo "[1/5] Python: $($PYTHON --version)"
if [[ ! -x .venv/bin/python ]]; then
    "$PYTHON" -m venv .venv
fi

echo "[2/5] 安装运行依赖…"
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
.venv/bin/python -c 'import PIL, requests, cryptography'

echo "[3/5] 初始化显示模式…"
mkdir -p artifacts
if [[ ! -f artifacts/ap01-mode ]]; then
    print -r -- "quota" > artifacts/ap01-mode
fi

echo "[4/5] 安装登录自动启动 Bridge…"
./macos/install-launch-agent.sh

if [[ "${CUKTECH_SETUP_DRY_RUN:-0}" == "1" ]]; then
    echo "[5/5] 测试模式：环境与 LaunchAgent 配置已验证，未启动服务。"
    exit 0
fi

echo "[5/5] 等待本地健康检查…"
for _ in {1..20}; do
    if /usr/bin/curl --noproxy '*' -fsS --max-time 2 http://127.0.0.1:8765/health >/dev/null 2>&1; then
        echo "[成功] Bridge 已运行：http://127.0.0.1:8765/health"
        ./macos/diagnose.sh || true
        exit 0
    fi
    sleep 1
done

echo "[失败] Bridge 未在 20 秒内启动。下面是诊断结果："
./macos/diagnose.sh || true
exit 1
