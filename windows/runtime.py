"""Platform services shared by the Windows UI and its background Bridge."""

from __future__ import annotations

import contextlib
import json
import os
import platform
import signal
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


APP_NAME = "CUKTECH Screen Controller"
STARTUP_FILE = "CUKTECH Screen Controller Bridge.vbs"
HEALTH_URL = "http://127.0.0.1:8765/health"


def _source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resource_root() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    return Path(frozen_root) if frozen_root else _source_root()


def default_data_root() -> Path:
    override = os.environ.get("CUKTECH_DATA_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt" or getattr(sys, "frozen", False):
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        return local / APP_NAME
    return _source_root()


@dataclass(frozen=True)
class AppPaths:
    root: Path
    data_root: Path
    artifacts: Path
    mode_file: Path
    custom_gif: Path
    quota_gif: Path
    quota_png: Path
    log_file: Path
    error_log: Path
    pid_file: Path
    lock_file: Path
    ota_url_file: Path
    gateway_free_firmware: Path

    @classmethod
    def discover(cls, data_root: Path | None = None) -> "AppPaths":
        root = resource_root()
        data = (data_root or default_data_root()).resolve()
        artifacts = data / "artifacts"
        return cls(
            root=root,
            data_root=data,
            artifacts=artifacts,
            mode_file=artifacts / "ap01-mode",
            custom_gif=artifacts / "custom-screen.gif",
            quota_gif=artifacts / "quota-dashboard.gif",
            quota_png=artifacts / "quota-dashboard.png",
            log_file=artifacts / "ap01_windows.log",
            error_log=artifacts / "ap01_windows.error.log",
            pid_file=artifacts / "ap01_windows.pid",
            lock_file=artifacts / "ap01_windows.lock",
            ota_url_file=artifacts / "ap01-ota-url.txt",
            gateway_free_firmware=artifacts / "ap01-gateway-free-realtime.bin",
        )

    def ensure(self) -> None:
        self.artifacts.mkdir(parents=True, exist_ok=True)
        if not self.mode_file.exists():
            atomic_write(self.mode_file, "quota\n")


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def current_mode(paths: AppPaths) -> str:
    try:
        value = paths.mode_file.read_text(encoding="utf-8").strip().lower()
    except OSError:
        return "quota"
    return "custom" if value == "custom" else "quota"


def self_command(*arguments: str) -> list[str]:
    """Return the frozen executable or source command for a helper mode."""

    launcher = os.environ.get("CUKTECH_LAUNCHER_EXE", "").strip()
    if os.name == "nt" and launcher and Path(launcher).exists():
        return [launcher, *arguments]
    if getattr(sys, "frozen", False):
        return [sys.executable, *arguments]
    executable = Path(sys.executable)
    if os.name == "nt":
        pythonw = executable.with_name("pythonw.exe")
        if pythonw.exists():
            executable = pythonw
    return [str(executable), str(_source_root() / "windows/AP01ScreenController.py"), *arguments]


def _process_creation_options() -> dict[str, Any]:
    if os.name == "nt":
        flags = 0
        for name in ("CREATE_NEW_PROCESS_GROUP", "DETACHED_PROCESS", "CREATE_NO_WINDOW"):
            flags |= int(getattr(subprocess, name, 0))
        return {"creationflags": flags}
    return {"start_new_session": True}


def health(timeout: float = 2.0) -> dict[str, Any] | None:
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(HEALTH_URL, timeout=timeout) as response:
            return json.load(response)
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def local_screen_url() -> str:
    from ap01_screen_bridge import lan_ip

    return f"http://{lan_ip()}:8765/screen.gif"


def _read_pid(paths: AppPaths) -> int | None:
    try:
        value = int(paths.pid_file.read_text(encoding="ascii").strip())
        return value if value > 0 else None
    except (OSError, ValueError):
        return None


def stop_bridge(paths: AppPaths) -> None:
    pid = _read_pid(paths)
    if not pid or pid == os.getpid():
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=10,
        )
    else:
        try:
            os.killpg(pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            try:
                os.kill(pid, signal.SIGTERM)
            except (OSError, ProcessLookupError):
                pass
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and health(0.25) is not None:
        time.sleep(0.15)
    try:
        paths.pid_file.unlink()
    except OSError:
        pass


def start_bridge(paths: AppPaths, *, restart: bool = False, timeout: float = 12.0) -> bool:
    paths.ensure()
    if health(0.5) is not None and not restart:
        return True
    if restart:
        stop_bridge(paths)
    environment = os.environ.copy()
    environment["CUKTECH_DATA_ROOT"] = str(paths.data_root)
    environment["CUKTECH_ARTIFACTS_DIR"] = str(paths.artifacts)
    environment["PYTHONUNBUFFERED"] = "1"
    subprocess.Popen(
        self_command("--bridge"),
        cwd=str(paths.root),
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        **_process_creation_options(),
    )
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if health(0.5) is not None:
            return True
        time.sleep(0.25)
    return False


def _acquire_bridge_lock(paths: AppPaths):
    paths.lock_file.parent.mkdir(parents=True, exist_ok=True)
    handle = paths.lock_file.open("a+b")
    if paths.lock_file.stat().st_size == 0:
        handle.write(b"0")
        handle.flush()
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def run_bridge(paths: AppPaths | None = None) -> int:
    """Run the selected Bridge mode in the foreground for Startup/PyInstaller."""

    paths = paths or AppPaths.discover()
    paths.ensure()
    lock = _acquire_bridge_lock(paths)
    if lock is None:
        return 0
    atomic_write(paths.pid_file, f"{os.getpid()}\n")
    os.environ["CUKTECH_DATA_ROOT"] = str(paths.data_root)
    os.environ["CUKTECH_ARTIFACTS_DIR"] = str(paths.artifacts)
    try:
        with paths.log_file.open("a", encoding="utf-8", buffering=1) as output, paths.error_log.open(
            "a", encoding="utf-8", buffering=1
        ) as error, contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Windows Bridge starting")
            mode = current_mode(paths)
            if mode == "custom" and paths.custom_gif.exists():
                from ap01_screen_bridge import main as bridge_main

                sys.argv = ["ap01_screen_bridge.py", str(paths.custom_gif), "--bind", "0.0.0.0", "--port", "8765"]
            else:
                from ap01_wifi_bridge import main as bridge_main

                sys.argv = [
                    "ap01_wifi_bridge.py",
                    "--bind",
                    "0.0.0.0",
                    "--port",
                    "8765",
                    "--interval",
                    "300",
                ]
            print(f"AP01 mode: {mode}")
            return int(bridge_main() or 0)
    finally:
        lock.close()
        try:
            paths.pid_file.unlink()
        except OSError:
            pass


def convert_custom_image(paths: AppPaths, source: Path, fit: str) -> dict[str, object]:
    from ap01_prepare_screen import build, parse_color

    if fit not in {"contain", "cover", "stretch"}:
        raise ValueError(f"unknown fit mode: {fit}")
    paths.ensure()
    temporary = paths.custom_gif.with_name(paths.custom_gif.name + ".tmp")
    result = build(
        source,
        temporary,
        mode=fit,
        background=parse_color("#01040B"),
        duration=1200,
        maximum_bytes=90_000,
        maximum_frames=8,
        minimum_frame_ms=120,
    )
    os.replace(temporary, paths.custom_gif)
    atomic_write(paths.mode_file, "custom\n")
    if not start_bridge(paths, restart=True):
        raise RuntimeError("图片已转换，但 Bridge 未能在 12 秒内启动")
    return result


def use_quota_mode(paths: AppPaths) -> None:
    paths.ensure()
    atomic_write(paths.mode_file, "quota\n")
    if not start_bridge(paths, restart=True):
        raise RuntimeError("额度 Bridge 未能在 12 秒内启动")


def preview_path(paths: AppPaths) -> Path | None:
    if current_mode(paths) == "custom" and paths.custom_gif.exists():
        return paths.custom_gif
    if paths.quota_gif.exists():
        return paths.quota_gif
    if paths.quota_png.exists():
        return paths.quota_png
    return None


def tail_log(paths: AppPaths, lines: int = 10) -> str:
    chunks: list[str] = []
    for target in (paths.log_file, paths.error_log):
        try:
            chunks.extend(target.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])
        except OSError:
            pass
    return "\n".join(chunks[-lines:])


