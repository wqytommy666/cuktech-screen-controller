#!/usr/bin/env python3
"""CUKTECH Screen Controller entry point for Windows."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Direct execution sets sys.path[0] to windows/, not the repository root.
# Fresh source installs and the generated Startup shortcut use this form.
if not getattr(sys, "frozen", False) and not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from windows.runtime import AppPaths, readiness, run_bridge


def _ota_helper(arguments: list[str]) -> int:
    paths = AppPaths.discover()
    paths.ensure()
    os.environ["CUKTECH_DATA_ROOT"] = str(paths.data_root)
    os.environ["CUKTECH_ARTIFACTS_DIR"] = str(paths.artifacts)
    from ap01_install_firmware import main

    sys.argv = ["ap01_install_firmware.py", *arguments]
    return int(main() or 0)


def _relay_helper(arguments: list[str]) -> int:
    paths = AppPaths.discover()
    paths.ensure()
    os.environ["CUKTECH_DATA_ROOT"] = str(paths.data_root)
    os.environ["CUKTECH_ARTIFACTS_DIR"] = str(paths.artifacts)
    from ap01_fds_relay_client import main

    return int(main(arguments) or 0)


def main() -> int:
    arguments = sys.argv[1:]
    if arguments and arguments[0] == "--bridge":
        return run_bridge()
    if arguments and arguments[0] == "--ota-helper":
        return _ota_helper(arguments[1:])
    if arguments and arguments[0] == "--relay-helper":
        return _relay_helper(arguments[1:])
    if arguments and arguments[0] == "--diagnose-json":
        import json

        # Pipes on a fresh Windows install may use a non-UTF-8 code page.
        # JSON escapes retain the text without breaking redirected diagnostics.
        print(json.dumps(readiness(AppPaths.discover()), ensure_ascii=True, indent=2))
        return 0

    from windows.ui import run_gui

    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
