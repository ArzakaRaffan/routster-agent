"""Routster fork surface: hidden upstream features stay runnable but are not offered."""

from hermes_cli.commands import COMMAND_REGISTRY, resolve_command
from hermes_cli.config_defaults import DEFAULT_CONFIG
from hermes_cli.main import _build_cli_parser
from hermes_cli.routster_fork import HIDDEN_SUBCOMMANDS
from hermes_cli.skin_engine import load_skin


def test_hidden_subcommands_leave_help_but_still_parse():
    parser, _subparsers = _build_cli_parser()
    help_text = parser.format_help()
    assert "Messaging gateway management" not in help_text
    assert "Nous Portal" not in help_text
    assert "Interactive chat with the agent" in help_text
    # Internals relaunch hidden commands (gateway, serve), so they must keep parsing.
    assert parser.parse_args(["gateway", "status"]).command == "gateway"
    assert {"gateway", "portal", "kanban"} <= HIDDEN_SUBCOMMANDS


def test_nous_and_messaging_slash_commands_are_not_offered():
    names = {cmd.name for cmd in COMMAND_REGISTRY}
    assert not names & {"topup", "subscription", "login", "handoff", "kanban", "pet"}
    assert resolve_command("topup") is None
    assert resolve_command("model") is not None


def test_routster_skin_is_the_default_and_carries_the_brand():
    assert DEFAULT_CONFIG["display"]["skin"] == "routster"
    skin = load_skin("routster")
    assert skin.get_branding("agent_name") == "Routster Agent"
    assert skin.get_color("ui_accent") == "#8FE6B3"
    assert "██████╗" in skin.banner_logo
