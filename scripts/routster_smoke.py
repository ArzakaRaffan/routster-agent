#!/usr/bin/env python3
"""Live smoke test against the real Routster gateway. SPENDS BALANCE (a few hundred tokens).

Never run by CI or ``scripts/run_tests.sh``. Usage::

    ROUTSTER_API_KEY=... python scripts/routster_smoke.py [--model routster/deepseek-v4.1-flash]

Checks, in order: the key (free), the public catalog (free), then one real agent task that needs a
tool call (``read_file``) on the cheapest default model, streamed.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", default="routster/deepseek-v4.1-flash")
    parser.add_argument("--base-url", default=os.environ.get("ROUTSTER_BASE_URL", "https://routster.trackster.dev/v1"))
    args = parser.parse_args()
    api_key = os.environ.get("ROUTSTER_API_KEY", "").strip()
    if not api_key:
        print("ROUTSTER_API_KEY is not set.", file=sys.stderr)
        return 2

    import model_tools  # registers provider plugins
    from providers import get_provider_profile

    plugin = sys.modules[type(get_provider_profile("routster")).__module__]
    ok, message = plugin.check_api_key(api_key, args.base_url)
    print(f"[1/3] key check: {message}")
    if not ok:
        return 1
    ids = [row["id"] for row in plugin.fetch_catalog(args.base_url)]
    print(f"[2/3] catalog: {len(ids)} models; {args.model} {'listed' if args.model in ids else 'NOT listed'}")

    from run_agent import AIAgent

    with tempfile.TemporaryDirectory() as work:
        secret = Path(work) / "secret.txt"
        secret.write_text("the password is PAPAYA-42\n", encoding="utf-8")
        agent = AIAgent(provider="routster", base_url=args.base_url, api_key=api_key, model=args.model,
                        session_id="routster-smoke", quiet_mode=True, platform="cli", skip_memory=True,
                        enabled_toolsets=["file"], max_iterations=4)
        try:
            result = agent.run_conversation(
                f"Use the read_file tool on {secret} and reply with only the password it contains.",
                conversation_history=[], task_id="smoke")
        finally:
            agent.close()
    answer = (result.get("final_response") or "").strip()
    print(f"[3/3] agent task: {answer[:200]!r}")
    return 0 if "PAPAYA-42" in answer else 1


if __name__ == "__main__":
    raise SystemExit(main())