def latest_ap01_request(paths: AppPaths) -> str | None:
    try:
        lines = paths.log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    return next((line for line in reversed(lines) if "GET /screen.gif" in line), None)


def startup_path() -> Path:
    appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    return appdata / "Microsoft/Windows/Start Menu/Programs/Startup" / STARTUP_FILE


def autostart_enabled() -> bool:
    return startup_path().exists()


def enable_autostart() -> Path:
    target = startup_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    command = subprocess.list2cmdline(self_command("--bridge"))
    escaped = command.replace('"', '""')
    target.write_text(
        'Set shell = CreateObject("WScript.Shell")\r\n'
        f'shell.Run "{escaped}", 0, False\r\n',
        encoding="utf-16",
    )
    return target


def disable_autostart() -> None:
    try:
        startup_path().unlink()
    except FileNotFoundError:
        pass


def readiness(paths: AppPaths) -> list[dict[str, str]]:
    """Return the same read-only preparation checks shown by the macOS app."""

    checks: list[dict[str, str]] = []

    def add(title: str, detail: str, level: str) -> None:
        checks.append({"title": title, "detail": detail, "level": level})

    is_windows = os.name == "nt"
    add(
        "Windows 兼容性",
        f"{platform.system()} {platform.release()} · {'64 位' if sys.maxsize > 2**32 else '32 位'}",
        "ready" if is_windows and sys.maxsize > 2**32 else "attention",
    )
    add(
        "软件运行环境",
        "独立运行组件已就绪" if getattr(sys, "frozen", False) else f"Python {platform.python_version()}",
        "ready",
    )
    add(
        "登录自动启动",
        "已启用，登录 Windows 后自动运行 Bridge" if autostart_enabled() else "尚未启用，可在主界面一键开启",
        "ready" if autostart_enabled() else "attention",
    )
    document = health(1.5)
    add(
        "后台 Bridge",
        "服务已响应，可以向 AP01 提供画面" if document else "服务没有响应，请点击“重启并立即刷新”",
        "ready" if document else "missing",
    )
    claude_dir = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming")) / "Claude"
    add(
        "Claude Desktop",
        "已发现本地登录数据" if claude_dir.exists() else "未发现；仅显示自定义图片时可以忽略",
        "ready" if claude_dir.exists() else "attention",
    )
    try:
        from quota_dashboard import _codex_executable

        codex = _codex_executable()
    except Exception:
        codex = ""
    add(
        "Codex",
        f"已发现：{codex}" if codex else "未发现；可安装 Codex CLI 或在设置中指定路径",
        "ready" if codex else "attention",
    )
    url = local_screen_url()
    add(
        "局域网地址",
        url if "127.0.0.1" not in url else "没有检测到可供 AP01 访问的局域网 IPv4",
        "ready" if "127.0.0.1" not in url else "attention",
    )
    request = latest_ap01_request(paths)
    add(
        "AP01 画面请求",
        request or "最近没有 GET /screen.gif；等待轮询或检查一次性 Loader",
        "ready" if request else "attention",
    )
    return checks
