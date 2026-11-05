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
| `hermes_cli/routster_fork.py` (new) | **one place** listing the hidden subcommands and slash commands |
| `hermes_cli/main.py::_build_cli_parser` | `_parser.hide_fork_subcommands()` drops hidden ones from `--help` (they still parse: internals relaunch `gateway`/`serve`) |
| `hermes_cli/commands.py` | `COMMAND_REGISTRY` filtered by `HIDDEN_SLASH_COMMANDS` (Nous account, messaging, pets, kanban, cron) |
| `hermes_cli/setup.py` | no Messaging Platforms step, no `gateway`/`telemetry` sections; banner text |
| `hermes_cli/_parser.py` | help examples say `routster`, no gateway/profile/console lines |
| `hermes_cli/skin_engine.py` | new built-in `routster` skin (palette of routster.trackster.dev, mint accent, no kaomoji); unset `display.skin` falls back to it; Hermes-named skins carry the Routster persona |
| `hermes_cli/config_defaults.py`, `cli-config.yaml.example`, `gateway/session_config.py`, `tui_gateway/methods_config.py`, `hermes_cli/web_server_config.py` | default skin `routster`; `tui_status_indicator: unicode` |
| `hermes_cli/banner.py`, `ui-tui/src/banner.ts`, `ui-tui/src/theme.ts` | ROUTSTER wordmark + routing hero replace HERMES-AGENT / caduceus; "Routster Agent v…" labels |
| `acp_adapter/commands.py`, `agent/legacy_cli.py`, `hermes_cli/_startup_fast.py`, `hermes_cli/gateway_chat_view.py` | version / welcome text |
| `web/` (`index.html`, `index.css`, `themes/presets.ts`, `App.tsx`, `i18n/*.ts`) | dashboard default theme = Routster palette, brand text, no Cron/Channels/Webhooks/Pairing nav items |
| `hermes_cli/update_cmd_git.py`, `hermes_cli/update_cmd_zip.py` | "official" repo = ArzakaRaffan/routster-agent (no Hermes upstream prompt or push for users; ZIP fallback and repair hints point at the fork) |
| `hermes_cli/_launchers.py`, `hermes_cli/_install_repair.py` | `routster` launcher next to `hermes` / `hermes-acp` |
| `scripts/install.sh`, `scripts/install.ps1`, `scripts/install.cmd` | default repo = the fork, home `~/.routster`, Routster banner and wording, setup runs `routster setup`, gateway service stage disabled |
| `hermes_constants.py` (`HOME_DIRNAME`) + the stray `~/.hermes` fallbacks (`agent/file_safety.py`, `agent/nous_rate_guard.py`, `agent/transports/codex_app_server.py`, `hermes_cli/{dashboard_procs,env_loader,gateway,gateway_runtime_service_identity,main,main_dashboard,stdio,update_fleet_scope,update_lock}.py`, `hermes_state_holders.py`, `ui-tui/src/**` home fallbacks, `scripts/_activation.sh`, `scripts/run_tests.sh`, `setup-hermes.sh`, `activate.ps1`) | data folder is `~/.routster` (Windows `%LOCALAPPDATA%\routster`), never a Hermes home; the checkout inside it keeps the `hermes-agent` folder name (backup/uninstall/doctor key on it) |
| `hermes_cli/_launchers.py::expose_cli` | only `routster` is published to `~/.local/bin`; `hermes` stays free for a real Hermes install |
| `hermes_cli/setup.py`, `hermes_cli/setup_quick.py` | `routster setup` = Routster key + model, nothing else (no mode menu, agent import, terminal prompt or Nous metrics offer); `--reconfigure` = full wizard, `--quick` = missing items |
| `hermes_cli/main.py::cmd_chat` | no shared-metrics (Nous telemetry) offer before chat |

## Branding: `scripts/routster_rebrand.py`

User-visible text is rewritten by a script, not by hand, so upstream merges stay mechanical:
after `git merge upstream/main`, take upstream's side of any conflicted *string* and run

```bash
python scripts/routster_rebrand.py          # idempotent; --check exits 1 if anything is left
```

