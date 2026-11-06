"""A real ``AIAgent`` turn on the Routster provider against a recording fake gateway.

Pins the gateway contract the Routster profile exists for: every main request carries an explicit
``max_tokens`` (the gateway silently caps an omitted one at 1024), the client identifies as
``routster-agent``, a streamed tool call round-trips through a real tool, and Routster's
rejections end the turn the right way (no retry storm on a bad key or an empty balance, backoff on
the per-key rate limit).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.e2e.core.history._helpers import NO_BACKGROUND_REVIEW, OFFLINE_CONFIG
from tests.fakes.fake_llm_provider import FakeLLMServer, Raw, Text, ToolCall

MODEL = "routster/deepseek-v4.1-flash"


def _error(status: int, **error) -> Raw:
    return Raw(body=json.dumps({"error": error}), status=status, content_type="application/json")


def _turn(script, prompt="hi", *, retries: int = 1):
    from run_agent import AIAgent

    home = Path(os.environ["HERMES_HOME"])
    with FakeLLMServer(script) as srv:
        home.mkdir(parents=True, exist_ok=True)
        (home / "config.yaml").write_text(
            f"model:\n  provider: routster\n  base_url: {srv.base_url}\n  default: {MODEL}\n"
            f"  context_length: 128000\nagent:\n  api_max_retries: {retries}\n"
            + OFFLINE_CONFIG + NO_BACKGROUND_REVIEW, encoding="utf-8")
        agent = AIAgent(provider="routster", base_url=srv.base_url, api_key="rk-fake", model=MODEL,
                        session_id="routster-e2e", quiet_mode=True, platform="cli", skip_memory=True)
        try:
            result = agent.run_conversation(prompt, conversation_history=[], task_id="t")
        finally:
            agent.close()
        main = [r for r in srv.requests if r["kind"] == "main"]
    return result, main


def test_streamed_tool_call_round_trips_with_explicit_max_tokens(tmp_path):
    target = tmp_path / "hello.txt"
    target.write_text("the word is BANANA\n", encoding="utf-8")
    result, main = _turn([ToolCall("read_file", {"path": str(target)}), Text("File says BANANA.")],
                         prompt=f"read {target}")

    assert result.get("completed") and result.get("final_response") == "File says BANANA.", result
    assert len(main) == 2
    assert all(r["body"].get("max_tokens") == 8192 for r in main), [r["body"].get("max_tokens") for r in main]
    assert all(r["body"].get("model") == MODEL for r in main)
    assert all(r["headers"].get("user-agent", "").startswith("routster-agent/") for r in main)
    tool_messages = [m for m in main[1]["body"]["messages"] if m.get("role") == "tool"]
    assert tool_messages and "BANANA" in json.dumps(tool_messages[-1].get("content"))


@pytest.mark.parametrize("status,error,expect", [
    (401, {"message": "invalid api key"}, "API key"),
    (402, {"message": "token balance exhausted. top up first.", "type": "quota"}, "routster.trackster.dev/dashboard"),
    (429, {"message": "24h token quota reached (1000 tokens).", "type": "quota"}, "quota"),
], ids=["bad-key", "balance-empty", "key-quota"])
def test_terminal_rejections_end_the_turn_without_retrying(status, error, expect):
    result, main = _turn([_error(status, **error)] * 5, retries=3)

    assert result.get("failed"), result
    assert expect in (result.get("final_response") or ""), result
    assert len(main) == 1, f"retried a terminal Routster {status}: {len(main)} main requests"


def test_per_key_rate_limit_backs_off_then_answers():
    limited = _error(429, message="per-key rate limit reached. slow down.", type="rate_limit")
    result, main = _turn([limited, Text("answered")], retries=3)

    assert result.get("completed") and result.get("final_response") == "answered", result
    assert len(main) == 2
