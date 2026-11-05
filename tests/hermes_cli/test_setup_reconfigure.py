"""`routster setup` routing (Routster fork).

- Bare `routster setup` (fresh or existing) runs only the Routster step: API key, then model.
  No mode menu, no agent import offer, no terminal/tools/gateway prompts.
- `routster setup --quick` on an existing install fills only missing items.
- `routster setup --reconfigure` on an existing install runs the full wizard.
"""

from argparse import Namespace
from contextlib import ExitStack
from unittest.mock import patch

import pytest


def _make_setup_args(**overrides):
    return Namespace(
        non_interactive=overrides.get("non_interactive", False),
        section=overrides.get("section", None),
        reset=overrides.get("reset", False),
        reconfigure=overrides.get("reconfigure", False),
        quick=overrides.get("quick", False),
    )


@pytest.fixture
def existing_install(tmp_path, monkeypatch):
    """Simulate a returning user with an existing configured install."""
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(home))
    return home


@pytest.fixture
def fresh_install(tmp_path, monkeypatch):
    """Simulate a first-time user with no existing configuration."""
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(home))
    return home


def _enter_existing_install_patches(stack, **extra):
    """Apply standard existing-install mocks via an ExitStack.

    Returns a dict of mocks from the `extra` kwargs (which map mock-name to
    target path) so callers can assert on them.
    """
    # Unconditional mocks (no return values to assert against).
    for target, kwargs in [
        ("hermes_cli.setup.ensure_hermes_home", {}),
        ("hermes_cli.setup.is_interactive_stdin", {"return_value": True}),
        ("hermes_cli.config.is_managed", {"return_value": False}),
        ("hermes_cli.setup.load_config", {"return_value": {}}),
        ("hermes_cli.setup.save_config", {}),
        ("hermes_cli.setup.get_env_value", {"return_value": None}),
        ("hermes_cli.auth.get_active_provider", {"return_value": "openrouter"}),
        ("hermes_cli.setup._print_setup_summary", {}),
    ]:
        stack.enter_context(patch(target, **kwargs))

    # Named mocks caller wants to assert on.
    named = {}
    for name, target in extra.items():
        named[name] = stack.enter_context(patch(target))
    return named


def _enter_fresh_install_patches(stack, **extra):
    for target, kwargs in [
        ("hermes_cli.setup.ensure_hermes_home", {}),
        ("hermes_cli.setup.is_interactive_stdin", {"return_value": True}),
        ("hermes_cli.config.is_managed", {"return_value": False}),
        ("hermes_cli.setup.load_config", {"return_value": {}}),
        ("hermes_cli.setup.save_config", {}),
        ("hermes_cli.auth.get_active_provider", {"return_value": None}),
        ("hermes_cli.setup.get_env_value", {"return_value": None}),
    ]:
        stack.enter_context(patch(target, **kwargs))

    named = {}
    for name, target_spec in extra.items():
        if isinstance(target_spec, tuple):
            target, kwargs = target_spec
            named[name] = stack.enter_context(patch(target, **kwargs))
        else:
            named[name] = stack.enter_context(patch(target_spec))
    return named


class TestBareSetup:
    """Bare `routster setup` = the Routster step only, fresh or existing."""

    @pytest.mark.parametrize("install", ["fresh_install", "existing_install"])
    def test_bare_setup_runs_only_the_routster_step(self, install, request):
        request.getfixturevalue(install)
        enter = _enter_fresh_install_patches if install == "fresh_install" else _enter_existing_install_patches
        with ExitStack() as stack:
            m = enter(
                stack,
                prompt_choice="hermes_cli.setup.prompt_choice",
                first="hermes_cli.setup_quick._run_first_time_quick_setup",
                model="hermes_cli.setup.setup_model_provider",
                terminal="hermes_cli.setup.setup_terminal_backend",
                tools="hermes_cli.setup.setup_tools",
                gateway="hermes_cli.setup.setup_gateway",
            )
            from hermes_cli import setup as setup_mod

            section_indexes = []
            m["first"].side_effect = lambda *_args: section_indexes.append(
                setup_mod._SETUP_NAVIGATION.get().section_index
            )
            setup_mod.run_setup_wizard(_make_setup_args())

        m["first"].assert_called_once()
        assert section_indexes == [0]
        for name in ("prompt_choice", "model", "terminal", "tools", "gateway"):
            m[name].assert_not_called()

    def test_reconfigure_on_fresh_install_is_still_the_routster_step(self, fresh_install):
        with ExitStack() as stack:
            m = _enter_fresh_install_patches(
                stack, first="hermes_cli.setup_quick._run_first_time_quick_setup",
                model="hermes_cli.setup.setup_model_provider",
            )
            from hermes_cli.setup import run_setup_wizard
            run_setup_wizard(_make_setup_args(reconfigure=True))

        m["first"].assert_called_once()
        m["model"].assert_not_called()


class TestExistingInstallFlags:
    def test_reconfigure_runs_the_full_wizard(self, existing_install):
        with ExitStack() as stack:
            m = _enter_existing_install_patches(
                stack,
                first="hermes_cli.setup_quick._run_first_time_quick_setup",
                model="hermes_cli.setup.setup_model_provider",
                terminal="hermes_cli.setup.setup_terminal_backend",
                agent="hermes_cli.setup.setup_agent_settings",
                tools="hermes_cli.setup.setup_tools",
            )
            from hermes_cli.setup import run_setup_wizard
            run_setup_wizard(_make_setup_args(reconfigure=True))

        m["first"].assert_not_called()
        m["model"].assert_called_once()
        m["terminal"].assert_called_once()
        m["tools"].assert_called_once()
        m["agent"].assert_not_called()

    def test_quick_flag_runs_quick_setup_only(self, existing_install):
        with ExitStack() as stack:
            m = _enter_existing_install_patches(
                stack,
                quick="hermes_cli.setup._run_quick_setup",
                first="hermes_cli.setup_quick._run_first_time_quick_setup",
                model="hermes_cli.setup.setup_model_provider",
            )
            from hermes_cli.setup import run_setup_wizard
            run_setup_wizard(_make_setup_args(quick=True))

        m["quick"].assert_called_once()
        m["first"].assert_not_called()
        m["model"].assert_not_called()


class TestArgparse:
    """The flags are plumbed through argparse to cmd_setup."""

    def test_reconfigure_flag_reaches_cmd_setup(self, monkeypatch):
        import sys
        from hermes_cli.main import main

        captured = {}
        monkeypatch.setattr(
            "hermes_cli.setup.run_setup_wizard",
            lambda args: captured.setdefault("args", args),
        )
        monkeypatch.setattr(sys, "argv", ["hermes", "setup", "--reconfigure"])
        try:
            main()
        except SystemExit:
            pass
        assert captured["args"].reconfigure is True
        assert captured["args"].quick is False
