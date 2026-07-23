#!/usr/bin/env python3
"""Copy the current local Mi Home session into a private Keychain item.

The value is never printed and is used only by the Controller's one-time AP01
deployment helpers. This avoids relying on cross-container plist access when a
GUI or LaunchAgent starts Python outside Terminal.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mi_cloud import MiCloud  # noqa: E402


def store(service: str, keychain_account: str) -> None:
    account = MiCloud._load_account()
    payload = json.dumps(
        {
            "userId": str(account["userId"]),
            "passToken": str(account["passToken"]),
            "deviceId": str(account.get("deviceId") or ""),
        },
        separators=(",", ":"),
    )
    subprocess.run(
        [
            "/usr/bin/security",
            "add-generic-password",
            "-U",
            "-a",
            keychain_account,
            "-s",
            service,
            "-T",
            "/usr/bin/security",
            "-w",
            payload,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        timeout=15,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", required=True)
    parser.add_argument("--account", default="owner")
    args = parser.parse_args()
    store(args.service, args.account)
    print("米家本机登录态已安全保存到 macOS 钥匙串（未输出 Token）")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
