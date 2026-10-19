"""Unit tests for Kdenlive executable discovery and launch logic across platforms."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from clip_harvester.kdenlive.launcher import (
    find_kdenlive_executable,
    open_in_kdenlive,
    trigger_kdenlive_background_install,
)


def test_find_kdenlive_executable_real_or_none():
    exe = find_kdenlive_executable()
    # If installed on this machine, it must point to an existing file
    if exe is not None:
        assert isinstance(exe, Path)
        assert exe.exists()
        assert exe.name.lower().startswith("kdenlive")


def test_find_kdenlive_custom_path_override(tmp_path: Path):
    dummy_exe = tmp_path / "kdenlive.exe"
    dummy_exe.write_text("binary placeholder", encoding="utf-8")

    found = find_kdenlive_executable(custom_path=str(dummy_exe))
    assert found == dummy_exe.resolve()


def test_open_in_kdenlive_nonexistent_project():
    # Must fail cleanly without crashing if the project does not exist
    result = open_in_kdenlive(Path("C:/nonexistent_project_xyz123.kdenlive"))
    assert result is False


def test_open_in_kdenlive_darwin_fallback(tmp_path: Path):
    """Verifies open_in_kdenlive uses 'open' on macOS when no binary is found."""
    project = tmp_path / "test.kdenlive"
    project.write_text("<mlt></mlt>", encoding="utf-8")

    with patch("clip_harvester.kdenlive.launcher.find_kdenlive_executable", return_value=None), \
         patch("os.name", "posix"), \
         patch("sys.platform", "darwin"), \
         patch("subprocess.Popen") as mock_popen:
        success = open_in_kdenlive(project)
        assert success is True
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args[0] == "open"
        assert str(project.resolve()) in args[1]


def test_open_in_kdenlive_linux_fallback(tmp_path: Path):
    """Verifies open_in_kdenlive uses 'xdg-open' on Linux when no binary is found."""
    project = tmp_path / "test.kdenlive"
    project.write_text("<mlt></mlt>", encoding="utf-8")

    with patch("clip_harvester.kdenlive.launcher.find_kdenlive_executable", return_value=None), \
         patch("os.name", "posix"), \
         patch("sys.platform", "linux"), \
         patch("shutil.which", return_value="/usr/bin/xdg-open"), \
         patch("subprocess.Popen") as mock_popen:
        success = open_in_kdenlive(project)
        assert success is True
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args[0] == "/usr/bin/xdg-open"


def test_trigger_kdenlive_background_install_macos():
    """Verifies trigger_kdenlive_background_install calls brew on macOS."""
    with patch("os.name", "posix"), \
         patch("sys.platform", "darwin"), \
         patch("shutil.which", return_value="/opt/homebrew/bin/brew"), \
         patch("subprocess.Popen") as mock_popen:
        trigger_kdenlive_background_install()
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert "brew" in args[0]
        assert "kdenlive" in args


def test_trigger_kdenlive_background_install_linux():
    """Verifies trigger_kdenlive_background_install calls flatpak on Linux."""
    with patch("os.name", "posix"), \
         patch("sys.platform", "linux"), \
         patch("shutil.which", return_value="/usr/bin/flatpak"), \
         patch("subprocess.Popen") as mock_popen:
        trigger_kdenlive_background_install()
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert "flatpak" in args[0]
        assert "org.kde.kdenlive" in args
