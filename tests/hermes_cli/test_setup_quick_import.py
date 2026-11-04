"""First-time Quick Setup after an agent import: a model the import brought is kept by default
instead of being replaced by the Routster key/model step (Routster Agent: was Nous Portal)."""

from argparse import Namespace
from unittest.mock import patch

import pytest


def _fake_import(_hermes_home):
    """What an agent import leaves behind: a model in config.yaml and its key in .env."""
    from hermes_cli.config import load_config, save_config, save_env_value
    config = load_config()
    config["model"] = {"provider": "openrouter", "default": "anthropic/claude-sonnet-4.5"}
    save_config(config)
    save_env_value("OPENROUTER_API_KEY", "sk-or-demo-not-a-real-key")
    return "OpenClaw"


def _fake_routster_step(config):
    """The real step validates a key and saves provider ``routster`` with a picked model."""
    from hermes_cli.config import save_config
    config["model"] = {"provider": "routster", "default": "routster/deepseek-v4.1-flash"}
    save_config(config)


@pytest.mark.parametrize("switch, routster_runs, expected_model", [
    (False, 0, {"provider": "openrouter", "default": "anthropic/claude-sonnet-4.5"}),
    (True, 1, {"provider": "routster", "default": "routster/deepseek-v4.1-flash"}),
])
def test_quick_setup_keeps_imported_model_unless_user_switches(switch, routster_runs, expected_model):
    from hermes_cli.config import get_env_value, load_config
    from hermes_cli.setup import run_setup_wizard

    questions = []

    def answer(question, choices, default=0, description=None):
        # Enter on every menu (the mode menu's default is Quick Setup), except the keep/switch
        # question when the test switches.
        questions.append(question)
        if switch and "switch to Routster" in question:
            return 1
        return default

    with patch("hermes_cli.setup.is_interactive_stdin", return_value=True), \
            patch("hermes_cli.setup.offer_agent_import", side_effect=_fake_import), \
            patch("hermes_cli.setup.prompt_choice", side_effect=answer), \
            patch("hermes_cli.setup_quick._quick_setup_routster", side_effect=_fake_routster_step) as routster, \
            patch("hermes_cli.setup.setup_terminal_backend") as terminal, \
            patch("hermes_cli.setup.setup_gateway") as gateway, \
            patch("hermes_cli.setup._print_setup_summary"), \
            patch("hermes_cli.setup._record_setup_completed"):
        run_setup_wizard(Namespace(non_interactive=False, section=None, reset=False,
                                   reconfigure=False, quick=False))

    assert routster.call_count == routster_runs
    model = load_config()["model"]
    assert {k: model.get(k) for k in expected_model} == expected_model
    assert get_env_value("OPENROUTER_API_KEY") == "sk-or-demo-not-a-real-key"
    terminal.assert_called_once()  # the rest of Quick Setup still runs
    gateway.assert_not_called()  # Routster Agent's Quick Setup offers no messaging step
    assert any("Keep your imported model (OpenRouter · anthropic/claude-sonnet-4.5)" in q
               for q in questions), questions
