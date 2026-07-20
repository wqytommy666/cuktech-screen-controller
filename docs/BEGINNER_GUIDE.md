# CUKTECH Screen Controller beginner guide

This guide is for people who do not normally use Terminal or write code.

## Before you begin

Prepare an Apple Silicon Mac running macOS 14 or later. This includes 2024,
2025, and 2026 Macs and macOS versions 24, 25, and 26. Put the Mac and AP01
on the same non-guest Wi-Fi network. For the quota dashboard, install and sign
in to Claude Desktop and the official Codex/ChatGPT app.

If the AP01 has already shown a custom image or quota dashboard, its real-time
loader is installed and normal updates only use RAM. A completely stock AP01
needs the supported loader installed once; use the coding-agent route below.

## Install the app

1. Download the latest arm64 ZIP from
   [GitHub Releases](https://github.com/wqytommy666/cuktech-screen-controller/releases/latest).
2. Unzip it and double-click `Install CUKTECH Screen Controller.command`.
3. If macOS blocks the command, Control-click it, choose **Open**, and confirm.
4. Wait for “安装完成”. The app opens automatically.
5. Follow the in-app **新手引导 / Beginner guide** readiness checks.

Choose **显示 Claude / Codex 额度** for quotas, or choose a fit mode and click
**选择图片并推送** for PNG, JPG, HEIC, WebP, or animated GIF content.

## Give the repository to a coding agent

Give Claude Code, Codex, OpenCode, WorkBuddy, or another terminal-capable agent
this URL:

```text
https://github.com/wqytommy666/cuktech-screen-controller
```

Use this prompt:

```text
Read AGENTS.md, README.md, and skills/cuktech-ap01-screen-kit/SKILL.md first.
I am not a programmer, so ask for only one manual action at a time. Run the
read-only diagnostic before making changes. Configure the app/Bridge, verify
/health, validate the 320x240 GIF89a, and show a logged AP01 GET /screen.gif
200. If the real-time loader is already installed, do not use OTA. If it is
missing, verify the exact supported AP01 model and firmware and ask me again
immediately before the one-time installation. Daily updates must use /tmp RAM.
```

## If something stops updating

Open the in-app beginner guide and rerun its checks, or ask the agent:

```text
Run ./macos/diagnose.sh and repair the Bridge without performing OTA.
```

The Mac must remain logged in and connected to the same Wi-Fi. The AP01 keeps
the last successful screen while the Mac is offline.
