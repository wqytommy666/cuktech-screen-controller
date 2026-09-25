import io
import unittest
from unittest.mock import patch

from ap01_console import configure_stdio


class ConsoleTests(unittest.TestCase):
    def test_chinese_ota_messages_survive_legacy_windows_pipe_encoding(self):
        output = io.BytesIO()
        stream = io.TextIOWrapper(output, encoding="cp1252")
        with patch("sys.stdout", stream), patch("sys.stderr", stream):
            configure_stdio()
            print("仅下载验证通过；尚未安装")
            stream.flush()
            self.assertEqual(output.getvalue().decode("utf-8"), "仅下载验证通过；尚未安装\n")

    def test_windowed_apps_and_captured_streams_are_supported(self):
        with patch("sys.stdout", None), patch("sys.stderr", io.StringIO()):
            configure_stdio()


if __name__ == "__main__":
    unittest.main()
