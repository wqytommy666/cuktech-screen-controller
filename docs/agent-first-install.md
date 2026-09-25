# 新电脑 + 新 AP01：Codex / WorkBuddy 首次配置

[中文入口](../README.zh-CN.md) · [English entry](../README.md) · [Windows 登录限制](#3-米家登录与兼容性)

目标是让另一个用户从**干净的 GitHub 克隆**开始，不使用作者的电脑路径、账号、
设备 ID、IP、固件文件或已安装的 Skill。Codex 和 WorkBuddy 都可直接读取本文；
不要求它们原生支持 Codex Skill。Agent 必须有本地终端和文件读写能力。

**适用边界：**新设备不等于兼容设备。首次 Loader 仅支持
`njcuk.enstor.ap01 / 1.0.2_0031`；`0041` 或未知版本停止，不自动降级。
Windows 源码和日常显示可用，但首次 OTA 的米家登录仍需合法取得的本机凭据 JSON，
仓库尚未提供 Windows 扫码登录器。共享 FDS 服务也不是永久在线承诺。

## 0. 直接交给 Agent 的话

```text
请克隆 https://github.com/wqytommy666/cuktech-screen-controller 到本机的新目录，
阅读 AGENTS.md 和 docs/agent-first-install.md，按文档配置我的酷态科 AP01。
你负责检测系统、安装缺失依赖、配置内容与后台服务、验证兼容性及完成端到端验收。
先判断是否已经有 Loader；没有请求记录不等于没有 Loader，不要盲目重新 OTA。
我只负责必须本人完成的登录、配网、路由器地址保留及最终安装确认。
显示内容可选：我的图片、Claude+Codex、Antigravity+Codex；只问尚未明确的选择。
使用我的电脑、账号与设备信息，不复制作者的 IP、登录态或安装路径。
安装固件前先仅下载验证，写 Flash 前向我单独确认。
若不兼容、缺少 Windows 米家凭据或共享服务离线，请指出具体阻塞，不假装成功。
完成后报告本机健康、GIF 校验、真实 AP01 取图记录和登录自启状态。
```

## 1. 获取项目并判断当前状态

```sh
git clone https://github.com/wqytommy666/cuktech-screen-controller.git
cd cuktech-screen-controller
```

没有 Git 时可用 GitHub 的 **Code → Download ZIP** 并解压；不要依赖作者的绝对路径。
工作目录必须可长期保留，后台服务会引用它；不要放在下载后会自动清理的临时目录。

先读 `AGENTS.md`，再读取本次相关 Skill reference。检测系统后只运行对应诊断：

| 平台 | 首次只读诊断 | 环境准备 |
| --- | --- | --- |
| macOS | `./macos/diagnose.sh` | `./scripts/setup-macos.sh` |
| Windows PowerShell | `powershell -ExecutionPolicy Bypass -File scripts/diagnose-windows.ps1` | `powershell -ExecutionPolicy Bypass -File scripts/setup-windows.ps1 -App -NoLaunch` |

缺少 Git/Python 时让用户从官方来源安装，或在当前宿主权限允许的情况下安装。
源码需要 Python 3.9+；原生 macOS App 需要 Apple Silicon + macOS 14+；Windows App
需要 Windows 10/11 x64。首次诊断报“没有 .venv/Bridge”是待配置，不是固件故障。
Windows 的 `-NoLaunch` 只准备环境，不自动打开界面或启动 Bridge。

**已有 Loader 分支：**用户以前显示过自定义内容，或存在已确认设备 IP 的近期
`GET /screen.gif 200`，就跳过第 6、7 节。换电脑导致旧 IP 不可达时，先按
[固定 IP 指南](STABLE_IP_GUIDE.zh-CN.md)恢复原地址；不要用 OTA 代替网络诊断。

## 2. 用户配网，Agent 记录实际网络

- AP01 稳定供电，在用户自己的米家中配网并显示在线。
- 电脑与 AP01 使用同一个**可互访**的 LAN，非访客网/隔离网。
- 路由器 DHCP 为当前电脑 MAC 保留 IPv4；重连后验证仍为同一地址。
  macOS 私有 Wi-Fi 地址保持固定，不能轮换。不要关闭整体防火墙或更改他人绑定。
- VPN/代理放行 LAN；Windows 入站 TCP 8765 仅允许专用网络。
- 记录设备实际 IP、电脑实际 IP/MAC/网卡及预留结果到本机 `artifacts/`，不提交 Git。
- Loader 嵌入字面量 URL：`http://实际电脑IP:8765/screen.gif`。
  不能使用 `localhost`，不能照抄示例或作者地址。

已有图片更新只需要 LAN；额度查询需要电脑联网；首次 OTA 需要电脑和 AP01 联网。
USB 不是内容通道。电脑要保持开机、登录和联网，退出 Agent 不会自动关掉后台 Bridge。

## 3. 米家登录与兼容性

这一步只在**首次 OTA**需要。普通图片更新不需要米家令牌。

- **macOS：**用户在本机米家 App 登录。`MiCloud` 读取本人本机偏好文件；setup 可将
  登录态存入当前用户钥匙串。若系统无法安装/运行米家 App，可使用下面的本机 JSON 路径。
- **Windows：**手机米家登录不等于电脑已有凭据。当前没有内置扫码登录器；必须已具有
  用户授权取得的米家会话 JSON（`userId`、`passToken`，可选 `deviceId`）。
  文件只保存在本机，示例字段不是可用令牌，也不是账号密码。
  **如果没有合法可用的 JSON，到此明确报告“Windows 首次 OTA 登录尚未就绪”**；
  可以先把图片、Bridge、自启配置好，但不能说新屏已完成安装。不要向用户索要作者令牌，
  不要要求把令牌粘贴到聊天或 GitHub，也不要虚构自动获取方法。

选择凭据文件时，下面只填写**路径**，不要在命令中写凭据内容：

```powershell
$env:CUKTECH_MI_CREDENTIALS = "C:\Users\YOUR_USER\private\mi-credentials.json"
```

```sh
# macOS 如使用 JSON，代替默认本机米家读取
export CUKTECH_MI_CREDENTIALS="$HOME/private/mi-credentials.json"
```

后续示例以 `PY` 表示本项目解释器（不是实际命令名）：
macOS 为 `.venv/bin/python`；Windows 为 `.\.venv\Scripts\python.exe`。
Windows 下对后续单行命令用 `& $PY ...`，先设置 `$PY=".\.venv\Scripts\python.exe"`。
macOS 可设置 `PY="$PWD/.venv/bin/python"` 并用 `"$PY" ...`。

准备环境后，执行这个**只读兼容性检查**（不输出 DID/令牌）：

```sh
PY -c "from ap01_fds_relay_client import check_local_ap01; d=check_local_ap01(); print(d['model'],d['firmware'],d['online'])"
```

只有确认为 `njcuk.enstor.ap01 1.0.2_0031 True` 才继续。未知版本不猜测；多台
AP01 时先辨认用户目标，不能任选一台。若米家读取失败，先处理登录或账号区域匹配。

## 4. 内容选择与后台服务

先把电脑端做通，**这一步还不能要求未安装 Loader 的屏幕产生取图请求**。
先确认用户要显示图片、Claude+Codex，还是 Antigravity+Codex。不要为了图片模式
要求登录所有额度账户。首次传输也可用仓库公开样图测试，但必须说明样图数值是示例。

### macOS

`setup-macos.sh` 安装了登录自启。若用户选择额度：

```sh
printf 'quota\n' > artifacts/ap01-mode
# Claude+Codex 写 claude；Antigravity+Codex 写 antigravity
printf 'antigravity\n' > artifacts/ap01-quota-provider
launchctl kickstart -k gui/$(id -u)/io.github.wqytommy666.cuktech-screen-controller.bridge
```

图片模式：

```sh
.venv/bin/python ap01_prepare_screen.py /实际图片路径.png artifacts/custom-screen.gif --fit contain
printf 'custom\n' > artifacts/ap01-mode
launchctl kickstart -k gui/$(id -u)/io.github.wqytommy666.cuktech-screen-controller.bridge
```

### Windows

源码运行 Controller 与打包程序都使用 `windows.runtime.AppPaths` 确定数据目录，
通常是 `%LOCALAPPDATA%\CUKTECH Screen Controller\artifacts`。不要误把配置写入
仓库 artifacts 后启动另一个数据目录的服务。以下命令在仓库根目录执行。

额度模式（Claude+Codex 将 `antigravity` 改成 `claude`）：

```powershell
& $PY -c "from windows.runtime import AppPaths,atomic_write,enable_autostart,use_quota_mode; p=AppPaths.discover(); p.ensure(); atomic_write(p.artifacts/'ap01-quota-provider','antigravity\n'); enable_autostart(); use_quota_mode(p)"
```

图片模式：

```powershell
& $PY -c "import sys; from pathlib import Path; from windows.runtime import AppPaths,enable_autostart,convert_custom_image; p=AppPaths.discover(); enable_autostart(); print(convert_custom_image(p,Path(sys.argv[1]),'contain'))" "C:\实际图片路径.png"
```

可打开界面：`& .\.venv\Scripts\pythonw.exe windows\AP01ScreenController.py`。
不要同时启动两个占用 8765 的 Bridge。

### 额度账户

Claude：用户登录官方 Claude Desktop；Codex：用户登录官方 Codex App/CLI。
Antigravity 使用已登录的官方 `agy`，查询 `agy -p /usage --output-format json`。
Codex/WorkBuddy 是操作 Agent，并不意味着它们的聊天登录就能提供所有这些额度。
详见[Antigravity 中英文说明](ANTIGRAVITY_QUOTA.md)。首次图可在一个账号失败时显示
另一账号；交付要报告 `partial`，不能把缺失窗口写成 100%。

## 5. 电脑端验收（安装前）

```sh
PY -c "import json,urllib.request; o=urllib.request.build_opener(urllib.request.ProxyHandler({})); print(json.load(o.open('http://127.0.0.1:8765/health',timeout=3)))"
```

额度模式 `live` 才表示全部额度获取成功，`partial` 表示部分失败；`/health` 有响应只说明
HTTP 服务存在，不证明屏幕连上。图片模式按其返回的 `ok`/文件信息检查。
验证 `/screen.gif` 为 GIF89a、320×240、至少 2 帧，目标 <90 KB；母版不是设备图片。
用同一 LAN 的另一台设备访问电脑的 GIF，检查入站链路，不能只做 localhost 测试。

## 6. 获取首次部署包：普通用户优先共享 Relay

**不需要用户购买网关，也不需要安装 RISC-V 编译器。**共享服务负责从固定 hash 的
0031 镜像生成配置包。不要把“本地安装”误解成“必须本地编译固件”。

在已通过第 3、5 节后执行以下**单行**命令，替换 `PY` 和电脑实际 IP：

```sh
PY ap01_fds_relay_client.py --bridge-url http://实际电脑IP:8765/screen.gif --refresh-seconds 300 --output artifacts/screen-realtime.bin --url-output artifacts/ap01-ota-url.txt
```

不要加 `--skip-device-check`。客户端自行读取当前服务发现地址，不复制旧的
`trycloudflare.com` 域名。它只上传 LAN URL、刷新间隔及固定型号版本，不上传登录态。
成功后应通过 BFNP、大小、SHA-256/MD5 与 CDN 主机校验；票据只存本机文件。

服务离线或心跳过期：报告实际失败与时间，不编造 ETA，不无限重试或自动创建监控。
可等待恢复，或让用户明确选择[可信自建 Relay/网关运维路径](FDS_RELAY_OPERATOR.md)。
没有共享服务、没有兼容固件来源/编译工具和有效 FDS 上传身份时，**首次 OTA 被阻塞**。
不能假造 DID/model/bucket，也不能把 AP01 本身当作 FDS 网关。

## 7. 先仅下载，再由本人确认安装

同一个 BIN、同一个有效票据文件，先执行：

```sh
PY ap01_install_firmware.py artifacts/screen-realtime.bin --download-only --ota-url-file artifacts/ap01-ota-url.txt --timeout 360
```

这个步骤验证设备下载，不是安装成功。失败先处理网络/票据/兼容性，不自动转 `--install`。
票据过期回到第 6 节重新获取并验证；不要手工修改签名链接。

**停在这里向用户确认：目标为其 AP01/0031，已确认固定的电脑 URL，下载验证通过，
下一步将写入一次固件 Flash 并重启。必须收到这一步的明确同意后才执行：**

```sh
PY ap01_install_firmware.py artifacts/screen-realtime.bin --install --ota-url-file artifacts/ap01-ota-url.txt --timeout 360
```

不能把整段流程包成无人确认的自动安装脚本。安装后保持供电，等待设备重启；
让用户切到电子宠物/虚拟形象页面。未收到请求时先看网络/IP/页面，不连续重刷。

## 8. 最终验收和交付

记录到本机 `artifacts/first-install-report.md`（不提交 Git）：

- OS、仓库 commit、内容来源、实际数据目录；
- AP01 型号/版本、电脑稳定 IPv4 与 DHCP 保留结果；
- `/health` 与额度时间（没有令牌）；GIF 尺寸、帧数、字节数；
- **在最新图片生成之后**，来自已确认 AP01 IP 的 `GET /screen.gif ... 200` 及时间；
  不得用浏览器、localhost 或其他设备的请求冒充 AP01。
- macOS LaunchAgent 或 Windows Startup 已启用；重启 Bridge 后仍正常。
  检查最近两次 AP01 请求约 300 秒间隔；默认应在 10 分钟内出现，超时继续诊断。
- 用户确认实物画面；若未观察到，注明“设备下载已验证，实物视觉待用户确认”。
- 以后换图/改额度走 RAM，不重新 OTA；电脑地址和数据目录不要随意改变。

**完成层级必须分开：**环境就绪 ≠ Bridge 就绪 ≠ 固件已下载 ≠ Loader 已安装
≠ 屏幕已取到图。遇到登录、版本或上游服务阻塞，报告已完成阶段与真正下一步。

## English summary

Give Codex or WorkBuddy the repository URL and ask it to read `AGENTS.md` plus
this guide. No preinstalled Skill, maintainer credentials, private firmware,
fixed author IP, or local absolute path is required. A terminal-capable agent
clones the repository, detects the OS, prepares the platform runtime, configures
content and login startup, verifies the owner's device and DHCP reservation,
and uses the shared relay for a per-LAN loader. `download-only` comes first;
explicit user confirmation immediately precedes `--install`. Do not flash an
existing loader merely because requests disappeared after changing computers.

Support is limited to `njcuk.enstor.ap01 / 1.0.2_0031`. Version 0041 and unknown
versions stop. Windows source startup is supported, but a first OTA currently
requires an owner-provided local Mi Home credential JSON; no Windows QR-login
helper is bundled. If credentials or the shared relay are unavailable, report
the precise blocker instead of promising a fully automatic clean-device install.
A source/runtime smoke test is not evidence of a fresh physical-device flash.
The acceptance checklist above requires a fresh AP01-originated HTTP 200 image
request and autostart, not just a healthy localhost endpoint.
