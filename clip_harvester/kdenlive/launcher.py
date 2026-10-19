"""Kdenlive application discovery and project launch engine."""

import os
import shutil
import subprocess
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

    # 3. Known Windows directories
    home = Path.home()
    program_files = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
    program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))

    candidates = [
        # User AppData Local Programs (Standard per-user installer)
        home / "AppData/Local/Programs/Kdenlive/bin/kdenlive.exe",
        home / "AppData/Local/Programs/kdenlive/bin/kdenlive.exe",
        home / "AppData/Local/Programs/Kdenlive/kdenlive.exe",
        home / "AppData/Local/Programs/kdenlive/kdenlive.exe",
        # System Program Files
        program_files / "kdenlive/bin/kdenlive.exe",
        program_files / "Kdenlive/bin/kdenlive.exe",
        program_files / "kdenlive/kdenlive.exe",
        program_files / "Kdenlive/kdenlive.exe",
        program_files_x86 / "kdenlive/bin/kdenlive.exe",
        program_files_x86 / "Kdenlive/bin/kdenlive.exe",
    ]

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

    # Windows shell fallback if direct executable invocation is unavailable
    if os.name == "nt":
        try:
            os.startfile(str(resolved_project))
            return True
        except Exception:
            return False

    return False


def trigger_kdenlive_background_install() -> Optional[subprocess.Popen]:
    """Triggers background installation of Kdenlive via winget if available.

    Returns the subprocess.Popen instance running the installer, or None if winget is unavailable.
    """
    if os.name != "nt":
        return None

    winget_path = shutil.which("winget")
    if not winget_path:
        return None

    try:
        cmd = [
            winget_path,
            "install",
            "KDE.Kdenlive",
            "--silent",
            "--accept-package-agreements",
            "--accept-source-agreements",
        ]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS,
        )
        return proc
    except Exception:
        return None
