# CUKTECH Screen Controller 0.4.0

## 中文

### 无网关首次部署

- macOS 与 Windows 新增“无网关：一键获取部署包”；
- 用户无需购买米家网关，也无需选择或传递固件 BIN；
- 本机先确认 `njcuk.enstor.ap01 / 1.0.2_0031` 与米家在线状态；
- 从受限共享 Relay 获取小米 FDS 临时票据和固件摘要；
- 客户端验证 BFNP、固定大小、SHA-256、MD5 与 OTA CDN 主机；
- 先执行 `download-only`，真正安装前单独弹窗再次确认；
- 安装一次后，所有画面更新仍只使用局域网 `/tmp` RAM。

### Relay 安全边界

- 不接受任意固件上传；
- 只从 SHA-256 固定的 AP01 `1.0.2_0031` 原厂镜像构建；
- 只允许私有 IPv4 `http://IP:8765/screen.gif`；
- 用户米家凭据、AP01 DID、Claude/Codex 登录态不会发送到 Relay；
- 签名 URL 自动脱敏，并启用来源/全局限流。

安装包：

- `CUKTECH-Screen-Controller-v0.4.0-macOS-arm64.zip`
- `CUKTECH-Screen-Controller-0.4.0-Windows-x64.zip`

## English

Version 0.4 adds restricted gateway-free onboarding to both desktop apps. A
stock AP01 owner no longer needs to buy a Xiaomi gateway or prepare a firmware
file. The app performs local Mi Home compatibility checks, obtains a verified
package and short-lived FDS ticket, validates BFNP/size/SHA-256/MD5, performs a
download-only device test, and asks again immediately before installation.

The relay never accepts arbitrary firmware or user Xiaomi credentials. It
builds only from the hash-pinned AP01 `1.0.2_0031` source and accepts only a
private-LAN Bridge URL plus refresh interval. Daily screen updates remain
LAN-only and RAM-backed after the one-time loader installation.
