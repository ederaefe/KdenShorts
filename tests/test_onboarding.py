"""Unit tests for interactive onboarding and live credential verification."""

from unittest.mock import MagicMock, patch

from clip_harvester.ui.onboarding import (
    render_kdenlive_tips_panel,
    save_api_key_permanently,
    validate_gemini_api_key,
    wait_for_downloader_with_progress,
)


def test_validate_gemini_api_key_success() -> None:
    """Verifies that validate_gemini_api_key returns True when the API ping succeeds."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "OK"
    mock_client.models.generate_content.return_value = mock_response

    with patch("clip_harvester.ui.onboarding.create_gemini_client", return_value=mock_client):
        valid, message = validate_gemini_api_key("valid-dummy-api-key")
        assert valid is True
        assert "authenticated" in message.lower()


def test_validate_gemini_api_key_failure() -> None:
    """Verifies that validate_gemini_api_key returns False when an API exception occurs."""
    with patch("clip_harvester.ui.onboarding.create_gemini_client", side_effect=ValueError("403 Forbidden")):
        valid, message = validate_gemini_api_key("bad-key")
        assert valid is False
        assert "403 Forbidden" in message


def test_render_kdenlive_tips_panel_does_not_crash() -> None:
    """Verifies that render_kdenlive_tips_panel renders without raising exceptions."""
    try:
        render_kdenlive_tips_panel()
    except Exception as exc:
        raise AssertionError(f"render_kdenlive_tips_panel raised an exception: {exc}")


def test_wait_for_downloader_already_finished_success() -> None:
    """Verifies wait_for_downloader_with_progress returns True if downloader succeeded."""
    mock_downloader = MagicMock()
    mock_downloader.is_finished.return_value = True
    mock_downloader.get_snapshot.return_value = (True, 100.0, "Ready", None)

    result = wait_for_downloader_with_progress(mock_downloader)
    assert result is True


def test_wait_for_downloader_already_finished_error() -> None:
    """Verifies wait_for_downloader_with_progress returns False if downloader encountered an error."""
    mock_downloader = MagicMock()
    mock_downloader.is_finished.return_value = True
    mock_downloader.get_snapshot.return_value = (True, 0.0, "Failed", "Network timeout")

    result = wait_for_downloader_with_progress(mock_downloader)
    assert result is False


def test_save_api_key_permanently_sets_env(monkeypatch) -> None:
    """Verifies that save_api_key_permanently sets GEMINI_API_KEY in os.environ on Windows."""
    import os

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    # Mock subprocess.run to avoid modifying the real Windows registry in tests
    with patch("subprocess.run"):
        save_api_key_permanently("test-key-12345")
        assert os.environ.get("GEMINI_API_KEY") == "test-key-12345"


def test_save_api_key_permanently_unix(tmp_path, monkeypatch) -> None:
    """Verifies that save_api_key_permanently appends export statement to shell RC file on Unix."""
    from pathlib import Path

    zshrc = tmp_path / ".zshrc"
    zshrc.write_text("# existing config\n", encoding="utf-8")

    with patch("os.name", "posix"), patch("pathlib.Path.home", return_value=tmp_path):
        saved = save_api_key_permanently("secret-gemini-key")
        assert saved is True
        content = zshrc.read_text(encoding="utf-8")
        assert 'export GEMINI_API_KEY="secret-gemini-key"' in content
