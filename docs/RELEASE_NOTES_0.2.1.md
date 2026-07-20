# CUKTECH Screen Controller 0.2.1

## 中文

- 新增软件内“新手引导”，首次打开自动检查运行环境、登录自启、Bridge、
  Claude/Codex、Wi-Fi 与 AP01 请求记录。
- 新增完整的[零基础教程](BEGINNER_GUIDE.zh-CN.md)，覆盖下载、安装、换图、
  额度显示、重启恢复与原厂屏幕首次配置。
- 新增 `AGENTS.md`、`CLAUDE.md`、`scripts/setup-macos.sh` 和
  `macos/diagnose.sh`，把 GitHub 链接交给 Claude Code、Codex、OpenCode、
  WorkBuddy 后即可按统一流程检查和配置。
- 修复电脑重启后额度接口刷新较慢时 Bridge 暂时无法访问的问题：服务现在会先
  立即提供最后一次画面或等待画面，再在后台刷新账户数据。
- Codex 额度读取现在可以自动发现官方 ChatGPT/Codex App 内置的 Codex，
  不再强制要求用户另外安装 CLI。
- 改善安装器的 macOS/Apple Silicon/Python 检查、错误提示和首次操作说明。
- 将 Mach-O 的真实最低部署目标固定为 macOS 14（不只是 Info.plist），因此可在
  macOS 14、15、24、25、26、27 及后续版本的 Apple Silicon Mac 上运行。

### 安装

1. 下载并解压 `CUKTECH-Screen-Controller-v0.2.1-macOS-arm64.zip`。
2. 双击 `Install CUKTECH Screen Controller.command`。
3. 如果 macOS 阻止打开，请右键安装程序并选择“打开”。
4. 第一次打开软件后跟随“新手引导”。

当前安装包适用于 Apple Silicon 与 macOS 14 或更高版本，包括 2024、2025、2026
款 Mac，以及 macOS 24、25、26 和后续版本。首次安装依赖时需要联网。

## English

- Adds an automatic first-run beginner guide with readiness checks for the
  runtime, login service, Bridge, provider apps, Wi-Fi, and AP01 requests.
- Adds beginner documentation plus agent-native `AGENTS.md`, `CLAUDE.md`,
  one-command setup, and a read-only diagnostic.
- Starts the Bridge immediately with the last-known or waiting screen while
  live account refresh continues in the background.
- Discovers Codex from the official ChatGPT/Codex app bundle as well as PATH.
- Improves installer prerequisite checks and first-run error messages.
- Sets the actual Mach-O deployment target to macOS 14 for forward-compatible
  Apple Silicon operation, rather than relying on Info.plist alone.

The package supports Apple Silicon on macOS 14 or later.
