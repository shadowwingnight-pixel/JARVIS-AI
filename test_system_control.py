"""Mocked tests for JARVIS's local allowlisted system actions."""

import tempfile
import unittest
import ctypes
from pathlib import Path
from unittest.mock import MagicMock, patch

from system_control import MEMORYSTATUSEX, SystemController


class SystemControllerTests(unittest.TestCase):
    def setUp(self):
        self.controller = SystemController()

    @patch("system_control.platform.system", return_value="Windows")
    @patch.object(SystemController, "_get_cpu_times", side_effect=[(20, 100), (30, 200)])
    @patch("system_control.time.sleep")
    def test_cpu_usage(self, _sleep, _get_cpu_times, _system):
        self.assertEqual(self.controller.get_cpu_usage(), "CPU usage is 90.0% across all processors.")

    @patch("system_control.shutil.disk_usage")
    def test_disk_usage(self, mock_disk_usage):
        mock_disk_usage.return_value = MagicMock(total=1000, used=250)
        self.assertIn("25.0%", self.controller.get_disk_usage())

    @patch("system_control.platform.system", return_value="Windows")
    @patch("system_control.ctypes.windll")
    def test_ram_usage(self, mock_windll, _system):
        def set_memory_status(status_pointer):
            status = ctypes.cast(status_pointer, ctypes.POINTER(MEMORYSTATUSEX)).contents
            status.ullTotalPhys = 8 * 1024**3
            status.ullAvailPhys = 4 * 1024**3
            status.dwMemoryLoad = 50
            return 1

        mock_windll.kernel32.GlobalMemoryStatusEx.side_effect = set_memory_status

        self.assertEqual(self.controller.get_ram_usage(), "RAM usage is 4.0 GB of 8.0 GB (50%).")

    @patch("system_control.platform.release", return_value="11")
    @patch("system_control.platform.system", return_value="Windows")
    def test_operating_system(self, _system, _release):
        self.assertEqual(self.controller.get_operating_system(), "You are running Windows 11.")

    @patch("system_control.subprocess.Popen")
    def test_allowlisted_applications(self, mock_popen):
        self.assertEqual(self.controller.open_chrome(), "Opening Google Chrome.")
        self.assertEqual(self.controller.open_vs_code(), "Opening VS Code.")
        self.assertEqual(mock_popen.call_args_list[0].args[0], ["chrome"])
        self.assertEqual(mock_popen.call_args_list[0].kwargs["shell"], False)
        self.assertEqual(mock_popen.call_args_list[1].args[0], ["code"])

    @patch("system_control.platform.system", return_value="Windows")
    @patch("system_control.os.startfile", create=True)
    def test_open_downloads(self, mock_startfile, _system):
        self.assertEqual(self.controller.open_downloads_folder(), "Opening your Downloads folder.")
        self.assertEqual(Path(mock_startfile.call_args.args[0]).name, "Downloads")

    @patch("system_control.webbrowser.open", return_value=True)
    def test_open_url_requires_http_or_https(self, mock_open):
        self.assertEqual(self.controller.open_url("https://example.com"), "Opening that URL.")
        mock_open.assert_called_once_with("https://example.com")
        with self.assertRaisesRegex(Exception, "complete http"):
            self.controller.open_url("file:///unsafe")

    @patch("system_control.platform.system", return_value="Windows")
    @patch("system_control.subprocess.run")
    @patch("system_control.Path.home")
    def test_screenshot_uses_fixed_powershell_arguments(self, mock_home, mock_run, _system):
        with tempfile.TemporaryDirectory() as directory:
            mock_home.return_value = Path(directory)
            result = self.controller.take_screenshot()

        command = mock_run.call_args.args[0]
        self.assertEqual(command[:4], ["powershell", "-NoProfile", "-NonInteractive", "-Command"])
        self.assertIn("CopyFromScreen", command[4])
        self.assertIn("Screenshot saved locally", result)


if __name__ == "__main__":
    unittest.main()
