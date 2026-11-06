"""Bare `routster setup` on a fresh home: the Routster key + model step, nothing else asked."""

from argparse import Namespace
from unittest.mock import patch


def _fake_routster_step(config):
    """The real step validates a key and saves provider ``routster`` with a picked model."""
    from hermes_cli.config import save_config
    config["model"] = {"provider": "routster", "default": "routster/deepseek-v4.1-flash"}
    save_config(config)


def test_fresh_setup_asks_only_for_the_routster_key_and_model():
    from hermes_cli.config import load_config
    from hermes_cli.setup import run_setup_wizard

    with patch("hermes_cli.setup.is_interactive_stdin", return_value=True),             patch("hermes_cli.setup.prompt_choice") as menu,             patch("hermes_cli.setup.prompt_yes_no") as yes_no,             patch("hermes_cli.setup_quick._quick_setup_routster", side_effect=_fake_routster_step) as routster,             patch("hermes_cli.setup.setup_terminal_backend") as terminal,             patch("hermes_cli.setup.setup_tools") as tools,             patch("hermes_cli.setup.setup_gateway") as gateway:
        run_setup_wizard(Namespace(non_interactive=False, section=None, reset=False,
                                   reconfigure=False, quick=False))

    routster.assert_called_once()
    assert load_config()["model"]["provider"] == "routster"
    for mock in (menu, yes_no, terminal, tools, gateway):
        mock.assert_not_called()
