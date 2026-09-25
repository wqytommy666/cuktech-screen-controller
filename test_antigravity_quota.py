import copy
import json
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from quota_dashboard import Quota, fetch_antigravity, parse_antigravity_usage, render_outputs


def report():
    return {"status": "SUCCESS", "command": {"name": "usage", "data": {"groups": [
        {"name": "Gemini Models", "buckets": [
            {"id": "gemini-5h", "window": "5h", "remaining_fraction": .75,
             "reset_time": "2026-09-25T11:00:00Z"},
            {"id": "gemini-weekly", "window": "weekly", "remaining_fraction": .90,
             "reset_time": "2026-09-30T05:00:00Z"}]},
        {"name": "Claude and GPT models", "buckets": [
            {"id": "3p-5h", "window": "5h", "remaining_fraction": 0},
            {"id": "3p-weekly", "window": "weekly", "remaining_fraction": 1}]}]}}}


class AntigravityTests(unittest.TestCase):
    def test_actual_command_schema_and_remaining_direction(self):
        quota = parse_antigravity_usage(report())
        self.assertEqual(quota.provider, "ANTIGRAVITY")
        self.assertIsNone(quota.plan)  # /usage does not identify a paid plan.
        self.assertEqual(quota.groups[0].used_percent, 25)
        self.assertAlmostEqual(quota.groups[0].weekly_used_percent, 10)
        self.assertIsInstance(quota.groups[0].resets_at, int)
        self.assertEqual(quota.groups[1].used_percent, 100)
        self.assertEqual(quota.groups[1].weekly_used_percent, 0)
        self.assertEqual(quota.remaining_percent, 0)

    def test_missing_disabled_invalid_windows_do_not_become_full(self):
        for fraction in (None, "1", True, -1, 1.2, float("nan"), float("inf")):
            value = report()
            value["command"]["data"]["groups"][0]["buckets"][0]["remaining_fraction"] = fraction
            self.assertIsNone(parse_antigravity_usage(value).groups[0].used_percent)
        value = report()
        value["command"]["data"]["groups"][0]["buckets"][0]["enabled"] = False
        self.assertIsNone(parse_antigravity_usage(value).groups[0].used_percent)
        value["command"]["data"]["groups"] = value["command"]["data"]["groups"][:1]
        self.assertIsNone(parse_antigravity_usage(value).groups[1].weekly_used_percent)

    def test_does_not_parse_llm_text_or_wrong_command(self):
        for value in ({"status": "SUCCESS", "response": "100%"},
                      {"status": "ERROR", "command": report()["command"]}, [],
                      {"status": "SUCCESS", "command": {"name": "usage", "data": {"groups": []}}}):
            with self.assertRaises(ValueError):
                parse_antigravity_usage(value)

    def test_unknown_and_duplicate_windows(self):
        value = report()
        buckets = value["command"]["data"]["groups"][0]["buckets"]
        buckets.append(copy.deepcopy(buckets[0]))
        with self.assertRaises(ValueError):
            parse_antigravity_usage(value)
        buckets[-1]["id"] = "future-unknown"
        self.assertEqual(parse_antigravity_usage(value).groups[0].used_percent, 25)

    def run_cli(self, script, timeout=2):
        with TemporaryDirectory() as directory:
            fixture = Path(directory) / "agy_fixture.py"
            fixture.write_text(script)
            with patch("quota_dashboard._antigravity_executable", return_value=sys.executable), \
                 patch("quota_dashboard._codex_command", return_value=[sys.executable, str(fixture)]):
                return fetch_antigravity(timeout=timeout)

    def test_readonly_metacommand_uses_empty_cwd_and_no_stdin(self):
        value = self.run_cli(
            "import os,sys\nassert not os.listdir('.')\n"
            "assert sys.argv[1:] == ['-p','/usage','--output-format','json']\n"
            "assert sys.stdin.read() == ''\nprint(" + repr(json.dumps(report())) + ")\n")
        self.assertEqual(value.provider, "ANTIGRAVITY")

    def test_cli_size_timeout_and_error_are_bounded_and_sanitized(self):
        with self.assertRaisesRegex(RuntimeError, "大小限制"):
            self.run_cli("print('x' * (1024 * 1024 + 2))")
        with self.assertRaisesRegex(TimeoutError, "超时"):
            self.run_cli("import time\ntime.sleep(5)", timeout=.1)
        with self.assertRaisesRegex(RuntimeError, "登录状态") as failure:
            self.run_cli("import sys\nprint('secret-token', file=sys.stderr)\nsys.exit(1)")
        self.assertNotIn("secret-token", str(failure.exception))

    def test_lightweight_dashboard_preserves_clock_and_offline_timeout(self):
        from PIL import Image
        with TemporaryDirectory() as directory:
            root = Path(directory)
            render_outputs(parse_antigravity_usage(report()),
                           Quota(provider="CODEX", used_percent=None, weekly_used_percent=54),
                           root / "screen.png", root / "screen.gif", root / "master.png")
            payload = (root / "screen.gif").read_bytes()
            self.assertTrue(payload.startswith(b"GIF89a"))
            self.assertLess(len(payload), 90000)
            with Image.open(root / "screen.gif") as image:
                self.assertEqual(image.size, (320, 240))
                self.assertEqual(image.n_frames, 4)
                self.assertNotIn("loop", image.info)
                durations = []
                for index in range(image.n_frames):
                    image.seek(index)
                    durations.append(image.info["duration"])
                self.assertEqual(sum(durations[:-1]), 420000)
            with Image.open(root / "screen.png") as image:
                self.assertEqual(len(image.crop((0, 0, 320, 40)).getcolors()), 1)

    def test_bridge_emits_antigravity_not_claude_and_retains_partial_codex(self):
        import ap01_wifi_bridge as bridge
        with TemporaryDirectory() as directory, ExitStack() as stack:
            for key, name in (("PNG", "screen.png"), ("GIF", "screen.gif"),
                              ("MASTER", "master.png"), ("JSON_OUT", "quota.json")):
                stack.enter_context(patch.object(bridge, key, Path(directory) / name))
            stack.enter_context(patch.object(bridge, "STATE", bridge.State()))
            bridge.STATE.quota_provider = "antigravity"
            stack.enter_context(patch.object(bridge, "_fetch_with_retry", side_effect=[
                parse_antigravity_usage(report()), RuntimeError("Codex offline")]))
            result = bridge.refresh()
            self.assertIn("antigravity", result)
            self.assertNotIn("claude", result)
            self.assertEqual(result["status"], "partial")
            self.assertEqual(len(result["antigravity"]["groups"]), 2)
            self.assertIsNone(result["codex"]["remaining_percent"])


if __name__ == "__main__":
    unittest.main()
