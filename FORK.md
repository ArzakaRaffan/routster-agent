# Routster Agent fork notes

Routster Agent is a fork of [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous
Research (MIT). This file lists every place the fork touches upstream code, so a merge from upstream
knows what to keep.

## Keeping up with upstream

```bash
git remote add upstream https://github.com/NousResearch/hermes-agent.git   # once per clone
git fetch upstream main
git merge upstream/main        # resolve conflicts with the list below
scripts/run_tests.sh tests/agent/test_routster_agent_loop.py tests/plugins/model_providers/test_routster_profile.py tests/hermes_cli/test_routster_setup.py
```

Most Routster behaviour lives in a file upstream never edits:
`plugins/model-providers/routster/__init__.py` (provider profile, error mapping, `routster login` /
`routster model` flow).

## Upstream files the fork changes

| File | Change |
|---|---|
| `pyproject.toml` | `routster` console script (`hermes` kept: core relaunches itself via `which("hermes")`) |
| `routster` | repo-root launcher, copy of `hermes` |
| `hermes_cli/_parser.py` | `prog="routster"` + description; hint helpers still see the `hermes` prog |
| `hermes_cli/subcommands/login.py`, `hermes_cli/main.py` (`cmd_login` forward), `hermes_cli/auth.py` (stub removed) | `login` signs in to Routster via the new `hermes_cli/auth_routster_login.py` (upstream: deprecation stub) |
| `hermes_cli/setup.py` | wizard banner, first-run menu label |
| `hermes_cli/setup_quick.py` | Quick Setup step = Routster (was Nous Portal); no messaging step |
| `hermes_cli/models_catalog_static.py` | `picker_after="^"` anchor; `FORK_UNOFFERED_PROVIDERS` (Nous) filtered from provider lists |
| `providers/base.py` | comment documenting the `"^"` anchor |
| `agent/auxiliary_client.py::_forwards_max_tokens` | auxiliary calls forward `max_tokens` to Routster |
| `agent/billing_links.py` | Routster dashboard as the top-up link |
| `README.md` | Routster Agent README (upstream README kept as `README.hermes.md`) |
| Tests adapted to the fork | `tests/hermes_cli/test_setup_quick_import.py`, `test_provider_parity.py`, `test_anon_picker.py`; `test_cli_provider_resolution.py::test_cmd_model_forwards_nous_login_tls_options` skipped (Nous is not in the picker) |
| `tests/fixtures/provider_wire_snapshot.json` | Routster wire entries (regenerate: `HERMES_UPDATE_WIRE_SNAPSHOT=1 python -m pytest tests/agent/transports/test_provider_wire_snapshot.py`) |
| `scripts/routster_smoke.py` | optional live smoke test (spends balance; never run by CI) |

## Routster gateway contract (what the profile relies on)

- `max_tokens` defaults to 1024 server-side, max 32768. The gateway **reserves**
  `input + max_tokens × output_multiplier` before calling upstream, so the profile sends a moderate
  8192 (raise it with `model.max_tokens` in config.yaml).
- Model ids are `routster/<name>`; `/v1/models` is public and ignores the key.
- Key check without spending balance: `POST /v1/chat/completions` with `messages: []` answers
  401/403 for a bad key and 400 `messages kosong` for a good one (before any reservation).
- `type: quota` means an empty balance on 402 and a per-key token window on 429; `type: rate_limit`
  (429) is the per-key / per-IP rpm limit and is retried with backoff.

## Open requests for the gateway

1. `capabilities.tools` in `/v1/models`, so the CLI can filter agent-capable models (the agent list
   is hand-curated until then).
2. A key-authenticated balance/usage endpoint (`GET /v1/me` or similar) for a status bar and a real
   key check (the empty-messages trick depends on validation order).
3. Test streamed `tool_calls` deltas on every upstream (fragmented arguments).
4. Optional: count `User-Agent: routster-agent/<version>` separately in stats.
5. Distinct `code`s for an empty balance (402) and a key quota (429); both are `type: quota` today.
6. Consider reserving against a smaller estimate than the full `max_tokens`: a large cap makes a
   low balance fail with 402 although the real cost is small.

## Not done yet

- One-line install. Plain `uv tool install` fails to resolve (upstream pins conflict outside
  `uv.lock`). `scripts/install.sh` honours `HERMES_REPO_URL`/`--branch` but publishes a `hermes`
  launcher only (`hermes_cli/_launchers.py`); `source ./activate` defines a checkout-bound dev
  function. The verified path today is `pm.build_env` (README), whose venv has `bin/routster`.

- Full rename of user-facing "Hermes" text, banner/ASCII art, docs links.
- `routster update` still pulls from NousResearch/hermes-agent (`hermes_cli/update_cmd_git.py`,
  installer URLs): must be redirected or disabled before distributing.
- `routster` with no model configured and only `ROUTSTER_API_KEY` in the environment fails with
  upstream's `storage_unavailable`; `routster login` (Enter keeps the env key) fixes it.
- Messaging gateway, desktop app, cron, kanban and Nous-only commands (`portal`) are still
  registered; only setup and provider lists hide Nous.
