"""Kdenlive application discovery and project launch engine."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


def find_kdenlive_executable(custom_path: Optional[str] = None) -> Optional[Path]:
    """Discovers the kdenlive executable on Windows, Linux, or macOS.

    Search priority:
    1. Explicit custom_path argument or KDENLIVE_PATH environment variable.
    2. System PATH (shutil.which).
    3. Standard Windows installation directories (%LOCALAPPDATA% and %PROGRAMFILES%).
    """
    # 1. Environment or argument override
    env_path = custom_path or os.getenv("KDENLIVE_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists() and p.is_file():
            return p.resolve()

    # 2. Discover via PATH
    which_path = shutil.which("kdenlive")
    if which_path:
        return Path(which_path).resolve()

    # 3. Known platform directories
    home = Path.home()
    system = sys.platform.lower()

    candidates = []

    if system.startswith("win") or os.name == "nt":
        program_files = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
        program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
        candidates.extend([
            home / "AppData/Local/Programs/Kdenlive/bin/kdenlive.exe",
            home / "AppData/Local/Programs/kdenlive/bin/kdenlive.exe",
            home / "AppData/Local/Programs/Kdenlive/kdenlive.exe",
            home / "AppData/Local/Programs/kdenlive/kdenlive.exe",
            program_files / "kdenlive/bin/kdenlive.exe",
            program_files / "Kdenlive/bin/kdenlive.exe",
            program_files / "kdenlive/kdenlive.exe",
            program_files / "Kdenlive/kdenlive.exe",
            program_files_x86 / "kdenlive/bin/kdenlive.exe",
            program_files_x86 / "Kdenlive/bin/kdenlive.exe",
        ])
    elif system.startswith("darwin"):
        candidates.extend([
            Path("/Applications/kdenlive.app/Contents/MacOS/kdenlive"),
            home / "Applications/kdenlive.app/Contents/MacOS/kdenlive",
            Path("/Applications/Kdenlive.app/Contents/MacOS/kdenlive"),
            home / "Applications/Kdenlive.app/Contents/MacOS/kdenlive",
        ])
    else:
        # Linux / Unix
        candidates.extend([
            Path("/usr/bin/kdenlive"),
            Path("/usr/local/bin/kdenlive"),
            Path("/snap/bin/kdenlive"),
            Path("/var/lib/flatpak/exports/bin/org.kde.kdenlive"),
            home / ".local/share/flatpak/exports/bin/org.kde.kdenlive",
        ])

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()

    return None


def open_in_kdenlive(project_path: Path, custom_exe: Optional[Path] = None) -> bool:
    """Launches Kdenlive with the specified project file in a non-blocking subprocess.

    Returns:
        True if Kdenlive was launched successfully, False otherwise.
    """
    resolved_project = project_path.resolve()
    if not resolved_project.exists():
        return False

    exe = custom_exe or find_kdenlive_executable()

    if exe and exe.exists():
        try:
            # Launch in background without blocking CLI execution
            subprocess.Popen(
                [str(exe), str(resolved_project)],
                creationflags=subprocess.DETACHED_PROCESS if os.name == "nt" else 0,
                close_fds=True,
            )
            return True
        except Exception:
            pass

    # Operating system shell fallbacks
    if os.name == "nt":
        try:
            os.startfile(str(resolved_project))
            return True
        except Exception:
            return False
    elif sys.platform.startswith("darwin"):
        try:
            subprocess.Popen(["open", str(resolved_project)], close_fds=True)
            return True
        except Exception:
            return False
    else:
        # Linux / BSD (xdg-open)
        xdg_path = shutil.which("xdg-open")
        if xdg_path:
            try:
                subprocess.Popen([xdg_path, str(resolved_project)], close_fds=True)
                return True
            except Exception:
                return False

    return False


def trigger_kdenlive_background_install() -> Optional[subprocess.Popen]:
    """Triggers background installation of Kdenlive via the native OS package manager if available.

    Returns the subprocess.Popen instance running the installer, or None if unavailable.
    """
    cmd = None

    if os.name == "nt":
        winget_path = shutil.which("winget")
        if winget_path:
            cmd = [
                winget_path,
                "install",
                "KDE.Kdenlive",
                "--silent",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ]
    elif sys.platform.startswith("darwin"):
        brew_path = shutil.which("brew")
        if brew_path:
            cmd = [brew_path, "install", "--cask", "kdenlive"]
    else:
        # Linux
        flatpak_path = shutil.which("flatpak")
        if flatpak_path:
            cmd = [flatpak_path, "install", "-y", "flathub", "org.kde.kdenlive"]

    if cmd:
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.DETACHED_PROCESS if os.name == "nt" else 0,
                close_fds=True,
            )
            return proc
        except Exception:
            return None

    return None
