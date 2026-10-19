"""Unit tests for model resolution and aliases."""

import os
from clip_harvester.config import MODEL_ALIASES, resolve_model_name


def test_resolve_model_name_aliases():
    assert resolve_model_name("flash") == "gemini-2.5-flash"
    assert resolve_model_name("flash-latest") == "gemini-2.5-flash"
    assert resolve_model_name("FLASH") == "gemini-2.5-flash"
    assert resolve_model_name("pro") == "gemini-2.5-pro"
    assert resolve_model_name("pro-latest") == "gemini-2.5-pro"


def test_resolve_model_name_custom_passthrough():
    assert resolve_model_name("gemini-2.5-flash") == "gemini-2.5-flash"
    assert resolve_model_name("custom-model-id") == "custom-model-id"
    assert resolve_model_name("gemini-3.0-flash") == "gemini-3.0-flash"
