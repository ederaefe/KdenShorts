"""Background dependency downloader for portable FFmpeg and FFprobe binaries."""

import io
import os
import shutil
import sys
import tempfile
import threading
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Optional, Tuple

# Stable Windows 64-bit static release builds
FFMPEG_WINDOWS_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
FFMPEG_FALLBACK_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"


def get_managed_bin_dir() -> Path:
    """Returns the user-level managed directory for portable binaries."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        bin_dir = base / "KdenShorts" / "bin"
    else:
        bin_dir = Path.home() / ".local" / "share" / "kdenshorts" / "bin"

    bin_dir.mkdir(parents=True, exist_ok=True)
    return bin_dir.resolve()


def ensure_bin_in_path() -> None:
    """Ensures the managed binary directory is present in the active runtime PATH."""
    bin_dir = str(get_managed_bin_dir())
    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    if bin_dir not in path_entries:
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")


def check_ffmpeg_available() -> Tuple[bool, bool]:
    """Checks whether ffmpeg and ffprobe are available either in PATH or managed cache."""
    ensure_bin_in_path()
    has_ffmpeg = shutil.which("ffmpeg") is not None
    has_ffprobe = shutil.which("ffprobe") is not None
    return has_ffmpeg, has_ffprobe


class DependencyDownloader(threading.Thread):
    """Background worker that streams and unpacks static FFmpeg binaries."""

    def __init__(
        self,
        target_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
    ):
        super().__init__(daemon=True)
        self.target_dir = target_dir or get_managed_bin_dir()
        self.progress_callback = progress_callback

        self.bytes_downloaded = 0
        self.total_bytes = 0
        self.progress_percent = 0.0
        self.status = "Initializing..."
        self.completed = False
        self.error: Optional[str] = None
        self._lock = threading.Lock()

    def run(self) -> None:
        """Executes the download and extraction workflow in the background."""
        if os.name != "nt":
            from clip_harvester.bootstrap import detect_os_info

            os_info = detect_os_info()
            with self._lock:
                self.completed = True
                self.error = f"Portable zip downloader is configured for Windows. On {os_info.display_name}, please run: {os_info.ffmpeg_install_cmd}"
                self.status = f"Run: {os_info.ffmpeg_install_cmd}"
            return

        urls = [FFMPEG_WINDOWS_URL, FFMPEG_FALLBACK_URL]
        success = False

        for url in urls:
            try:
                with self._lock:
                    self.status = f"Connecting to {url.split('/')[2]}..."
                self._download_and_extract(url)
                success = True
                break
            except Exception as e:
                with self._lock:
                    self.error = str(e)
                    self.status = f"Failed ({e}). Trying fallback..."

        with self._lock:
            if success:
                ensure_bin_in_path()
                self.completed = True
                self.status = "FFmpeg installed successfully."
                self.progress_percent = 100.0
            else:
                self.completed = True
                self.status = f"Download failed: {self.error}"

    def _download_and_extract(self, url: str) -> None:
        """Streams zip archive to a temporary file and extracts ffmpeg.exe and ffprobe.exe."""
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
            temp_zip_path = Path(temp_zip.name)

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "KdenShorts-Downloader/1.0"},
            )

            with urllib.request.urlopen(req, timeout=60) as response:
                content_length = response.headers.get("Content-Length")
                total_size = int(content_length) if content_length else 90 * 1024 * 1024
                with self._lock:
                    self.total_bytes = total_size
                    self.status = "Downloading portable FFmpeg (~90MB)..."

                chunk_size = 64 * 1024
                downloaded = 0

                with open(temp_zip_path, "wb") as f_out:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f_out.write(chunk)
                        downloaded += len(chunk)

                        with self._lock:
                            self.bytes_downloaded = downloaded
                            self.progress_percent = min(100.0, (downloaded / total_size) * 100.0)

                        if self.progress_callback:
                            self.progress_callback(self.progress_percent, downloaded, total_size)

            with self._lock:
                self.status = "Extracting ffmpeg.exe and ffprobe.exe..."

            # Extract only the necessary executables from the zip
            self.target_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(temp_zip_path, "r") as z:
                for filename in z.namelist():
                    basename = os.path.basename(filename).lower()
                    if basename in ("ffmpeg.exe", "ffprobe.exe", "ffmpeg", "ffprobe"):
                        extracted_bytes = z.read(filename)
                        dest_file = self.target_dir / os.path.basename(filename)
                        dest_file.write_bytes(extracted_bytes)
                        # Set executable permissions on non-Windows
                        if os.name != "nt":
                            dest_file.chmod(0o755)

        finally:
            if temp_zip_path.exists():
                try:
                    temp_zip_path.unlink()
                except Exception:
                    pass

    def is_finished(self) -> bool:
        """Returns True if the background thread has finished."""
        with self._lock:
            return self.completed

    def get_snapshot(self) -> Tuple[bool, float, str, Optional[str]]:
        """Returns thread-safe snapshot of (completed, progress_percent, status, error)."""
        with self._lock:
            return self.completed, self.progress_percent, self.status, self.error
