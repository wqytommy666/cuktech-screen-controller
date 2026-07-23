from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import ap01_fds_relay_client as client
from ap01_fds_relay_server import RateLimiter, TicketRequest, redact_urls


class RelayValidationTests(unittest.TestCase):
    def test_private_bridge_url_is_normalized(self) -> None:
        self.assertEqual(
            client.validate_bridge_url("http://192.168.31.45:8765/screen.gif"),
            "http://192.168.31.45:8765/screen.gif",
        )

    def test_public_or_wrong_path_bridge_is_rejected(self) -> None:
        for value in (
            "https://192.168.1.2:8765/screen.gif",
            "http://8.8.8.8:8765/screen.gif",
            "http://127.0.0.1:8765/screen.gif",
            "http://192.168.1.2:8000/screen.gif",
            "http://192.168.1.2:8765/other.gif",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                client.validate_bridge_url(value)

    def test_ticket_request_rejects_extra_fields(self) -> None:
        payload = {
            "api_version": 1,
            "model": "njcuk.enstor.ap01",
            "firmware": "1.0.2_0031",
            "bridge_url": "http://192.168.31.45:8765/screen.gif",
            "refresh_seconds": 300,
            "firmware_upload": "not-allowed",
        }
        with self.assertRaises(ValueError):
            TicketRequest.parse(payload)

    def test_ticket_payload_pins_model_hashes_and_cdn(self) -> None:
        bridge = "http://192.168.31.45:8765/screen.gif"
        payload = {
            "api_version": 1,
            "firmware": {
                "model": "njcuk.enstor.ap01",
                "version": "1.0.2_0031",
                "bridge_url": bridge,
                "refresh_seconds": 300,
                "size": client.EXPECTED_FIRMWARE_SIZE,
                "sha256": "a" * 64,
                "md5": "b" * 32,
            },
            "ticket": {
                "url": "https://iot-ota-cdn.io.mi.com/object.bin?Signature=secret"
            },
        }
        self.assertIs(
            client.validate_ticket_payload(payload, bridge_url=bridge, refresh_seconds=300),
            payload,
        )
        payload["ticket"]["url"] = "https://example.com/object.bin"
        with self.assertRaises(RuntimeError):
            client.validate_ticket_payload(payload, bridge_url=bridge, refresh_seconds=300)

    def test_rate_limiter_enforces_client_window(self) -> None:
        now = [1000.0]
        limiter = RateLimiter(
            per_client=2,
            per_client_window=60,
            global_limit=10,
            global_window=600,
            clock=lambda: now[0],
        )
        self.assertEqual(limiter.acquire("one"), (True, 0))
        self.assertEqual(limiter.acquire("one"), (True, 0))
        allowed, retry = limiter.acquire("one")
        self.assertFalse(allowed)
        self.assertGreaterEqual(retry, 60)
        now[0] += 61
        self.assertEqual(limiter.acquire("one"), (True, 0))

    def test_redaction_removes_signed_query(self) -> None:
        value = redact_urls("failed https://iot-ota-cdn.io.mi.com/a?Signature=secret now")
        self.assertNotIn("secret", value)
        self.assertIn("?••••", value)


class RelayDownloadTests(unittest.TestCase):
    def test_download_checks_firmware_metadata_before_atomic_replace(self) -> None:
        content = b"BFNP" + os.urandom(128)
        payload = {
            "firmware": {
                "size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "md5": hashlib.md5(content).hexdigest(),
            },
            "ticket": {
                "url": "https://iot-ota-cdn.io.mi.com/object.bin?Signature=secret"
            },
        }
        response = Mock(status_code=200)
        response.iter_content.return_value = [content[:7], content[7:]]
        with tempfile.TemporaryDirectory() as directory, patch.object(
            client.requests, "get", return_value=response
        ):
            output = Path(directory) / "firmware.bin"
            self.assertEqual(client.download_firmware(payload, output), output)
            self.assertEqual(output.read_bytes(), content)

    def test_discovery_disabled_has_clear_error(self) -> None:
        response = Mock(status_code=200)
        response.json.return_value = {"enabled": False, "url": ""}
        with patch.object(client.requests, "get", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "维护"):
                client.resolve_relay_url(discovery_url="https://example.invalid/relay.json")


if __name__ == "__main__":
    unittest.main()
