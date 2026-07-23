#!/usr/bin/env python3
"""Restricted FDS ticket relay for gateway-free CUKTECH AP01 onboarding.

This service never accepts firmware uploads and never receives an AP01 owner's
Xiaomi credentials. It builds only the reviewed 1.0.2_0031 loader from an
operator-owned, hash-pinned stock image, uploads it with the operator's
FDS-capable gateway identity, and returns a short-lived Xiaomi OTA CDN ticket.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import hmac
import ipaddress
import json
import os
import re
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from PIL import Image, ImageDraw

from ap01_custom_ota import build_firmware as build_compat_firmware
from ap01_custom_ota import upload_to_xiaomi
from ap01_fds_relay_client import (
    API_VERSION,
    EXPECTED_FIRMWARE_SIZE,
    SUPPORTED_FIRMWARE,
    validate_bridge_url,
)
from ap01_realtime_patch import (
    PAYLOAD_LINKER,
    PAYLOAD_SOURCE,
    build_firmware as build_realtime_firmware,
)
from mi_cloud import MODEL, MiCloud


SUPPORTED_STOCK_SHA256 = "8a721fc8ef25458d415b2460e4a251e0503a82f7743fdff85b12612190e5c1cb"
MAX_REQUEST_BYTES = 4096
URL_RE = re.compile(r"https?://[^\s]+")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def redact_urls(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        raw = match.group(0)
        return raw.split("?", 1)[0] + ("?••••" if "?" in raw else "")

    return URL_RE.sub(replace, value)


def build_fallback_gif(output: Path) -> Path:
    """Create a tiny deterministic two-frame compatibility screen."""

    frames: list[Image.Image] = []
    for bright in (False, True):
        image = Image.new("RGB", (320, 240), "#01040B")
        draw = ImageDraw.Draw(image)
        accent = "#22D3EE" if bright else "#0EA5E9"
        draw.rounded_rectangle((20, 50, 300, 205), radius=24, fill="#071426", outline=accent, width=3)
        draw.ellipse((43, 80, 93, 130), outline=accent, width=5)
        draw.line((55, 105, 80, 105), fill=accent, width=5)
        draw.text((112, 80), "CUKTECH", fill="#F8FAFC", stroke_width=1)
        draw.text((112, 112), "CONTROLLER READY", fill=accent)
        draw.text((50, 164), "Waiting for /screen.gif", fill="#94A3B8")
        frames.append(image)
    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=[900, 900],
        loop=0,
        optimize=True,
    )
    data = output.read_bytes()
    if data[:6] != b"GIF89a" or len(data) > 90_000:
        raise RuntimeError("generated fallback GIF failed validation")
    return output


@dataclass(frozen=True)
class TicketRequest:
    bridge_url: str
    refresh_seconds: int

    @classmethod
    def parse(cls, payload: dict[str, Any]) -> "TicketRequest":
        if payload.get("api_version") != API_VERSION:
            raise ValueError("客户端协议版本不兼容")
        if payload.get("model") != MODEL or payload.get("firmware") != SUPPORTED_FIRMWARE:
            raise ValueError("只支持 njcuk.enstor.ap01 固件 1.0.2_0031")
        bridge_url = validate_bridge_url(str(payload.get("bridge_url") or ""))
        try:
            refresh = int(payload.get("refresh_seconds", 300))
        except (TypeError, ValueError) as error:
            raise ValueError("刷新间隔无效") from error
        if not 60 <= refresh <= 1800:
            raise ValueError("刷新间隔必须在 60 到 1800 秒之间")
        allowed = {
            "api_version",
            "model",
            "firmware",
            "bridge_url",
            "refresh_seconds",
        }
        if set(payload) - allowed:
            raise ValueError("请求包含未允许的字段")
        return cls(bridge_url=bridge_url, refresh_seconds=refresh)


class RateLimiter:
    def __init__(
        self,
        *,
        per_client: int = 3,
        per_client_window: int = 3600,
        global_limit: int = 40,
        global_window: int = 86400,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.per_client = per_client
        self.per_client_window = per_client_window
        self.global_limit = global_limit
        self.global_window = global_window
        self.clock = clock
        self.clients: dict[str, collections.deque[float]] = {}
        self.global_events: collections.deque[float] = collections.deque()
        self.lock = threading.Lock()

    @staticmethod
    def _trim(events: collections.deque[float], cutoff: float) -> None:
        while events and events[0] <= cutoff:
            events.popleft()

    def acquire(self, client: str) -> tuple[bool, int]:
        with self.lock:
            now = self.clock()
            events = self.clients.setdefault(client, collections.deque())
            self._trim(events, now - self.per_client_window)
            self._trim(self.global_events, now - self.global_window)
            waits: list[float] = []
            if len(events) >= self.per_client:
                waits.append(events[0] + self.per_client_window - now)
            if len(self.global_events) >= self.global_limit:
                waits.append(self.global_events[0] + self.global_window - now)
            if waits:
                return False, max(1, int(max(waits)) + 1)
            events.append(now)
            self.global_events.append(now)
            return True, 0


class RelayBuilder:
    def __init__(
        self,
        stock_firmware: Path,
        cache_dir: Path,
        *,
        fds_did: str | None = None,
        fds_model: str | None = None,
        tool_prefix: str = "riscv64-elf-",
    ) -> None:
        self.stock_firmware = stock_firmware.resolve()
        self.cache_dir = cache_dir.resolve()
        self.fds_did = fds_did
        self.fds_model = fds_model
        self.tool_prefix = tool_prefix
        if bool(fds_did) != bool(fds_model):
            raise ValueError("FDS DID 与 Model 必须同时配置")
        if not self.stock_firmware.is_file():
            raise FileNotFoundError(f"stock firmware not found: {self.stock_firmware}")
        if sha256_file(self.stock_firmware) != SUPPORTED_STOCK_SHA256:
            raise RuntimeError("stock firmware SHA-256 is not the reviewed AP01 1.0.2_0031 image")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.cache_dir.chmod(0o700)
        except OSError:
            pass
        build_material = (
            PAYLOAD_SOURCE.read_bytes()
            + PAYLOAD_LINKER.read_bytes()
            + SUPPORTED_STOCK_SHA256.encode("ascii")
            + b"relay-v1"
        )
        self.build_id = hashlib.sha256(build_material).hexdigest()[:16]
        self.lock = threading.Lock()

    def _cache_key(self, request: TicketRequest) -> str:
        material = json.dumps(
            {
                "build": self.build_id,
                "url": request.bridge_url,
                "refresh": request.refresh_seconds,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(material).hexdigest()

    def _cached_firmware(self, request: TicketRequest) -> tuple[Path, dict[str, Any]] | None:
        root = self.cache_dir / self._cache_key(request)
        firmware = root / "screen-realtime.bin"
        metadata = root / "metadata.json"
        try:
            payload = json.loads(metadata.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return None
        if (
            payload.get("build_id") != self.build_id
            or payload.get("bridge_url") != request.bridge_url
            or payload.get("refresh_seconds") != request.refresh_seconds
            or not firmware.is_file()
            or firmware.stat().st_size != EXPECTED_FIRMWARE_SIZE
            or sha256_file(firmware) != payload.get("sha256")
        ):
            shutil.rmtree(root, ignore_errors=True)
            return None
        return firmware, payload

    def _build(self, request: TicketRequest) -> tuple[Path, dict[str, Any]]:
        cached = self._cached_firmware(request)
        if cached:
            return cached
        destination = self.cache_dir / self._cache_key(request)
        with tempfile.TemporaryDirectory(prefix="ap01-relay-", dir=self.cache_dir) as temporary_name:
            temporary = Path(temporary_name)
            fallback = build_fallback_gif(temporary / "fallback.gif")
            compat = temporary / "screen-compat.bin"
            realtime = temporary / "screen-realtime.bin"
            build_dir = temporary / "realtime-build"
            build_compat_firmware(self.stock_firmware, fallback, compat)
            manifest = build_realtime_firmware(
                compat,
                realtime,
                build_dir,
                url=request.bridge_url,
                refresh_seconds=request.refresh_seconds,
                tool_prefix=self.tool_prefix,
            )
            sha256 = sha256_file(realtime)
            md5 = md5_file(realtime)
            if (
                realtime.stat().st_size != EXPECTED_FIRMWARE_SIZE
                or realtime.read_bytes()[:4] != b"BFNP"
                or manifest.get("output_sha256") != sha256
                or manifest.get("output_md5") != md5
                or manifest.get("url") != request.bridge_url
                or manifest.get("refresh_seconds") != request.refresh_seconds
            ):
                raise RuntimeError("locally built firmware failed relay validation")
            metadata: dict[str, Any] = {
                "build_id": self.build_id,
                "bridge_url": request.bridge_url,
                "refresh_seconds": request.refresh_seconds,
                "size": realtime.stat().st_size,
                "sha256": sha256,
                "md5": md5,
            }
            staged = temporary / "cache"
            staged.mkdir()
            shutil.copy2(realtime, staged / "screen-realtime.bin")
            (staged / "metadata.json").write_text(
                json.dumps(metadata, sort_keys=True, indent=2) + "\n", encoding="utf-8"
            )
            if destination.exists():
                shutil.rmtree(destination)
            os.replace(staged, destination)
        return destination / "screen-realtime.bin", metadata

    def create_ticket(self, request: TicketRequest) -> dict[str, Any]:
        with self.lock:
            firmware, metadata = self._build(request)
            cloud = MiCloud()
            ota_url = upload_to_xiaomi(
                cloud,
                firmware,
                fds_did=self.fds_did,
                fds_model=self.fds_model,
            )
        return {
            "api_version": API_VERSION,
            "generated_at": int(time.time()),
            "firmware": {
                "model": MODEL,
                "version": SUPPORTED_FIRMWARE,
                "bridge_url": request.bridge_url,
                "refresh_seconds": request.refresh_seconds,
                "size": metadata["size"],
                "sha256": metadata["sha256"],
                "md5": metadata["md5"],
            },
            "ticket": {"url": ota_url},
        }


class RelayHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        builder: RelayBuilder,
        *,
        limiter: RateLimiter,
        api_token: str | None,
        trust_proxy: bool,
    ) -> None:
        super().__init__(address, RelayHandler)
        self.builder = builder
        self.limiter = limiter
        self.api_token = api_token
        self.trust_proxy = trust_proxy


class RelayHandler(BaseHTTPRequestHandler):
    server: RelayHTTPServer
    protocol_version = "HTTP/1.1"

    def _client_key(self) -> str:
        if self.server.trust_proxy:
            forwarded = self.headers.get("CF-Connecting-IP", "").strip()
            try:
                return str(ipaddress.ip_address(forwarded))
            except ValueError:
                pass
        return self.client_address[0]

    def _json(
        self,
        status: HTTPStatus,
        payload: dict[str, Any],
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        expected = self.server.api_token
        if not expected:
            return True
        supplied = self.headers.get("Authorization", "")
        return hmac.compare_digest(supplied, f"Bearer {expected}")

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "service": "cuktech-ap01-fds-relay",
                    "api_version": API_VERSION,
                    "model": MODEL,
                    "firmware": SUPPORTED_FIRMWARE,
                },
            )
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/tickets":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        if not self._authorized():
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "未授权的共享部署请求"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if not 0 < length <= MAX_REQUEST_BYTES:
            self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "请求大小无效"})
            return
        allowed, retry = self.server.limiter.acquire(self._client_key())
        if not allowed:
            self._json(
                HTTPStatus.TOO_MANY_REQUESTS,
                {"error": "申请过于频繁"},
                extra_headers={"Retry-After": str(retry)},
            )
            return
        try:
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("请求必须是 JSON 对象")
            request = TicketRequest.parse(payload)
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        fingerprint = hashlib.sha256(
            f"{request.bridge_url}|{request.refresh_seconds}".encode("utf-8")
        ).hexdigest()[:12]
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ticket request {fingerprint}", flush=True)
        try:
            result = self.server.builder.create_ticket(request)
        except Exception as error:
            print(f"relay error {fingerprint}: {redact_urls(str(error))}", flush=True)
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "服务端构建或上传失败"})
            return
        print(f"ticket ready {fingerprint}", flush=True)
        self._json(HTTPStatus.OK, result)

    def log_message(self, fmt: str, *args: object) -> None:
        # Avoid BaseHTTPRequestHandler logs containing paths or future query data.
        print(f"http {self.client_address[0]} {fmt % args}", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stock-firmware",
        type=Path,
        default=Path(os.environ.get("CUKTECH_FDS_RELAY_STOCK", "")).expanduser(),
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path.home() / "Library/Caches/CUKTECH Screen Controller/fds-relay",
    )
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8790)
    parser.add_argument("--fds-did", default=os.environ.get("CUKTECH_FDS_RELAY_GATEWAY_DID"))
    parser.add_argument("--fds-model", default=os.environ.get("CUKTECH_FDS_RELAY_GATEWAY_MODEL"))
    parser.add_argument("--tool-prefix", default="riscv64-elf-")
    parser.add_argument("--trust-proxy", action="store_true")
    parser.add_argument("--allow-public", action="store_true")
    parser.add_argument("--per-client-hour", type=int, default=3)
    parser.add_argument("--global-day", type=int, default=40)
    args = parser.parse_args(argv)

    stock_value = str(args.stock_firmware)
    if not stock_value or stock_value == ".":
        parser.error("--stock-firmware or CUKTECH_FDS_RELAY_STOCK is required")
    try:
        bind_address = ipaddress.ip_address(args.bind)
    except ValueError:
        bind_address = None
    is_loopback = bool(bind_address and bind_address.is_loopback)
    api_token = os.environ.get("CUKTECH_FDS_RELAY_TOKEN", "").strip() or None
    if not is_loopback and not api_token and not args.allow_public:
        parser.error("non-loopback bind requires CUKTECH_FDS_RELAY_TOKEN or --allow-public")
    if args.per_client_hour < 1 or args.global_day < 1:
        parser.error("rate limits must be positive")

    builder = RelayBuilder(
        args.stock_firmware,
        args.cache_dir,
        fds_did=args.fds_did,
        fds_model=args.fds_model,
        tool_prefix=args.tool_prefix,
    )
    limiter = RateLimiter(
        per_client=args.per_client_hour,
        global_limit=args.global_day,
    )
    server = RelayHTTPServer(
        (args.bind, args.port),
        builder,
        limiter=limiter,
        api_token=api_token,
        trust_proxy=args.trust_proxy,
    )
    print(
        f"CUKTECH FDS relay listening on http://{args.bind}:{args.port} · "
        f"build {builder.build_id} · signed URLs are never logged",
        flush=True,
    )
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {redact_urls(str(error))}")
        raise SystemExit(2)
