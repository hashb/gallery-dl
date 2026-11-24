"""Downloader module that uses aria2c"""

from .common import DownloaderBase
from requests.cookies import get_cookie_header
import requests
import subprocess
import os


class Aria2cDownloader(DownloaderBase):
    scheme = "aria2c"

    def __init__(self, job):
        DownloaderBase.__init__(self, job)
        self._job = job
        self._http = None
        self.fallback = self.config("fallback", True)
        self.aria2c_args = self.config("args", default=[])
        self.aria2c_path = self.config("path", default="aria2c")
        self.connections = self.config("connections", 1)
        self.headers = self.config("headers")
        extractor = job.extractor
        self.retries = self.config("retries", extractor._retries)
        self.timeout = self.config("timeout", extractor._timeout)
        self.verify = self.config("verify", extractor._verify)

    def download(self, url, pathfmt):
        # Skip downloads if content exists
        if pathfmt.exists():
            return True

        # Prepare aria2c arguments
        args = [self.aria2c_path]

        # Add default arguments
        connections = str(self.connections)
        args.extend(
            [
                "--continue=true",
                "--file-allocation=none",
                "--summary-interval=0",
                "--download-result=hide",
                "--console-log-level=error",
                "--enable-color=false",
                "--no-want-digest-header=true",
                "--max-connection-per-server=" + connections,
                "--split=" + connections,
            ]
        )

        retries = self.retries
        if retries is None or retries < 0 or retries == float("inf"):
            args.append("--max-tries=0")  # unlimited
        else:
            args.append("--max-tries=" + str(int(retries) + 1))
        if timeout := self.timeout:
            if isinstance(timeout, (tuple, list)):
                timeout = max(timeout)
            args.append("--timeout=" + str(max(1, int(timeout))))
        if self.verify is False:
            args.append("--check-certificate=false")
        elif isinstance(self.verify, str):
            args.append("--ca-certificate=" + self.verify)

        # Add custom arguments
        args.extend(self.aria2c_args)

        # Collect HTTP headers (same order of precedence as 'http')
        headers = {"Accept": "*/*"}
        if self.session:
            headers.update(self.session.headers)
        if extra := pathfmt.kwdict.get("_http_headers"):
            headers.update(extra)
        if self.headers:
            headers.update(self.headers)

        # Add cookies matching this URL
        if self.session and self.session.cookies:
            if cookie := get_cookie_header(
                    self.session.cookies,
                    requests.Request("GET", url).prepare()):
                headers["Cookie"] = cookie

        for name, value in headers.items():
            if value is not None:
                args.extend(("--header", f"{name}: {value}"))

        # Add proxy settings
        if self.proxies:
            proxy = self.proxies.get("https") or self.proxies.get("http")
            if proxy:
                args.extend(["--all-proxy", proxy])

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
            process = subprocess.run(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        except Exception as exc:
            self.log.warning("aria2c download failed: %s", exc)
            return False

        if process.returncode == 0:
            return True

        self.log.warning("aria2c exited with code %d%s",
                         process.returncode,
                         self._error_message(process.stdout))

        if not self.fallback:
            return False

        # retry with the built-in HTTP downloader, which supports
        # everything gallery-dl's own requests do (TLS settings,
        # browser emulation, adapters, ...)
        self.log.info("Retrying with built-in HTTP downloader")
        temppath = pathfmt.temppath or pathfmt.path
        for p in (temppath, temppath + ".aria2"):
            try:
                os.unlink(p)
            except OSError:
                pass
        if self._http is None:
            from .http import HttpDownloader
            self._http = HttpDownloader(self._job)
        return self._http.download(url, pathfmt)

    @staticmethod
    def _error_message(output):
        """Extract the most relevant error line from aria2c's output"""
        reason = ""
        for line in output.decode(errors="replace").splitlines():
            line = line.strip()
            if line.startswith("->") or "errorCode=" in line:
                reason = line
        if not reason:
            return ""
        # strip "-> [File.cc:123] errorCode=22 " prefix
        _, _, msg = reason.rpartition("] ")
        if msg.startswith("errorCode="):
            msg = msg.partition(" ")[2]
        return " - " + (msg or reason)


__downloader__ = Aria2cDownloader
