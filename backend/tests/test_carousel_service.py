from types import SimpleNamespace

import pytest

from app.services import carousel


def _raw_config():
    return {
        "title": "My Carousel",
        "profile": {"display_name": "Creator", "handle": "@creator"},
        "slides": [
            {"type": "hook", "text": "Hook *line*"},
            {"type": "body", "title": "Body 1", "bullets": ["One", "Two", "Three"]},
            {"type": "body", "title": "Body 2", "text": "Body text"},
            {"type": "body", "title": "Body 3", "text": "More text"},
            {"type": "body", "title": "Body 4", "text": "More text"},
            {"type": "cta", "text": "CTA", "cta_action": 'Comment *"GUIDE"* and I\'ll DM you the link'},
        ],
    }


def test_list_templates_includes_expected_defaults():
    templates = carousel.list_templates()
    template_ids = {item["id"] for item in templates}
    assert "viral-dark" in template_ids
    assert "navy-clean" in template_ids


def test_get_template_unknown_raises():
    with pytest.raises(carousel.CarouselError):
        carousel.get_template_or_raise("missing-template")


def test_generate_config_claude_path(monkeypatch):
    user = SimpleNamespace(email="tester@example.com")
    monkeypatch.setattr(carousel, "_generate_with_claude", lambda *args, **kwargs: _raw_config())

    config, provider = carousel.generate_config("viral-dark", "Topic", user)
    assert provider == "claude"
    assert config["renderer"] == "render_viral_with_green.py"
    assert len(config["slides"]) == 6
    assert config["slides"][0]["type"] == "hook"
    assert config["slides"][5]["type"] == "cta"


def test_generate_config_deepseek_fallback(monkeypatch):
    user = SimpleNamespace(email="tester@example.com")

    def fail_claude(*args, **kwargs):
        raise carousel.CarouselError("claude unavailable")

    monkeypatch.setattr(carousel, "_generate_with_claude", fail_claude)
    monkeypatch.setattr(carousel, "_generate_with_deepseek", lambda *args, **kwargs: _raw_config())

    config, provider = carousel.generate_config("navy-clean", "Topic", user)
    assert provider == "deepseek"
    assert config["renderer"] == "render.py"
