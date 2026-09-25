from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
from contextlib import ExitStack
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory


class WiFiBridgeTests(unittest.TestCase):
    def test_one_failed_provider_does_not_hide_live_provider(self) -> None:
        import ap01_wifi_bridge as bridge
        from quota_dashboard import Quota
        from PIL import Image

        with TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            for key, name in (("PNG", "screen.png"), ("GIF", "screen.gif"),
                              ("MASTER", "master.png"), ("JSON_OUT", "quota.json")):
                stack.enter_context(patch.object(bridge, key, root / name))
            stack.enter_context(patch.object(bridge, "STATE", bridge.State()))
            stack.enter_context(patch.object(bridge, "_fetch_with_retry", side_effect=[
                RuntimeError("Claude Desktop sessionKey was not found"),
                Quota(provider="CODEX", used_percent=None, weekly_used_percent=53, plan="pro"),
            ]))
            result = bridge.refresh()
            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["codex"]["weekly_used_percent"], 53)
            self.assertIsNone(result["claude"]["used_percent"])
            self.assertIsNone(result["claude"]["remaining_percent"])
            self.assertIn("CLAUDE", result["provider_errors"])
            self.assertEqual(bridge.STATE.screen_status, "partial")
            with Image.open(bridge.GIF) as image:
                self.assertEqual(image.size, (320, 240))
                self.assertGreaterEqual(image.n_frames, 2)
            self.assertLessEqual(bridge.GIF.stat().st_size, 90000)
            bridge.STATE.last_refresh = time.time() - 500
            bridge._disconnect_if_stale()
            self.assertEqual(bridge.STATE.screen_status, "disconnected")

    def test_bridge_serves_health_and_placeholder_before_live_refresh(self) -> None:
        root = Path(__file__).resolve().parent
        with TemporaryDirectory() as directory:
            try:
                with socket.socket() as sock:
                    sock.bind(("127.0.0.1", 0))
                    port = sock.getsockname()[1]
            except PermissionError:
                self.skipTest("local listening sockets are disabled in this sandbox")

            env = os.environ.copy()
            env["CUKTECH_ARTIFACTS_DIR"] = directory
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(root / "ap01_wifi_bridge.py"),
                    "--bind",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--interval",
                    "600",
                    "--no-initial-refresh",
                ],
                cwd=root,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                deadline = time.monotonic() + 8
                health = None
                while time.monotonic() < deadline:
                    try:
                        with opener.open(f"http://127.0.0.1:{port}/health", timeout=1) as response:
                            health = json.load(response)
                        break
                    except OSError:
                        time.sleep(0.1)
                self.assertIsNotNone(health, process.stderr.read() if process.poll() is not None else "")
                self.assertTrue(health["snapshot_ready"])
                self.assertFalse(health["connected"])
                self.assertEqual(health["status"], "disconnected")

                with opener.open(f"http://127.0.0.1:{port}/screen.gif", timeout=2) as response:
                    payload = response.read()
                self.assertTrue(payload.startswith(b"GIF89a"))
                self.assertLessEqual(len(payload), 90_000)
                with opener.open(f"http://127.0.0.1:{port}/api/v1/quota", timeout=2) as response:
                    document = json.load(response)
                self.assertEqual(document["status"], "disconnected")
                self.assertEqual(document["message"], "未连接，请连接")
            finally:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
                if process.stderr is not None:
                    process.stderr.close()


if __name__ == "__main__":
    unittest.main()
