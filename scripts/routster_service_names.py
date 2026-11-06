#!/usr/bin/env python3
"""Give Routster its own service names, so a Hermes install on the same account never shares a unit:
systemd ``hermes-gateway*``/``hermes-serve*``/``hermes-dashboard*`` -> ``routster-*``, launchd
``ai.hermes.gateway*`` -> ``ai.routster.gateway*``, the ``Hermes_Gateway`` Scheduled Task ->
``Routster_Gateway``. Only string literals change (not docstrings or comments). Idempotent; rerun after
every upstream merge (``--check`` exits 1 when anything is left):

    python scripts/routster_service_names.py [--check] [paths...]

Left alone: the ``hermes-gateway`` toolset, lock kind, OTLP service name, thread names and exe shim;
the ``hermes-gateway-v1`` wire protocol and ``-ticket`` files; the per-home named pipe.
"""
from __future__ import annotations

import argparse
import io
import re
import subprocess
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Files whose "hermes-gateway" literals are not service names.
_SKIP = {"toolsets.py", "gateway/status.py", "gateway/run.py", "agent/monitoring/otlp_exporter.py",
         "hermes_cli/config_defaults.py", "hermes_cli/profiles.py", "gateway/control_socket.py",
         "hermes_cli/main_install_repair.py", "agent/curator.py", "scripts/routster_service_names.py"}
_UNIT = re.compile(r"(?<![\\\w])hermes-(gateway|serve|dashboard)"
                   r"(?!-(?:v\d|ticket|smoke|metrics|loop|hk|heartbeat|health|command|theme|font|audit)|[\w.]exe|\w)")
_LABEL = re.compile(r"\bai\.hermes\.(?=gateway|dashboard|[\"']|$)")
_TASK = re.compile(r"\bHermes_Gateway")


def rename(text: str) -> str:
    return _TASK.sub("Routster_Gateway", _LABEL.sub("ai.routster.", _UNIT.sub(r"routster-\1", text)))


def _is_docstring(tokens, index) -> bool:
    prev = next((t for t in reversed(tokens[:index]) if t.type not in (tokenize.NL, tokenize.COMMENT)), None)
    nxt = next((t for t in tokens[index + 1:] if t.type not in (tokenize.NL, tokenize.COMMENT)), None)
    starts = prev is None or prev.type in (tokenize.INDENT, tokenize.DEDENT, tokenize.NEWLINE)
    return starts and nxt is not None and nxt.type in (tokenize.NEWLINE, tokenize.ENDMARKER)


def rewrite_source(source: str) -> str:
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    middle = getattr(tokenize, "FSTRING_MIDDLE", None)
    edits = []
    for index, token in enumerate(tokens):
        if token.type == tokenize.STRING and _is_docstring(tokens, index):
            continue
        if token.type != tokenize.STRING and token.type != middle:
            continue
        new = rename(token.string)
        start = offsets[token.start[0] - 1] + token.start[1]
        end = offsets[token.end[0] - 1] + token.end[1]
        if new != token.string and source[start:end] == token.string:
            edits.append((start, end, new))
    for start, end, new in reversed(edits):
        source = source[:start] + new + source[end:]
    return source


def default_paths():
    listed = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True, text=True, check=True)
    for name in listed.stdout.split():
        if name in _SKIP or name.startswith(("tests/", "website/", "evals/", "scripts/releases/")):
            continue
        yield ROOT / name


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args(argv)
    changed = []
    for path in args.paths or default_paths():
        with open(path, encoding="utf-8", newline="") as handle:
            source = handle.read()
        new = rewrite_source(source)
        if new != source:
            changed.append(path)
            if not args.check:
                with open(path, "w", encoding="utf-8", newline="") as handle:
                    handle.write(new)
    for path in changed:
        print(path)
    print(f"{len(changed)} file(s) {'need renaming' if args.check else 'renamed'}", file=sys.stderr)
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
