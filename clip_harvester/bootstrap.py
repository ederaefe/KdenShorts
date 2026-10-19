"""Zero-dependency environment bootstrap, OS detection, and package auto-installer."""

import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class OSInfo:
    """Operating system metadata and tailored dependency management commands."""

    os_type: str  # "windows", "macos", "linux", "unknown"
    display_name: str  # e.g., "Windows 11 (AMD64)", "macOS 14.4", "Ubuntu 22.04 LTS"
    distro: Optional[str]  # e.g., "debian", "fedora", "arch", or None
    architecture: str  # e.g., "AMD64", "arm64", "x86_64"
    pip_install_cmd: str  # Tailored command to install Python packages
    ffmpeg_install_cmd: str  # Tailored command to install FFmpeg
    kdenlive_install_cmd: str  # Tailored command to install Kdenlive


def get_linux_distro() -> Tuple[str, str]:
    """Detects Linux distribution family and display name from /etc/os-release."""
    if os.path.exists("/etc/os-release"):
        try:
            with open("/etc/os-release", "r", encoding="utf-8") as f:
                content = f.read()
            data = {}
            for line in content.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    data[k.strip()] = v.strip().strip('"').strip("'")

            pretty_name = data.get("PRETTY_NAME", "Linux")
            id_like = (data.get("ID_LIKE", "") + " " + data.get("ID", "")).lower()

            if any(x in id_like for x in ["ubuntu", "debian", "mint", "pop"]):
                return "debian", pretty_name
            if any(x in id_like for x in ["fedora", "rhel", "centos", "rocky"]):
                return "fedora", pretty_name
            if any(x in id_like for x in ["arch", "manjaro", "endeavouros"]):
                return "arch", pretty_name
            if any(x in id_like for x in ["suse", "opensuse"]):
                return "suse", pretty_name
            return "generic", pretty_name
        except Exception:
            pass
    return "generic", f"Linux ({platform.release()})"


def detect_os_info() -> OSInfo:
    """Detects current operating system and produces tailored install commands."""
    system = platform.system()
    machine = platform.machine() or "x86_64"

    if system == "Windows":
        release = platform.release()
        return OSInfo(
            os_type="windows",
            display_name=f"Windows {release} ({machine})",
            distro=None,
            architecture=machine,
            pip_install_cmd="py -m pip install -r requirements.txt",
            ffmpeg_install_cmd="winget install Gyan.FFmpeg",
            kdenlive_install_cmd="winget install KDE.Kdenlive",
        )
    elif system == "Darwin":
        mac_ver = platform.mac_ver()[0] or "macOS"
        return OSInfo(
            os_type="macos",
            display_name=f"macOS {mac_ver} ({machine})",
            distro=None,
            architecture=machine,
            pip_install_cmd="pip3 install -r requirements.txt",
            ffmpeg_install_cmd="brew install ffmpeg",
            kdenlive_install_cmd="brew install --cask kdenlive",
        )
    elif system == "Linux":
        distro_family, pretty_name = get_linux_distro()
        if distro_family == "debian":
            ffmpeg_cmd = "sudo apt update && sudo apt install -y ffmpeg"
            kdenlive_cmd = "sudo apt update && sudo apt install -y kdenlive"
            pip_cmd = "pip3 install -r requirements.txt"
        elif distro_family == "fedora":
            ffmpeg_cmd = "sudo dnf install -y ffmpeg"
            kdenlive_cmd = "sudo dnf install -y kdenlive"
            pip_cmd = "pip3 install -r requirements.txt"
        elif distro_family == "arch":
            ffmpeg_cmd = "sudo pacman -S --noconfirm ffmpeg"
            kdenlive_cmd = "sudo pacman -S --noconfirm kdenlive"
            pip_cmd = "pip install -r requirements.txt"
        elif distro_family == "suse":
            ffmpeg_cmd = "sudo zypper install -y ffmpeg"
            kdenlive_cmd = "sudo zypper install -y kdenlive"
            pip_cmd = "pip3 install -r requirements.txt"
        else:
            ffmpeg_cmd = "sudo [package-manager] install ffmpeg"
            kdenlive_cmd = "sudo [package-manager] install kdenlive"
            pip_cmd = "pip3 install -r requirements.txt"

        return OSInfo(
            os_type="linux",
            display_name=f"{pretty_name} ({machine})",
            distro=distro_family,
            architecture=machine,
            pip_install_cmd=pip_cmd,
            ffmpeg_install_cmd=ffmpeg_cmd,
            kdenlive_install_cmd=kdenlive_cmd,
        )
    else:
        return OSInfo(
            os_type="unknown",
            display_name=f"Unknown OS ({system})",
            distro=None,
            architecture=machine,
            pip_install_cmd="pip install -r requirements.txt",
            ffmpeg_install_cmd="Install ffmpeg via system package manager",
            kdenlive_install_cmd="Install Kdenlive from https://kdenlive.org",
        )


# Mapping of module import names to human description and pip specifier
REQUIRED_PYTHON_MODULES: Dict[str, Tuple[str, str]] = {
    "google.genai": ("google-genai>=1.0.0", "Google Gemini Multimodal Audio SDK"),
    "rich": ("rich>=13.0.0", "Terminal UI & Curation Table"),
    "pydantic": ("pydantic>=2.0.0", "Structured Schema Validation"),
}


def check_missing_python_modules() -> List[Tuple[str, str, str]]:
    """Returns a list of (module_name, pip_specifier, description) that are currently missing."""
    missing = []
    for mod_name, (pip_spec, desc) in REQUIRED_PYTHON_MODULES.items():
        try:
            __import__(mod_name)
        except ImportError:
            missing.append((mod_name, pip_spec, desc))
    return missing


def auto_install_packages(packages: List[str]) -> bool:
    """Attempts to install missing Python packages using current Python executable's pip."""
    try:
        cmd = [sys.executable, "-m", "pip", "install", *packages]
        result = subprocess.run(cmd)
        return result.returncode == 0
    except Exception:
        return False


def ensure_environment() -> None:
    """Bootstraps the Python runtime environment, auto-installing missing packages if needed."""
    missing = check_missing_python_modules()
    if not missing:
        return

    os_info = detect_os_info()

    print("=" * 68)
    print(" KdenShorts :: Environment Bootstrap")
    print(f" Detected OS: {os_info.display_name}")
    print("=" * 68)
    print("[!] Missing required Python dependencies:")
    for _, pip_spec, desc in missing:
        print(f"     [•] {pip_spec:<22} ({desc})")
    print()
    print("[*] Initiating automatic installation via pip...")
    print("-" * 68)

    specs = [spec for _, spec, _ in missing]
    installed_ok = auto_install_packages(specs)

    if installed_ok:
        print("-" * 68)
        print("[OK] All required dependencies installed successfully.")
        print("[OK] Starting KdenShorts...\n")
    else:
        print("-" * 68)
        print("[ERR] Automatic dependency installation could not be completed.")
        print()
        print(f"Please install the prerequisites for your detected system ({os_info.display_name}):")
        print(f"    {os_info.pip_install_cmd}")
        print()
        print("Then re-run: python kdenshorts.py\n")
        sys.exit(1)
