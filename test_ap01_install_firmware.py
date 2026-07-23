from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import ap01_install_firmware
from ap01_custom_ota import choose_fds_device
from mi_cloud import MiCloud


class InstallFirmwareTests(unittest.TestCase):
    def test_keychain_credentials_are_loaded_without_printing_tokens(self) -> None:
        completed = Mock(stdout='{"userId":"10001","passToken":"secret","deviceId":"mac"}')
        with (
            patch.dict(
                "os.environ",
                {
                    "CUKTECH_MI_KEYCHAIN_SERVICE": "test.service",
                    "CUKTECH_MI_KEYCHAIN_ACCOUNT": "relay",
                },
                clear=True,
            ),
            patch("mi_cloud.subprocess.run", return_value=completed) as run,
        ):
            self.assertEqual(
                MiCloud._load_account(),
                {"userId": "10001", "passToken": "secret", "deviceId": "mac"},
            )
        command = run.call_args.args[0]
        self.assertNotIn("secret", command)

    def test_windows_json_credentials_are_loaded_without_persisting_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mi-credentials.json"
            path.write_text(
                '{"userId":"10001","passToken":"secret","deviceId":"windows-device"}',
                encoding="utf-8",
            )
            self.assertEqual(
                MiCloud._load_account(credentials=path),
                {
                    "userId": "10001",
                    "passToken": "secret",
                    "deviceId": "windows-device",
                },
            )

    def make_firmware(self, root: Path) -> Path:
        path = root / "screen-realtime.bin"
        path.write_bytes(b"BFNP" + bytes(60))
        return path

    def test_explicit_fds_identity_does_not_require_device_listing(self) -> None:
        cloud = Mock()
        selected = choose_fds_device(
            cloud,
            did="gateway-did",
            model="lumi.gateway.example",
        )
        self.assertEqual(
            selected,
            {"did": "gateway-did", "model": "lumi.gateway.example"},
        )
        cloud.devices.assert_not_called()

    def test_upload_only_writes_transferable_url(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            firmware = self.make_firmware(root)
            output = root / "ota-url.txt"
            with (
                patch.object(ap01_install_firmware, "MiCloud", return_value=Mock()),
                patch.object(
                    ap01_install_firmware,
                    "upload_to_xiaomi",
                    return_value="https://iot-ota-cdn.io.mi.com/object?signature=test",
                ),
                patch.object(ap01_install_firmware, "deliver") as deliver,
                patch(
                    "sys.argv",
                    [
                        "ap01_install_firmware.py",
                        str(firmware),
                        "--upload-only",
                        "--url-output",
                        str(output),
                    ],
                ),
            ):
                self.assertEqual(ap01_install_firmware.main(), 0)
            self.assertEqual(
                output.read_text(encoding="utf-8").strip(),
                "https://iot-ota-cdn.io.mi.com/object?signature=test",
            )
            deliver.assert_not_called()

    def test_download_only_can_reuse_signed_url(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            firmware = self.make_firmware(root)
            cloud = Mock()
            url = "https://iot-ota-cdn.io.mi.com/object?signature=test"
            with (
                patch.object(ap01_install_firmware, "MiCloud", return_value=cloud),
                patch.object(ap01_install_firmware, "probe_ota_url") as probe,
                patch.object(ap01_install_firmware, "upload_to_xiaomi") as upload,
                patch.object(ap01_install_firmware, "deliver") as deliver,
                patch(
                    "sys.argv",
                    [
                        "ap01_install_firmware.py",
                        str(firmware),
                        "--download-only",
                        "--ota-url",
                        url,
                    ],
                ),
            ):
                self.assertEqual(ap01_install_firmware.main(), 0)
            probe.assert_called_once_with(url)
            upload.assert_not_called()
            deliver.assert_called_once_with(
                cloud,
                firmware,
                url,
                360,
                download_only=True,
            )

    def test_download_only_can_read_signed_url_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            firmware = self.make_firmware(root)
            url = "https://iot-ota-cdn.io.mi.com/object?signature=test"
            url_file = root / "ota-url.txt"
            url_file.write_text(url + "\n", encoding="utf-8")
            cloud = Mock()
            with (
                patch.object(ap01_install_firmware, "MiCloud", return_value=cloud),
                patch.object(ap01_install_firmware, "probe_ota_url") as probe,
                patch.object(ap01_install_firmware, "upload_to_xiaomi") as upload,
                patch.object(ap01_install_firmware, "deliver") as deliver,
                patch(
                    "sys.argv",
                    [
                        "ap01_install_firmware.py",
                        str(firmware),
                        "--download-only",
                        "--ota-url-file",
                        str(url_file),
                    ],
                ),
            ):
                self.assertEqual(ap01_install_firmware.main(), 0)
            probe.assert_called_once_with(url)
            upload.assert_not_called()
            deliver.assert_called_once_with(
                cloud,
                firmware,
                url,
                360,
                download_only=True,
            )


if __name__ == "__main__":
    unittest.main()
