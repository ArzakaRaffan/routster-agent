#!/usr/bin/env python3
"""Rewrite user-visible Hermes branding in Python string literals, locale files and
skills to Routster.

Only string literals change: comments, docstrings, identifiers, module names and paths stay
upstream's, so an upstream merge conflicts only on rewritten text. After merging upstream, take
upstream's side of a conflicted string and run this again (it is idempotent):

    python scripts/routster_rebrand.py            # rewrite in place
    python scripts/routster_rebrand.py --check    # exit 1 if anything is left to rewrite

Left alone on purpose: wire contracts (``X-Hermes-*`` headers, ``Hermes-Agent/…`` user agents),
the Hermes desktop app (``Hermes.app``, "Hermes Desktop"), Nous models (``Hermes 3``,
``NousResearch/Hermes-4-70B``), credits naming Nous Research, and strings that are exactly
``hermes``/``Hermes`` (program and app identifiers).
"""
from __future__ import annotations

import argparse
import io
import re
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIRS = ("hermes_cli", "gateway", "agent", "tools", "tui_gateway", "cron", "plugins",
               "acp_adapter", "pm", "providers")
SOURCE_FILES = ("cli.py", "run_agent.py", "model_tools.py", "toolsets.py", "hermes_constants.py",
                "hermes_logging.py", "hermes_state.py", "utils.py")

# `hermes <subcommand>`: a command the user is told to run. Only `routster` is on PATH. Top-level
# names from the live parser (plus plugin-registered ones); add new upstream commands here.
_SUBCOMMANDS = (
    "whatsapp-cloud|codex-runtime|computer-use|import-agent|memory-graph|checkpoints|prompt-size|"
    "completion|connectors|monitoring|approvals|dashboard|providers|uninstall|fallback|insights|"
    "learning|security|sessions|whatsapp|worktree|browser|bundles|console|curator|desktop|gateway|"
    "journey|migrate|pairing|plugins|profile|project|secrets|version|webhook|backup|config|doctor|"
    "egress|honcho|import|kanban|logout|memory|photon|portal|resume|skills|status|update|verify|"
    "webapp|debug|hooks|login|model|pause|proxy|serve|setup|slack|tools|usage|vault|auth|chat|claw|"
    "cron|dump|init|logs|meet|peer|pets|send|skin|acp|bot|gui|lsp|mcp|moa|tui|pm|"
    r"-p|--profile|-c|--continue|--resume|-z|--help|-m|--model|-q|--version|-w|--worktree|--cli|--tui|--yolo"
)
# A literal's source spells a newline as backslash-n: that "n" is an escape, not a letter.
_AFTER_ESCAPE = r"(?<=\\[nrt])"
_COMMAND = re.compile(r"(?:(?<![\w./~\\$-])|" + _AFTER_ESCAPE + r")hermes(?= (?:(?:" + _SUBCOMMANDS + r")(?![\w-])|<|\{))")
# A quoted bare command inside prose: Run `hermes` / Run 'hermes' to start. A single-quoted 'hermes'
# without a run verb is a name (the image's user, a model, a profile), so it stays.
_QUOTED_COMMAND = re.compile(
    r"(?<=`)hermes(?=`)|(?:(?<=[Rr]un ')|(?<=next ')|(?<=[Tt]ype ')|(?<=[Rr]un: '))hermes(?=')")
# Outside a Python literal a quoted 'hermes' is usually code (an enum value): only `hermes` is prose.
_BACKTICK_COMMAND = re.compile(r"(?<=`)hermes(?=`)")
_PRODUCT = re.compile(r"\bHermes Agent\b")
_NAME = re.compile(
    r"(?:(?<![\w./-])|" + _AFTER_ESCAPE + r")(?<!X-)(?<![Hh]ey )Hermes(?![\w/-])"  # "Hey Hermes" is the wake word the model hears
    r"(?!\.app)(?! \d)(?! (?:Desktop|desktop|Console|Native|Relay|Webapp|Local Signi|plugin catalog))"
)
# The whole literal is skipped when it credits or links upstream.
_UPSTREAM = re.compile(r"Nous ?Research|nousresearch", re.IGNORECASE)
_IDENTIFIER = {"hermes", "Hermes"}
# Skill frontmatter authorship is a credit, not branding.
_CREDIT_LINE = re.compile(r"\s*(?:authors?|maintainers?)\s*:", re.IGNORECASE)


