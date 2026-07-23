#!/usr/bin/env python3
"""Request a verified AP01 first-deployment ticket from a shared FDS relay.

The relay receives only the Bridge LAN URL and refresh interval. Xiaomi account
credentials stay on the AP01 owner's computer. The returned firmware is
downloaded from Xiaomi's OTA CDN, checked byte-for-byte against the relay
metadata, and stored locally for the existing download-only/install workflow.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import stat
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests

from ap01_custom_ota import OTA_CDN_HOST
from mi_cloud import MODEL, MiCloud


API_VERSION = 1
SUPPORTED_FIRMWARE = "1.0.2_0031"
EXPECTED_FIRMWARE_SIZE = 6_804_520
MAX_FIRMWARE_SIZE = 8 * 1024 * 1024
DEFAULT_DISCOVERY_URL = (
    "https://api.github.com/gists/6e3d9ecbd917f0c1252caac1ad620978"
)


def validate_bridge_url(value: str) -> str:
    """Accept only the exact private-LAN URL understood by the AP01 loader."""

    parsed = urlsplit(value.strip())
    if parsed.scheme != "http" or parsed.username or parsed.password:
        raise ValueError("Bridge 地址必须是局域网 HTTP 地址")
    if parsed.path != "/screen.gif" or parsed.query or parsed.fragment:
        raise ValueError("Bridge 地址必须以 /screen.gif 结尾且不能包含查询参数")
    if parsed.port != 8765:
        raise ValueError("Bridge 必须使用 TCP 8765")
    try:
        address = ipaddress.ip_address(parsed.hostname or "")
    except ValueError as error:
        raise ValueError("Bridge 主机必须是局域网 IPv4 地址") from error
    if (
        address.version != 4
        or not address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_unspecified
    ):
        raise ValueError("Bridge 必须使用可由 AP01 访问的私有 IPv4 地址")
    normalized = f"http://{address}:8765/screen.gif"
    if len(normalized.encode("ascii")) + 1 > 40:
        raise ValueError("Bridge 地址超过 AP01 固件 URL 槽位长度")
    return normalized


def validate_relay_url(value: str, *, allow_local_http: bool = False) -> str:
    parsed = urlsplit(value.strip().rstrip("/"))
    local = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if parsed.scheme != "https" and not (allow_local_http and local and parsed.scheme == "http"):
        raise ValueError("共享部署服务必须使用 HTTPS")
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("共享部署服务地址无效")
    return value.strip().rstrip("/")


def resolve_relay_url(
    explicit: str | None = None,
    *,
    discovery_url: str = DEFAULT_DISCOVERY_URL,
    timeout: float = 10,
) -> str:
    configured = (explicit or os.environ.get("CUKTECH_FDS_RELAY_URL", "")).strip()
    if configured:
        return validate_relay_url(
            configured,
            allow_local_http=os.environ.get("CUKTECH_FDS_RELAY_ALLOW_HTTP") == "1",
        )

    try:
        response = requests.get(
            discovery_url,
            headers={"Accept": "application/json", "Cache-Control": "no-cache"},
            timeout=timeout,
        )
    except requests.RequestException as error:
        raise RuntimeError("无法获取共享部署服务地址，请检查网络后重试") from error
    if response.status_code != 200:
        raise RuntimeError(f"共享部署服务发现失败：HTTP {response.status_code}")
    try:
        payload = response.json()
    except (ValueError, json.JSONDecodeError) as error:
        raise RuntimeError("共享部署服务配置不是有效 JSON") from error
    if isinstance(payload, dict) and isinstance(payload.get("files"), dict):
        gist_file = payload["files"].get("cuktech-relay-service.json")
        if not isinstance(gist_file, dict) or not isinstance(gist_file.get("content"), str):
            raise RuntimeError("共享部署服务发现文件缺失")
        try:
            payload = json.loads(gist_file["content"])
        except (ValueError, json.JSONDecodeError) as error:
            raise RuntimeError("共享部署服务发现文件不是有效 JSON") from error
    if not isinstance(payload, dict):
        raise RuntimeError("共享部署服务发现配置结构无效")
    if not payload.get("enabled") or not payload.get("url"):
        raise RuntimeError("共享部署服务正在维护，请稍后重试")
    return validate_relay_url(str(payload["url"]))


def check_local_ap01() -> dict[str, Any]:
    """Read only the minimum AP01 state required before building a loader."""

    cloud = MiCloud()
    device = cloud.ap01()
    if str(device.get("model")) != MODEL:
        raise RuntimeError(f"米家账号中的设备不是受支持的 {MODEL}")
    if device.get("isOnline") is False:
        raise RuntimeError("AP01 当前离线，请先在米家中确认设备在线")
    version = str(device.get("fw_version") or "").strip()
    if not version:
        info = cloud.rpc(str(device["did"]), "miIO.info")
        result = info.get("result")
        if isinstance(result, dict):
            version = str(result.get("fw_ver") or result.get("fw_version") or "").strip()
    if version != SUPPORTED_FIRMWARE:
        shown = version or "无法读取"
        raise RuntimeError(
            f"AP01 固件为 {shown}；共享加载器只支持 {SUPPORTED_FIRMWARE}，已停止"
        )
    return {
        "model": MODEL,
        "firmware": version,
        "online": True,
        "name": str(device.get("name") or "AP01"),
    }


def _safe_json(response: requests.Response) -> dict[str, Any]:
    try:
        value = response.json()
    except (ValueError, json.JSONDecodeError) as error:
        raise RuntimeError("共享部署服务返回了无效响应") from error
    if not isinstance(value, dict):
        raise RuntimeError("共享部署服务响应结构无效")
    return value


def request_ticket(
    relay_url: str,
    bridge_url: str,
    *,
    refresh_seconds: int = 300,
    api_token: str | None = None,
    timeout: float = 600,
) -> dict[str, Any]:
    bridge_url = validate_bridge_url(bridge_url)
    if not 60 <= refresh_seconds <= 1800:
        raise ValueError("共享部署刷新间隔必须在 60 到 1800 秒之间")
    endpoint = validate_relay_url(
        relay_url,
        allow_local_http=os.environ.get("CUKTECH_FDS_RELAY_ALLOW_HTTP") == "1",
    ) + "/v1/tickets"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "CUKTECH-Screen-Controller/0.4",
    }
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"
    request_payload = {
        "api_version": API_VERSION,
        "model": MODEL,
        "firmware": SUPPORTED_FIRMWARE,
        "bridge_url": bridge_url,
        "refresh_seconds": refresh_seconds,
    }
    try:
        response = requests.post(endpoint, headers=headers, json=request_payload, timeout=timeout)
    except requests.RequestException as error:
        raise RuntimeError("无法连接共享部署服务，请检查网络后重试") from error
    payload = _safe_json(response)
    if response.status_code != 200:
        message = str(payload.get("error") or f"HTTP {response.status_code}")
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            message += f"；约 {retry_after} 秒后可重试"
        raise RuntimeError(f"共享部署失败：{message}")
    if payload.get("api_version") != API_VERSION:
        raise RuntimeError("共享部署服务协议版本不兼容")
    return validate_ticket_payload(payload, bridge_url=bridge_url, refresh_seconds=refresh_seconds)


def validate_ticket_payload(
    payload: dict[str, Any], *, bridge_url: str, refresh_seconds: int
) -> dict[str, Any]:
    firmware = payload.get("firmware")
    ticket = payload.get("ticket")
    if not isinstance(firmware, dict) or not isinstance(ticket, dict):
        raise RuntimeError("共享部署响应缺少固件或票据元数据")
    if firmware.get("model") != MODEL or firmware.get("version") != SUPPORTED_FIRMWARE:
        raise RuntimeError("共享部署服务返回了不兼容的 AP01 固件")
    if firmware.get("bridge_url") != bridge_url or firmware.get("refresh_seconds") != refresh_seconds:
        raise RuntimeError("共享部署固件配置与本机请求不一致")
    try:
        size = int(firmware["size"])
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("共享部署响应缺少有效固件大小") from error
    sha256 = str(firmware.get("sha256") or "").lower()
    md5 = str(firmware.get("md5") or "").lower()
    if size != EXPECTED_FIRMWARE_SIZE or len(sha256) != 64 or len(md5) != 32:
        raise RuntimeError("共享部署固件摘要无效")
    try:
        int(sha256, 16)
        int(md5, 16)
    except ValueError as error:
        raise RuntimeError("共享部署固件摘要不是十六进制") from error
    url = str(ticket.get("url") or "")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != OTA_CDN_HOST or not parsed.path:
        raise RuntimeError("共享部署票据不是 AP01 官方兼容 OTA CDN 地址")
    return payload


def download_firmware(payload: dict[str, Any], output: Path, *, timeout: float = 180) -> Path:
    firmware = payload["firmware"]
    url = str(payload["ticket"]["url"])
    expected_size = int(firmware["size"])
    expected_sha256 = str(firmware["sha256"]).lower()
    expected_md5 = str(firmware["md5"]).lower()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".part")
    temporary.unlink(missing_ok=True)
    sha256 = hashlib.sha256()
    md5 = hashlib.md5()
    size = 0
    header = b""
    try:
        response = requests.get(url, stream=True, timeout=timeout, allow_redirects=False)
        if response.status_code not in (200, 206):
            raise RuntimeError(f"固件下载失败：HTTP {response.status_code}")
        with temporary.open("wb") as target:
            for chunk in response.iter_content(128 * 1024):
                if not chunk:
                    continue
                if len(header) < 4:
                    header = (header + chunk)[:4]
                size += len(chunk)
                if size > MAX_FIRMWARE_SIZE:
                    raise RuntimeError("共享部署固件超过安全大小上限")
                sha256.update(chunk)
                md5.update(chunk)
                target.write(chunk)
    except requests.RequestException as error:
        temporary.unlink(missing_ok=True)
        raise RuntimeError("从小米 OTA CDN 下载固件失败") from error
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    if header != b"BFNP":
        temporary.unlink(missing_ok=True)
        raise RuntimeError("下载内容不是 AP01 BFNP 固件")
    if (
        size != expected_size
        or sha256.hexdigest().lower() != expected_sha256
        or md5.hexdigest().lower() != expected_md5
    ):
        temporary.unlink(missing_ok=True)
        raise RuntimeError("下载固件的大小或摘要与服务端签名不一致")
    os.replace(temporary, output)
    return output


def write_ticket(payload: dict[str, Any], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    temporary.write_text(str(payload["ticket"]["url"]) + "\n", encoding="utf-8")
    try:
        temporary.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    os.replace(temporary, output)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--relay-url")
    parser.add_argument("--discovery-url", default=DEFAULT_DISCOVERY_URL)
    parser.add_argument("--bridge-url", required=True)
    parser.add_argument("--refresh-seconds", type=int, default=300)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--url-output", type=Path, required=True)
    parser.add_argument("--skip-device-check", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    bridge_url = validate_bridge_url(args.bridge_url)
    if not args.skip_device_check:
        device = check_local_ap01()
        print(
            f"只读预检通过：{device['model']} · {device['firmware']} · 米家在线"
        )
    relay_url = resolve_relay_url(args.relay_url, discovery_url=args.discovery_url)
    print("正在向共享部署服务申请经过白名单验证的临时票据…")
    payload = request_ticket(
        relay_url,
        bridge_url,
        refresh_seconds=args.refresh_seconds,
        api_token=os.environ.get("CUKTECH_FDS_RELAY_TOKEN", "").strip() or None,
    )
    download_firmware(payload, args.output)
    write_ticket(payload, args.url_output)
    print(
        "共享部署包已就绪："
        f"BFNP · {payload['firmware']['size']} 字节 · "
        f"SHA-256 {str(payload['firmware']['sha256'])[:12]}…"
    )
    print("临时 OTA 链接已安全写入本机票据文件；日志未输出签名参数")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as error:
        print(f"error: {error}")
        raise SystemExit(2)
