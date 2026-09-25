# Antigravity + Codex 额度 / Quota dashboard

## 简体中文

本功能将上方的 Claude Desktop 卡片替换为 **Google Antigravity**，下方保留
Codex。不是 Gemini CLI 额度，也不是 Claude Max 额度。旧版本默认仍使用
Claude + Codex，不会因为升级源码自动切换账号来源。

### 数据从哪里来

使用已经登录的官方 Antigravity CLI：

```sh
agy -p /usage --output-format json
```

这是查询命令，不发送模型任务。桥接程序只解析成功的 `usage` 结构化数据，
显示「Gemini」及「Claude/GPT」两组的 **5 小时和本周剩余百分比**。
每组独立显示官方返回的重置时间（电脑本地时区）。`/usage` 不提供套餐身份，
因此不把它标成 Google Ultra、Claude Max 或其他猜测的套餐。

- 先安装官方 `agy` 并完成登录；使用支持结构化 `/usage` 的版本，macOS 已实测 `1.2.5`。
- 查找 PATH 和 `~/.local/bin/agy`；非标准路径使用 `CUKTECH_AGY_BIN`。
- 在临时空目录执行，只查询额度，不读取你的项目内容。
- 90 秒超时、1 MiB 输出上限；错误消息不携带原始命令输出或令牌。
- 未返回或禁用的窗口显示 `—`，不会假造为 100%。
- 某个账号查询失败时另一个账号仍可显示；整体数据过期后进入未连接画面。

### 启动或切换

在源码项目目录中运行（先停止占用 8765 的旧 Bridge）：

```sh
# macOS
.venv/bin/python -u ap01_wifi_bridge.py --quota-provider antigravity --interval 300
```

```powershell
# Windows 源码环境；当前版本的官方 agy 必须已安装并登录
.\.venv\Scripts\python.exe -u ap01_wifi_bridge.py --quota-provider antigravity --interval 300
```

后台服务持久化配置：在 Bridge 的 `artifacts/ap01-quota-provider` 文件中写入
一行 `antigravity`，然后重启 Bridge。写回 `claude` 即可恢复。
也可设置 `CUKTECH_QUOTA_PROVIDER=antigravity`；优先级是命令行、环境变量、
配置文件、默认 Claude。Windows 打包应用的 artifacts 通常位于
`%LOCALAPPDATA%\CUKTECH Screen Controller\artifacts`；已发布的旧安装包
需要先更新到包含该功能的代码，单独新增配置文件不会给旧代码增加支持。
桌面控制器旧版按钮可能仍写着 Claude/Codex，实际来源以 `/health` 的
`quota_provider` 和预览图为准。

### 验证

```sh
curl --noproxy '*' http://127.0.0.1:8765/health
curl --noproxy '*' http://127.0.0.1:8765/api/v1/quota
```

健康结果应有 `quota_provider: "antigravity"`；数据返回 `antigravity.groups`
和 `codex`，不把 Antigravity 冒充为 `claude`。最后检查 AP01 IP 的
`GET /screen.gif ... 200`，本地预览成功不代表屏幕已经收到。

设计母版 1280×960，设备图片 320×240 GIF89a、4 帧、目标小于 90 KB。
顶部 40 行保留时钟/日期，约每 5 分钟刷新。已有 Loader 的更新只替换 RAM
图片，**不需要 OTA，不因刷新额度写入固件 Flash**。Windows 的解析、配置与
子进程路径复用跨平台实现；本次实机验证为 macOS，不宣称已做 Windows 实机测试。

## English

Select **Google Antigravity**, not Gemini CLI or a standalone Claude Max
subscription, as the first card. Codex remains the second card. The existing
Claude default is preserved for other users.

The collector invokes the signed-in official `agy -p /usage --output-format json`
metacommand in an empty temporary directory. It parses only successful,
structured usage reports: Gemini and Claude/GPT each have a five-hour and weekly
pool. Values are **remaining** percentages; reset timestamps use the host's
local timezone. Missing/disabled data stays unknown. The command does not
identify a plan, so no paid tier is invented. Authentication stays with `agy`;
raw output and credentials are not persisted. Collection is bounded to 90 seconds
and 1 MiB.

Use `ap01_wifi_bridge.py --quota-provider antigravity --interval 300`, or persist
`antigravity` in the runtime's `artifacts/ap01-quota-provider` file and restart
the Bridge. `CUKTECH_QUOTA_PROVIDER` overrides that file; the CLI flag overrides
both. `CUKTECH_AGY_BIN` selects a nonstandard official CLI installation. An old
released package must be updated before this option works. Its legacy desktop
button may still say Claude/Codex; the preview and `/health.quota_provider`
identify the actual source.

`/api/v1/quota` exposes `antigravity.groups` plus `codex`. Validate a fresh AP01
`GET /screen.gif 200`, not just local health. The 320×240 four-frame GIF preserves
the top clock band and the seven-minute offline fallback. Existing realtime
Loaders update RAM images, not firmware Flash. macOS with `agy 1.2.5` was tested
live; the shared Python implementation is portable but no Windows device test
is claimed here.

Implementation reference: [CodexBar Antigravity provider](https://github.com/steipete/CodexBar/blob/main/docs/antigravity.md).