def rewrite_text(text: str, *, literal: bool = True) -> str:
    if text.strip() in _IDENTIFIER or _UPSTREAM.search(text):
        return text
    text = _COMMAND.sub("routster", text)
    text = (_QUOTED_COMMAND if literal else _BACKTICK_COMMAND).sub("routster", text)
    text = _PRODUCT.sub("Routster Agent", text)
    return _NAME.sub("Routster", text)


def _is_docstring(tokens: list, index: int) -> bool:
    prev = next((t for t in reversed(tokens[:index]) if t.type not in (tokenize.NL, tokenize.COMMENT)), None)
    nxt = next((t for t in tokens[index + 1:] if t.type not in (tokenize.NL, tokenize.COMMENT)), None)
    starts_statement = prev is None or prev.type in (tokenize.INDENT, tokenize.DEDENT, tokenize.NEWLINE)
    return starts_statement and nxt is not None and nxt.type in (tokenize.NEWLINE, tokenize.ENDMARKER)


def _string_body(token: str) -> tuple[str, str, str]:
    """Split a STRING token into (prefix+quote, body, quote). Raw strings keep their body as-is."""
    match = re.match(r"(?is)([a-z]*)('''|\"\"\"|'|\")", token)
    opener = match.group(0)
    quote = match.group(2)
    return opener, token[len(opener):len(token) - len(quote)], quote


def rewrite_source(source: str) -> str:
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    fstring_middle = getattr(tokenize, "FSTRING_MIDDLE", None)
    edits = []
    for index, token in enumerate(tokens):
        if token.type == tokenize.STRING:
            if _is_docstring(tokens, index):
                continue
            opener, body, quote = _string_body(token.string)
            if re.search(r"[rRbB]", opener):  # regexes and wire bytes keep upstream's spelling
                continue
            new = opener + rewrite_text(body) + quote
        elif fstring_middle is not None and token.type == fstring_middle:
            # f"hermes {selector}auth add": the middle ends where a replacement field starts.
            field_next = index + 1 < len(tokens) and tokens[index + 1].string == "{"
            new = rewrite_text(token.string + "{")[:-1] if field_next else rewrite_text(token.string)
        else:
            continue
        if new != token.string:
            start = offsets[token.start[0] - 1] + token.start[1]
            end = offsets[token.end[0] - 1] + token.end[1]
            if source[start:end] != token.string:  # FSTRING_MIDDLE un-doubles braces: skip those
                continue
            edits.append((start, end, new))
    for start, end, new in reversed(edits):
        source = source[:start] + new + source[end:]
    return source


def rewrite_lines(source: str) -> str:
    """Locale YAML and skill Markdown, line by line: locale keys never hold a spaced command or a
    capitalised name, and a skill line linking or crediting upstream is skipped like a literal."""
    return "".join(line if _CREDIT_LINE.match(line) else rewrite_text(line, literal=False)
                   for line in source.splitlines(keepends=True))


def iter_sources():
    for name in SOURCE_DIRS:
        for path in sorted((ROOT / name).rglob("*.py")):
            if "tests" not in path.relative_to(ROOT).parts:
                yield path
    for name in SOURCE_FILES:
        yield ROOT / name
    yield from sorted((ROOT / "locales").glob("*.yaml"))
    # Skills are instructions the agent follows: a `hermes …` line there is a command it would run.
    for name in ("skills", "optional-skills"):
        yield from (p for p in sorted((ROOT / name).rglob("*.md")) if p.name != "AGENTS.md")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report files left to rewrite, change nothing")
    args = parser.parse_args(argv)
    changed = []
    for path in iter_sources():
        with open(path, encoding="utf-8", newline="") as handle:
            source = handle.read()
        new = rewrite_source(source) if path.suffix == ".py" else rewrite_lines(source)
        if new != source:
            changed.append(path.relative_to(ROOT))
            if not args.check:
                with open(path, "w", encoding="utf-8", newline="") as handle:
                    handle.write(new)
    for path in changed:
        print(path)
    print(f"{len(changed)} file(s) {'need rewriting' if args.check else 'rewritten'}", file=sys.stderr)
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
