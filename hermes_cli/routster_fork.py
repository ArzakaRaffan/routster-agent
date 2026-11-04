"""Routster fork: which upstream Hermes surfaces the Routster CLI does not offer.

Routster Agent is a coding agent in the terminal (plus the web dashboard) on a Routster key or the
user's own provider keys. Messaging platforms, the Nous account, the desktop app and novelty
features stay in the code (internals and upstream merges depend on them) but are not offered:
hidden subcommands still run when typed (`_parser.hide_fork_subcommands`), hidden slash commands
are dropped from the registry (`commands.py`).
Stdlib-only: ``hermes_cli.commands`` imports this and must stay import-light.
"""

from __future__ import annotations

HIDDEN_SUBCOMMANDS = frozenset({
    # messaging gateway and its platforms
    "gateway", "proxy", "whatsapp", "whatsapp-cloud", "slack", "send", "pairing", "peer",
    "monitoring", "webhook",
    # scheduler / multi-profile boards (run inside the gateway)
    "cron", "pause", "resume", "kanban",
    # Nous account and hosted services
    "portal", "connectors", "codex-runtime",
    # desktop app and its backend
    "desktop", "webapp", "serve",
    # novelty / niche
    "pets", "journey", "computer-use", "vault", "egress",
})

HIDDEN_SLASH_COMMANDS = frozenset({
    # messaging platforms
    "start", "topic", "handoff", "sethome", "whoami", "discard", "platforms", "platform",
    "footer", "restart",
    # Nous account
    "login", "topup", "subscription", "codex-runtime",
    # scheduler / boards
    "cron", "suggestions", "blueprint", "kanban",
    # novelty / niche
    "pet", "hatch", "journey", "wake", "egress",
})

