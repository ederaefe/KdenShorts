"""Unit tests for the zero-dependency bootstrap, OS detection, and auto-installer."""

from unittest.mock import MagicMock, patch

from clip_harvester.bootstrap import (
    auto_install_packages,
    check_missing_python_modules,
    detect_os_info,
    ensure_environment,
)


def test_detect_os_info_windows() -> None:
    """Verifies OS detection on Windows returns winget install commands."""
    with patch("platform.system", return_value="Windows"), patch("platform.release", return_value="11"), patch("platform.machine", return_value="AMD64"):
        info = detect_os_info()
        assert info.os_type == "windows"
        assert "Windows 11" in info.display_name
        assert "winget install Gyan.FFmpeg" in info.ffmpeg_install_cmd
        assert "winget install KDE.Kdenlive" in info.kdenlive_install_cmd
        assert "requirements.txt" in info.pip_install_cmd


def test_detect_os_info_macos() -> None:
    """Verifies OS detection on macOS returns Homebrew install commands."""
    with patch("platform.system", return_value="Darwin"), patch("platform.mac_ver", return_value=("14.4", ("", "", ""), "")):
        info = detect_os_info()
        assert info.os_type == "macos"
        assert "brew install ffmpeg" in info.ffmpeg_install_cmd
        assert "brew install --cask kdenlive" in info.kdenlive_install_cmd
        assert "pip3" in info.pip_install_cmd


def test_detect_os_info_linux_debian() -> None:
    """Verifies OS detection on Debian/Ubuntu returns apt install commands."""
    with patch("platform.system", return_value="Linux"), patch("clip_harvester.bootstrap.get_linux_distro", return_value=("debian", "Ubuntu 22.04 LTS")):
        info = detect_os_info()
        assert info.os_type == "linux"
        assert "apt" in info.ffmpeg_install_cmd
        assert "apt" in info.kdenlive_install_cmd


def test_detect_os_info_linux_fedora() -> None:
    """Verifies OS detection on Fedora returns dnf install commands."""
    with patch("platform.system", return_value="Linux"), patch("clip_harvester.bootstrap.get_linux_distro", return_value=("fedora", "Fedora Linux 39")):
        info = detect_os_info()
        assert info.os_type == "linux"
        assert "dnf" in info.ffmpeg_install_cmd
        assert "dnf" in info.kdenlive_install_cmd


def test_detect_os_info_linux_arch() -> None:
    """Verifies OS detection on Arch returns pacman install commands."""
    with patch("platform.system", return_value="Linux"), patch("clip_harvester.bootstrap.get_linux_distro", return_value=("arch", "Arch Linux")):
        info = detect_os_info()
        assert info.os_type == "linux"
        assert "pacman" in info.ffmpeg_install_cmd
        assert "pacman" in info.kdenlive_install_cmd


def test_check_missing_python_modules_all_installed() -> None:
    """Verifies check_missing_python_modules returns empty list in current complete environment."""
    missing = check_missing_python_modules()
    assert missing == []


def test_check_missing_python_modules_detects_missing() -> None:
    """Verifies check_missing_python_modules accurately detects a missing module."""
    mock_registry = {
        "nonexistent_package_for_test": ("nonexistent>=1.0.0", "Test Description"),
    }
    with patch("clip_harvester.bootstrap.REQUIRED_PYTHON_MODULES", mock_registry):
        missing = check_missing_python_modules()
        assert len(missing) == 1
        assert missing[0][0] == "nonexistent_package_for_test"


def test_auto_install_packages_success() -> None:
    """Verifies auto_install_packages returns True when pip completes with exit code 0."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    with patch("subprocess.run", return_value=mock_result):
        assert auto_install_packages(["dummy-package"]) is True


def test_auto_install_packages_failure() -> None:
    """Verifies auto_install_packages returns False when pip fails."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    with patch("subprocess.run", return_value=mock_result):
        assert auto_install_packages(["dummy-package"]) is False


def test_ensure_environment_no_op_when_clean() -> None:
    """Verifies ensure_environment completes silently when no modules are missing."""
    with patch("clip_harvester.bootstrap.check_missing_python_modules", return_value=[]):
        # Should not raise or exit
        ensure_environment()
