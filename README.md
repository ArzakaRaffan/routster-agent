# Routster Agent

A terminal coding agent powered by **[Routster](https://routster.trackster.dev)**: one API key,
many models (DeepSeek, GLM, Kimi, MiniMax, and more), billed in Rupiah.

Type a task, and the agent reads files, edits them, runs shell commands (with confirmation), and
keeps going until the task is done.

> Routster Agent is a fork of **[Hermes Agent](https://github.com/NousResearch/hermes-agent)
> by Nous Research** (MIT license). The whole TUI, agent loop, tools, and sandbox come from
> Hermes. The original Hermes README is in [README.hermes.md](README.hermes.md), and the fork's
> changes are listed in [FORK.md](FORK.md).

## Get started in 2 minutes

1. **Get an API key.** Sign up at <https://routster.trackster.dev>, top up your balance (QRIS), then
   copy your API key from the [dashboard](https://routster.trackster.dev/dashboard).
2. **Install (one line):**

   ```bash
   # macOS / Linux / WSL
   curl -fsSL https://raw.githubusercontent.com/ArzakaRaffan/routster-agent/main/scripts/install.sh | bash
   ```

   ```powershell
   # Windows (PowerShell)
   & ([scriptblock]::Create((irm https://raw.githubusercontent.com/ArzakaRaffan/routster-agent/main/scripts/install.ps1)))
   ```

   The installer sets up Python via `uv`, clones this repo into `~/.routster`, then installs the
   `routster` command. All Routster data lives in `~/.routster`, separate from Hermes Agent
   (`~/.hermes` and the `hermes` command are left untouched). No background service is installed.

   <details><summary>Manual install from source</summary>

   ```bash
   git clone https://github.com/ArzakaRaffan/routster-agent.git
   cd routster-agent
   uv python install 3.14
   "$(uv python find 3.14)" -m pm.build_env --source . --out ~/.local/share/routster-agent/venv
   mkdir -p ~/.local/bin && ln -sf ~/.local/share/routster-agent/venv/bin/routster ~/.local/bin/routster
   ```

   A plain `pip install`/`uv tool install` does **not** work, because the upstream dependency pins
   only resolve through `uv.lock` + PM.
   </details>

3. **Log in and start:**

   ```bash
   routster login     # paste your API key (input hidden); validated without spending balance
   routster           # start a session in your project folder
   ```

## Key commands

| Command | What it does |
|---|---|
| `routster` | Interactive session (TUI) |
| `routster -z "task"` | One-shot task, no interaction |
| `routster login` | Save and validate your Routster API key, make Routster the default provider |
| `routster model` | Pick a model. Shows each model's input/output multiplier |
| `routster setup` | Routster API key + model pick (`--reconfigure` for the full settings) |
| `routster doctor` | Check your configuration |
| `routster update` | Update to the latest version from this repo (`main` branch) |
| `routster dashboard` | Local web dashboard (port 9119) |
| `routster auth add <provider>` | Connect your own provider API key |

## Models and cost

Each request costs `input_tokens × input_multiplier + output_tokens × output_multiplier` from your
balance, and one agent task can call the API many times. The model list always comes from
`/v1/models`, and the `routster model` picker shows the multipliers.

- Default: `routster/deepseek-v4.1-flash` (multiplier 1×/1×, cheap).
- Recommended for agent work (hand-curated): `routster/deepseek-v4-pro`, `routster/glm-5.3`,
  `routster/glm-5.3-flash`, `routster/kimi-k2.7`, `routster/minimax-m3`.
- The agent always sends `max_tokens` (default 8192). The gateway reserves balance for the full
  `max_tokens` before the request runs, so only raise `model.max_tokens` in config when you need to.

## Security

- Your API key is stored in `~/.routster/.env` with permission `600`, or read from the
  `ROUTSTER_API_KEY` env var. Never commit your key to a repo.
- Dangerous shell commands ask for approval first (Hermes's built-in `smart` approval mode).
  `--yolo` turns confirmation off, so use it with care.
- Sandbox: by default commands run directly on your machine. For isolation, pick a Docker, SSH,
  Modal, Daytona, or Vercel Sandbox backend with `routster setup terminal`.
- Routster does not store prompt/response content, only metadata (token counts, model, status).

## Advanced configuration

| Variable / key | What it does |
|---|---|
| `ROUTSTER_API_KEY` | API key (alternative to `routster login`) |
| `ROUTSTER_BASE_URL` | Use a different gateway, e.g. staging or `http://localhost:8000/v1` |
| `model.max_tokens` (config.yaml) | Output limit per request (max 32768) |

Other providers (OpenRouter, Anthropic, and more) still work through `routster model` or the
config. Routster is just the default.

## Status

This is an early version. Not done yet:

- The one-line installer has not been tested end-to-end on a clean machine.
- Balance is not shown in the status bar, because the gateway has no API-key-based balance endpoint yet.
- Built-in Hermes features that don't apply here (messaging gateway, kanban, cron, desktop app,
  Nous account) are hidden from the menus, but the code is still there. Details in [FORK.md](FORK.md).

## License

MIT, same as Hermes Agent. Copyright (c) 2025 Nous Research for the Hermes code. See
[LICENSE](LICENSE).