It rewrites string literals (never comments, docstrings, raw strings, bytes or identifiers) in the
Python tree, every `locales/*.yaml` line and every skill `.md` (a `hermes …` line in a skill is a
command the agent runs). `hermes <subcommand>` → `routster <subcommand>` (the subcommand list is
the live parser's; add new upstream commands to `_SUBCOMMANDS`), `Hermes Agent` → `Routster Agent`,
`Hermes` → `Routster`. Kept on purpose: `X-Hermes-*` headers, `Hermes-Agent/…` user agents, the
desktop app (`Hermes.app`, "Hermes Desktop"), Nous models (`Hermes 3/4`), anything crediting Nous
Research, and literals that are exactly `hermes`/`Hermes`. `ui-tui/src` and `web/src` were rewritten
once with the same line rule (`rewrite_lines`); rerun it on them by hand after a TUI/web merge.

## Living next to a real Hermes install

A machine can run Hermes (`~/.hermes`, `hermes` on PATH) and Routster side by side:

- `hermes_cli/main.py` pins `HERMES_HOME` at entry, so every Routster process and unit carries it.
  A process or user unit *without* it is Hermes's: `dashboard_procs._hermes_home_for_pid`,
  `update_fleet_scope.systemd_unit_hermes_home` and `gateway_runtime_service_identity.verify_systemd`
  default to `~/.hermes`, so `routster update` never restarts Hermes services.
- `gateway/status.py::_get_lock_dir` is `~/.local/state/routster/locks`: a shared rendezvous made
  `routster` attach to the Hermes gateway (`Gateway inaccessible: profile_mismatch`).
- Service names are Routster's own (`scripts/routster_service_names.py`, rerun after upstream
  merges; `--check` exits 1 if anything is left): systemd `routster-gateway*`/`routster-serve*`/`routster-dashboard*`,
  launchd `ai.routster.gateway*`, Scheduled Task `Routster_Gateway`. A Hermes unit is never listed,
  installed over, started or restarted. `gateway_runtime_service_identity.verify_home` also treats a
  unit pinned to `~/.hermes` as another install (`ForeignRoot`), never `profile_mismatch`.
- Self-relaunch, kanban workers, profile wrapper scripts, the TUI's external commands, the agent
  terminal's PATH bin dir and `pm.environments.cli_command_name` resolve `routster`, never
  `which("hermes")` (that is the other install).
- `tools/approval_detection.py`, `tools/skills_guard.py`, `tools/threat_patterns.py` and
  `tools/plugin_guard_context.py` match `.routster` paths and `routster update/gateway`/`pkill
  routster` next to the Hermes spellings (`tests/tools/test_routster_approval_names.py`).
- The default persona says "You are Routster Agent." (`agent/prompt_builder.py`,
  `hermes_cli/default_soul.py`, `SOUL.md`, `docker/SOUL.md`); an auto-seeded Hermes-named `SOUL.md`
  upgrades in place, an edited one is never touched.
- `routster update` prints no curator notices and no "select a provider" tip.

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

- Live smoke test (`scripts/routster_smoke.py`) has not been run: needs `ROUTSTER_API_KEY`.
- Dashboard / TUI TypeScript changes are not type-checked locally (repo wants Node 26; `npm ci`
  not run). The edits are strings, palette values, four nav items and three icon imports.
- Hidden ≠ deleted: messaging gateway, kanban, cron, desktop app and Nous code still ship (the
  dashboard, TUI and upstream merges depend on them).
- Docstrings, comments and `website/` docs still say Hermes (never shown in the product).
- `routster debug share` still uploads to paste.rs/dpaste and points at Nous support.
- One-line install reads `scripts/install.sh` from `main`. It installs into `~/.routster`, so an
  existing Hermes checkout in `~/.hermes` (origin NousResearch, tracks Hermes stable tags) is never
  reused. Not yet run end-to-end on a clean machine.
- Windows: `%LOCALAPPDATA%\routster\bin` still holds a `hermes` launcher and goes on the User PATH.
- `routster` with no model configured and only `ROUTSTER_API_KEY` in the environment fails with
  upstream's `storage_unavailable`; `routster login` (Enter keeps the env key) fixes it.
