"""Unit tests for the portable binary dependency downloader."""

import io
import os
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from clip_harvester.media.downloader import (
    DependencyDownloader,
    check_ffmpeg_available,
    ensure_bin_in_path,
    get_managed_bin_dir,
)


def test_get_managed_bin_dir_exists(tmp_path: Path, monkeypatch) -> None:
    """Verifies that get_managed_bin_dir returns a directory and creates it."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    bin_dir = get_managed_bin_dir()
    assert bin_dir.exists()
    assert bin_dir.is_dir()
    assert "KdenShorts" in str(bin_dir)


def test_ensure_bin_in_path(tmp_path: Path, monkeypatch) -> None:
    """Verifies that ensure_bin_in_path prepends the managed directory to PATH."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    bin_dir = str(get_managed_bin_dir())

    # Reset PATH
    monkeypatch.setenv("PATH", "C:\\Windows\\system32")
    ensure_bin_in_path()

    current_path = os.environ.get("PATH", "")
    assert bin_dir in current_path


def test_check_ffmpeg_available_returns_booleans() -> None:
    """Verifies check_ffmpeg_available returns a tuple of booleans."""
    has_ffmpeg, has_ffprobe = check_ffmpeg_available()
    assert isinstance(has_ffmpeg, bool)
    assert isinstance(has_ffprobe, bool)


def test_downloader_initial_state(tmp_path: Path) -> None:
    """Verifies the initial state and snapshot properties of DependencyDownloader."""
    downloader = DependencyDownloader(target_dir=tmp_path)
    assert not downloader.is_finished()
    completed, pct, status, err = downloader.get_snapshot()
    assert not completed
    assert pct == 0.0
    assert err is None
    assert "Initializing" in status


def test_downloader_mock_download_and_extract(tmp_path: Path) -> None:
    """Tests archive streaming and extraction of ffmpeg and ffprobe executables."""
    # Create an in-memory zip with mock ffmpeg.exe and ffprobe.exe
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("bin/ffmpeg.exe", b"MZ_MOCK_FFMPEG_BINARY_DATA")
        z.writestr("bin/ffprobe.exe", b"MZ_MOCK_FFPROBE_BINARY_DATA")
        z.writestr("doc/readme.txt", b"Should not be extracted")
    zip_bytes = zip_buffer.getvalue()

    # Mock response object for urllib.request.urlopen
    mock_response = MagicMock()
    mock_response.headers.get.return_value = str(len(zip_bytes))
    mock_response.read.side_effect = [zip_bytes, b""]
    mock_response.__enter__.return_value = mock_response

    progress_events = []

    def on_progress(pct: float, current: int, total: int) -> None:
        progress_events.append((pct, current, total))

    downloader = DependencyDownloader(target_dir=tmp_path, progress_callback=on_progress)

    with patch("urllib.request.urlopen", return_value=mock_response):
        downloader._download_and_extract("https://example.com/mock-ffmpeg.zip")

    # Assert that binaries were extracted into the target directory
    ffmpeg_exe = tmp_path / "ffmpeg.exe"
    ffprobe_exe = tmp_path / "ffprobe.exe"
    readme_txt = tmp_path / "readme.txt"

    assert ffmpeg_exe.exists()
    assert ffmpeg_exe.read_bytes() == b"MZ_MOCK_FFMPEG_BINARY_DATA"
    assert ffprobe_exe.exists()
    assert ffprobe_exe.read_bytes() == b"MZ_MOCK_FFPROBE_BINARY_DATA"
    assert not readme_txt.exists()
    assert len(progress_events) > 0
