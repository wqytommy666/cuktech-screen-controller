# CUKTECH Screen Controller 零基础使用教程

这份教程写给完全没有编程基础的用户。正常使用时不需要写代码，也不需要每次刷固件。

## 先判断你属于哪一种情况

### 情况 A：万向屏已经显示过自定义画面或 Claude/Codex 额度

说明实时加载器已经安装完成。你只需要安装软件，之后换图片、换 GIF、刷新额度都通过
Wi-Fi 写入屏幕的临时内存，不会反复刷 Flash。

### 情况 B：万向屏还是完全原厂状态，从未显示过电脑发送的画面

需要先完成一次实时加载器安装。这个步骤对型号和固件版本有严格要求，建议使用本文
后面的“交给 Coding Agent”方法。完成一次后，日常操作就全部使用软件。

## 安装前准备清单

请提前准备好：

- Apple Silicon Mac（包括 2024、2025、2026 款），系统为 macOS 14 或更高版本；
- macOS 24、25、26 以及后续版本都可以使用；
- 酷态科 10 号充电站与 AP01 万向屏；
- Mac 和 AP01 连接同一个 Wi-Fi，不能使用访客网络；
- 需要显示额度时，提前安装并登录 Claude Desktop 和官方 Codex/ChatGPT App；
- 首次安装软件时保持网络连接；
- 最好在路由器中为 Mac 固定局域网 IP，避免以后地址变化。

## 方法一：直接安装软件（最简单）

### 第 1 步：下载安装包

打开 [GitHub Releases](https://github.com/wqytommy666/cuktech-screen-controller/releases/latest)，
下载名字类似下面的文件：

```text
CUKTECH-Screen-Controller-v0.2.x-macOS-arm64.zip
```

### 第 2 步：运行安装程序

1. 双击 ZIP 解压；
2. 打开解压后的文件夹；
3. 双击 `Install CUKTECH Screen Controller.command`；
4. 如果 macOS 阻止打开，请右键该文件，选择“打开”，再确认一次；
5. 等待终端显示“安装完成”，软件会自动打开。

如果提示没有 Python 3，安装程序会打开 Python 下载页面。安装 Python 后，再双击一次
安装程序即可。

### 第 3 步：跟着软件里的“新手引导”检查

第一次打开软件会自动显示新手引导，也可以点击窗口右上角的“新手引导”。确认：

- 运行环境：已就绪；
- 后台服务：运行中；
- Claude：已登录（只显示自定义图片时可以忽略）；
- Codex：已登录（只显示自定义图片时可以忽略）；
- AP01 请求：最近出现过 `GET /screen.gif 200`。

### 第 4 步：选择显示内容

#### 显示 Claude / Codex 额度

点击“显示 Claude / Codex 额度”。软件每 5 分钟获取一次最新数据。第一次读取 Claude
登录状态时，macOS 可能询问是否允许访问“Claude Safe Storage”，请选择“允许”或
“始终允许”。

#### 显示自己的图片或 GIF

1. 选择“完整显示”“铺满裁切”或“拉伸”；
2. 点击“选择图片并推送”；
3. 选择 PNG、JPG、HEIC、WebP 或动态 GIF；
4. 等待提示“已切换为自定义画面”。

AP01 通常会在下一次轮询时更新，默认最长约 5 分钟。

## 方法二：把 GitHub 链接交给 Coding Agent

这种方法适合全新电脑、原厂屏幕首次配置或出现故障时。可以使用 Claude Code、Codex、
OpenCode、WorkBuddy 等能够读取 GitHub 并执行终端命令的软件。

把下面整段话复制给它：

```text
请使用这个公开仓库帮我配置酷态科 AP01 万向屏：
https://github.com/wqytommy666/cuktech-screen-controller

开始前先阅读仓库根目录的 AGENTS.md、README.zh-CN.md 和
skills/cuktech-ap01-screen-kit/SKILL.md。先运行只读诊断，不要直接刷固件。

我没有编程基础，请一次只告诉我一个需要人工完成的动作，并解释我应该看到什么。
请检查 Mac、Python、Claude/Codex 登录、局域网、Bridge 和 AP01 请求记录。
如果设备已经请求 GET /screen.gif，就不要进行 OTA，直接完成软件和自动启动配置。
只有确认设备仍为原厂、型号为 njcuk.enstor.ap01、固件为 1.0.2_0031 时，才准备
一次性实时加载器；真正安装前必须再次向我确认。日常图片和额度刷新只使用 /tmp RAM。

完成后请给我展示：
1. /health 的结果；
2. screen.gif 为 320×240 GIF89a；
3. 日志中的 AP01 GET /screen.gif 200；
4. 登录后自动启动已经开启。
```

Agent 会自动识别 `AGENTS.md`/`CLAUDE.md`，运行一键配置脚本，并在需要你登录、选择
图片或确认一次性安装时暂停。

## 常见问题

### 软件显示“服务未运行”

点击“重启并立即刷新”。如果仍未恢复，在“新手引导”中运行检查，或把下面这句话交给
Coding Agent：

```text
请在 cuktech-screen-controller 仓库中运行 ./macos/diagnose.sh，修复 Bridge，
但不要执行 OTA。
```

### 软件运行，但额度不更新

- 重新打开并登录 Claude Desktop、Codex/ChatGPT App；
- Claude 第一次读取可能需要钥匙串授权；
- 检查代理/VPN是否能访问 Claude；
- 软件会保留上一次成功画面，网络恢复后自动重试。

### 电脑重启后屏幕不更新

软件安装器会创建登录自动启动服务。Mac 必须已经登录用户账户、保持开机，并与 AP01
处于同一 Wi-Fi。睡眠或关机期间屏幕保留最后一次成功画面。

### 屏幕一直没有请求

确认不是访客 Wi-Fi，关闭路由器的 AP/客户端隔离，并固定 Mac 的局域网 IP。如果这块
屏幕从未安装实时加载器，请使用“方法二”完成一次性配置。

### 会不会把 Flash 刷坏？

日常图片、GIF 和额度刷新只写入 `/tmp/.ap01q*.gif` RAM 槽位，不写固件分区。只有
原厂设备首次安装实时加载器时写入一次 Flash。
