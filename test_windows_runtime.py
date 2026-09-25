from __future__ import annotations

import os
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from windows.runtime import (
    AppPaths,
    autostart_enabled,
    convert_custom_image,
    current_mode,
    enable_autostart,
    preview_path,
)


class WindowsRuntimeTests(unittest.TestCase):
    def test_powershell5_can_decode_non_ascii_script_paths(self) -> None:
        root = Path(__file__).resolve().parent
        for script in list((root / "windows").glob("*.ps1")) + list((root / "scripts").glob("*.ps1")):
            if not script.read_text(encoding="utf-8-sig").isascii():
                self.assertTrue(script.read_bytes().startswith(b"\xef\xbb\xbf"), str(script))

    def test_source_launcher_imports_from_unrelated_cwd_without_pythonpath(self) -> None:
        root = Path(__file__).resolve().parent
        with TemporaryDirectory() as directory:
            environment = os.environ.copy()
            environment.pop("PYTHONPATH", None)
            environment["CUKTECH_DATA_ROOT"] = directory
            result = subprocess.run(
                [sys.executable, str(root / "windows/AP01ScreenController.py"), "--diagnose-json"],
                cwd=directory, env=environment, capture_output=True, text=True,
                encoding="utf-8", timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIsInstance(json.loads(result.stdout), list)

    def test_new_runtime_defaults_to_quota_mode(self) -> None:
        with TemporaryDirectory() as directory:
            paths = AppPaths.discover(Path(directory))
            paths.ensure()
            self.assertEqual(current_mode(paths), "quota")
            self.assertTrue(paths.artifacts.is_dir())

    def test_custom_image_conversion_switches_mode_and_validates_gif(self) -> None:
        from PIL import Image

        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            Image.new("RGB", (900, 500), "#159FCB").save(source)
            paths = AppPaths.discover(root / "data")
            with patch("windows.runtime.start_bridge", return_value=True):
                result = convert_custom_image(paths, source, "contain")
            self.assertEqual(current_mode(paths), "custom")
            self.assertEqual(preview_path(paths), paths.custom_gif)
            self.assertEqual(result["size"], (320, 240))
            with Image.open(paths.custom_gif) as image:
                self.assertEqual(image.info.get("version"), b"GIF89a")
                self.assertGreaterEqual(image.n_frames, 2)

    def test_startup_script_quotes_a_path_with_spaces(self) -> None:
        with TemporaryDirectory() as directory, patch.dict(
            os.environ, {"APPDATA": directory}
        ), patch(
            "windows.runtime.self_command",
            return_value=[r"C:\Program Files\CUKTECH\Controller.exe", "--bridge"],
        ):
            target = enable_autostart()
            self.assertTrue(autostart_enabled())
            content = target.read_text(encoding="utf-16")
            self.assertIn("WScript.Shell", content)
            self.assertIn("Controller.exe", content)
            self.assertIn("--bridge", content)


if __name__ == "__main__":
    unittest.main()
