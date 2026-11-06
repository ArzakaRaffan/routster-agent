"""``routster login`` subcommand parser."""

from __future__ import annotations

import argparse
from typing import Callable


def build_login_parser(subparsers, *, cmd_login: Callable) -> None:
    """Attach ``login``: validate + save a Routster API key and make Routster the default provider.

    Upstream Hermes keeps ``login`` as a hidden deprecation stub; this fork gives it back a job."""
    login_parser = subparsers.add_parser(
        "login", help="Sign in to Routster with an API key",
        description="Validate and save a Routster API key (https://routster.trackster.dev/dashboard) "
            "and make Routster the default provider. Without --api-key the key is asked for (hidden "
            "input); ROUTSTER_API_KEY is also picked up.")
    login_parser.add_argument(
        "--api-key", default=None,
        help="API key to save (prefer the hidden prompt or ROUTSTER_API_KEY: argv lands in shell history)")
    login_parser.add_argument(
        "--base-url", default=None, help="Gateway base URL (default: https://routster.trackster.dev/v1)")
    login_parser.add_argument(
        "--model", default=None, help="Default model to save (default: routster/deepseek-v4.1-flash)")
    # ``--provider`` is still accepted so old ``hermes login --provider X`` scripts get a clear
    # message instead of argparse's ``unrecognized arguments``.
    login_parser.add_argument("--provider", default=None, help=argparse.SUPPRESS)
    login_parser.set_defaults(func=cmd_login)

