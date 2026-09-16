"""Allowlisted local system actions for JARVIS on Windows."""

import ctypes
from ctypes import wintypes
from datetime import datetime
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time
from urllib.parse import urlparse
import webbrowser


CPU_SAMPLE_SECONDS = 0.1


class SystemControlError(Exception):
    """Raised when a local system action cannot be completed safely."""


class MEMORYSTATUSEX(ctypes.Structure):
    """Windows structure used by GlobalMemoryStatusEx."""

    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


class SystemController:
    """Perform only named, local Windows actions requested by the user."""

    def get_cpu_usage(self):
        """Return a short CPU-usage report based on Windows system times."""
        self._require_windows("CPU usage")
        first_idle, first_total = self._get_cpu_times()
        time.sleep(CPU_SAMPLE_SECONDS)
        second_idle, second_total = self._get_cpu_times()
        total_change = second_total - first_total
        if total_change <= 0:
            raise SystemControlError("CPU usage is temporarily unavailable. Please try again.")
        usage = 100 * (1 - (second_idle - first_idle) / total_change)
        return f"CPU usage is {usage:.1f}% across all processors."

    def get_ram_usage(self):
        """Return physical RAM usage reported by Windows."""
        self._require_windows("RAM usage")
        memory_status = MEMORYSTATUSEX()
        memory_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status)):
            raise SystemControlError("RAM usage is unavailable right now.")
        used = memory_status.ullTotalPhys - memory_status.ullAvailPhys
        return (
            f"RAM usage is {self._format_bytes(used)} of "
            f"{self._format_bytes(memory_status.ullTotalPhys)} ({memory_status.dwMemoryLoad}%)."
        )

    def get_disk_usage(self):
        """Return usage for the drive containing the user's home directory."""
        usage = shutil.disk_usage(Path.home().anchor or Path.home())
        used_percent = usage.used / usage.total * 100
        return (
            f"Disk usage is {self._format_bytes(usage.used)} of "
            f"{self._format_bytes(usage.total)} ({used_percent:.1f}%)."
        )

    def get_operating_system(self):
        """Return the current operating-system name and release."""
        return f"You are running {platform.system()} {platform.release()}."

    def open_chrome(self):
        """Open only the allowlisted Chrome executable."""
        return self._open_application("chrome", "Google Chrome")

    def open_vs_code(self):
        """Open only the allowlisted VS Code executable."""
        return self._open_application("code", "VS Code")

    def open_downloads_folder(self):
        """Open the current user's Downloads folder on Windows."""
        self._require_windows("Opening Downloads")
        downloads_path = Path.home() / "Downloads"
        try:
            os.startfile(str(downloads_path))
        except OSError as error:
            raise SystemControlError(f"I could not open Downloads: {error}") from error
        return "Opening your Downloads folder."

    def open_url(self, url):
        """Open one explicitly requested HTTP(S) URL in the default browser."""
        parsed_url = urlparse(url)
        if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
            raise SystemControlError("Please provide a complete http or https URL.")
        if not webbrowser.open(url):
            raise SystemControlError("I could not open that URL in your browser.")
        return "Opening that URL."

    def take_screenshot(self):
        """Capture the primary display to a local PNG through a fixed PowerShell script."""
        self._require_windows("Taking a screenshot")
        screenshots_directory = Path.home() / "Pictures" / "JARVIS Screenshots"
        screenshots_directory.mkdir(parents=True, exist_ok=True)
        filename = datetime.now().strftime("jarvis-screenshot-%Y%m%d-%H%M%S.png")
        screenshot_path = screenshots_directory / filename
        escaped_path = str(screenshot_path).replace("'", "''")
        script = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "Add-Type -AssemblyName System.Drawing; "
            "$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
            "$bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height; "
            "$graphics = [System.Drawing.Graphics]::FromImage($bitmap); "
            "$graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size); "
            f"$bitmap.Save('{escaped_path}', [System.Drawing.Imaging.ImageFormat]::Png); "
            "$graphics.Dispose(); $bitmap.Dispose()"
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            raise SystemControlError(f"I could not take a screenshot: {error}") from error
        return f"Screenshot saved locally to {screenshot_path}."

    def _get_cpu_times(self):
        idle_time = wintypes.FILETIME()
        kernel_time = wintypes.FILETIME()
        user_time = wintypes.FILETIME()
        if not ctypes.windll.kernel32.GetSystemTimes(
            ctypes.byref(idle_time), ctypes.byref(kernel_time), ctypes.byref(user_time)
        ):
            raise SystemControlError("CPU usage is unavailable right now.")
        idle = self._filetime_to_int(idle_time)
        total = self._filetime_to_int(kernel_time) + self._filetime_to_int(user_time)
        return idle, total

    @staticmethod
    def _filetime_to_int(file_time):
        return (file_time.dwHighDateTime << 32) + file_time.dwLowDateTime

    def _open_application(self, executable, application_name):
        try:
            subprocess.Popen([executable], shell=False)
        except OSError as error:
            raise SystemControlError(f"I could not open {application_name}: {error}") from error
        return f"Opening {application_name}."

    def _require_windows(self, action):
        if platform.system() != "Windows":
            raise SystemControlError(f"{action} is currently supported only on Windows.")

    @staticmethod
    def _format_bytes(size):
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or unit == "TB":
                return f"{size:.1f} {unit}"
            size /= 1024
