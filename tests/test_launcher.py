"""Unit tests for Kdenlive executable discovery and launch logic."""

from pathlib import Path
from clip_harvester.kdenlive.launcher import find_kdenlive_executable, open_in_kdenlive


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
