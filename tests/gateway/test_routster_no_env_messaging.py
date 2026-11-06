"""Routster fork: a bot token in the environment (e.g. a Hermes install's) must not start
messaging in Routster's gateway; ``platforms.<x>.enabled: true`` in config.yaml still does."""

import pytest

from gateway.config import Platform, load_gateway_config

TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / ".routster"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    return home


def test_env_token_alone_does_not_enable_telegram(home):
    cfg = load_gateway_config()
    assert not getattr(cfg.platforms.get(Platform.TELEGRAM), "enabled", False)


def test_explicit_enable_still_works(home):
    (home / "config.yaml").write_text("platforms:\n  telegram:\n    enabled: true\n", encoding="utf-8")
    assert load_gateway_config().platforms[Platform.TELEGRAM].enabled
