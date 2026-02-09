"""Downloader module that uses aria2c"""

from .common import DownloaderBase
import subprocess
import os
import sys


class Aria2cDownloader(DownloaderBase):
    scheme = "aria2c"

    def __init__(self, job):
        DownloaderBase.__init__(self, job)
        self.aria2c_args = self.config("args", default=[])
        self.aria2c_path = self.config("path", default="aria2c")

    def download(self, url, pathfmt):
        # Skip downloads if content exists
        if pathfmt.exists():
            return True

        # Prepare aria2c arguments
        args = [self.aria2c_path]

        # Add default arguments
        args.extend(
            [
                "--continue=true",
                "--file-allocation=none",
                "--quiet=true",
                "--console-log-level=error",
                "-x",
                "16",
                "-s",
                "16",
            ]
        )

        # Add custom arguments
        args.extend(self.aria2c_args)

        # Add headers from session
        if self.session:
            for name, value in self.session.headers.items():
                args.extend(["--header", f"{name}: {value}"])

            # Add cookies from session
            if self.session.cookies:
                cookie_header = "; ".join(
                    f"{cookie.name}={cookie.value}" for cookie in self.session.cookies
                )
                args.extend(["--header", f"Cookie: {cookie_header}"])

            # Add proxy settings from session
            if self.proxies:
                if "http" in self.proxies:
                    args.extend(["--all-proxy", self.proxies["http"]])
                elif "https" in self.proxies:
                    args.extend(["--all-proxy", self.proxies["https"]])

        # Add output path
        args.extend(
            [
                "--dir",
                os.path.dirname(pathfmt.temppath or pathfmt.path),
                "--out",
                os.path.basename(pathfmt.temppath or pathfmt.path),
            ]
        )

        # Add URL
        args.append(url)

        # Execute aria2c
        try:
            process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = process.communicate()

            # Check if download was successful
            success = process.returncode == 0
            if not success:
                stderr_text = stderr.decode() if stderr else ""
                self.log.warning(
                    "aria2c exited with code %d - %s",
                    process.returncode,
                    stderr_text,
                )
            return success

        except Exception as exc:
            self.log.warning("aria2c download failed: %s", exc)
            return False


__downloader__ = Aria2cDownloader
