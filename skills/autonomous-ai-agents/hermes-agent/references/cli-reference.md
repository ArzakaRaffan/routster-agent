# Routster CLI Reference

Live sources when anything looks stale: `routster --help`, `routster <command> --help`,
https://hermes-agent.nousresearch.com/docs/reference/cli-commands

### Global Flags

```
hermes [flags] [command]        (no subcommand = interactive chat)

  --version, -V             Show version
  -z, --oneshot PROMPT      One-shot: print ONLY the final response (for scripts/pipes)
  -m MODEL  --provider P    Model/provider override for this invocation
  -t, --toolsets LIST       Comma-separated toolsets for this invocation
  --resume, -r SESSION      Resume session by ID or title
  --continue, -c [NAME]     Resume by name, or most recent session
  --worktree, -w            Isolated git worktree mode (parallel agents)
  --skills, -s SKILL        Preload skills (comma-separate or repeat)
  --profile, -p NAME        Use a named profile
  --yolo                    Skip dangerous command approval
  --tui / --cli             Force the Ink TUI / classic REPL
  --ignore-rules            Skip AGENTS.md/SOUL.md/memory/skill injection
  --safe-mode               Disable ALL customizations (troubleshooting)
  --pass-session-id         Include session ID in system prompt
```

### Chat

```
routster chat [flags]
  -q, --query TEXT          Single query, non-interactive
  --image PATH              Attach a local image to a single query
  -Q, --quiet               Suppress banner, spinner, tool previews
  --checkpoints             Enable filesystem checkpoints (/rollback)
  --max-turns N             Cap tool-calling iterations
  --source TAG              Session source tag (default: cli)
```
(plus the global flags above)

### Configuration

```
routster setup [section]      Wizard (model|tts|terminal|gateway|tools|agent)
routster model                Interactive model/provider picker
routster fallback [add|remove|list]  Fallback provider chain
routster config [show|edit|get|set|unset|path|env-path|check|migrate]
routster login / logout       OAuth sign-in / clear stored auth
routster doctor [--fix]       Check dependencies and config
routster status [--full]      Component summary (--full: every section)
```

### Tools & Skills

```
routster tools [list|enable NAME|disable NAME]   Per-platform toolsets (curses UI with no args)

routster skills list|browse|search QUERY|inspect ID
routster skills install ID    Hub identifier OR a direct https://…/SKILL.md URL
routster skills config        Enable/disable skills per platform
routster skills check|update|uninstall|publish PATH
routster skills tap add REPO  Add a GitHub repo as a skill source
routster bundles              Skill bundles (one /<name> alias loads several skills)
```

### MCP Servers

```
routster mcp add NAME (--url or --command) | remove | list | test NAME
routster mcp catalog | install NAME     Curated catalog install
routster mcp configure NAME             Toggle tool selection
hermes mcp-serve                      Run Routster as an MCP server (mcp-serve plugin)
```
Details (transport, tool discovery, catalog): `references/native-mcp.md`.

### Gateway (Messaging Platforms)

```
routster gateway run|install|start|stop|restart|status|setup
```

20+ platforms: Telegram, Discord, Slack, WhatsApp (Baileys + Business Cloud API), iMessage (Photon — `routster photon setup`), Signal, Email, SMS, Matrix, Mattermost, Teams, LINE, SimpleX, ntfy, Google Chat, Home Assistant, DingTalk, Feishu, WeCom, Weixin, API Server, Webhooks. Open WebUI connects via the API Server adapter. Most adapters ship under `plugins/platforms/`.
Docs: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/

### Sessions

```
routster sessions list|browse|rename ID TITLE|delete ID|export OUT|prune|stats
```

### Cron / Webhooks

```
routster cron list|create SCHED|edit ID|pause|resume|run ID|remove|status
    Schedules: '30m', 'every 2h', '0 9 * * *', ISO timestamp
routster webhook subscribe NAME|list|remove NAME|test NAME
```
Webhook payloads/routes: `references/webhooks.md`.

### Profiles

```
routster profile list|create NAME (--clone|--clone-all|--clone-from)|use|show|delete
routster profile rename A B | alias NAME | export NAME | import FILE
routster profile migrate-identity A B   Retry a completed rename's session/routing identity migration
```

### Credentials & Pools

```
routster auth                 Interactive credential manager
routster auth add [PROVIDER]  Add OAuth or API-key credential (nous, openai-codex, qwen-oauth, …)
routster auth list|remove P IDX|reset PROVIDER|status
```
Multiple credentials per provider form a pool that rotates automatically and skips exhausted keys.

### Other

```
routster desktop / gui        Native desktop app
routster dashboard            Web admin panel + embedded chat (--stop / --status)
routster proxy                OpenAI-compatible local proxy backed by an OAuth provider
routster portal               Quick setup / sign in via Nous Portal
routster kanban <verb>        Multi-agent work-queue board
routster project              Named multi-folder workspaces (see references/projects-and-folders.md)
routster skin list|use|set    Switch/tweak skins (see references/themes.md)
routster pets <verb>          Pet mascots (see references/petdex.md)
routster memory setup|status|off|reset   Memory provider
routster secrets bitwarden|onepassword   External secret stores
routster moa                  Mixture-of-Agents slots
routster hooks / security / backup / import / checkpoints / console
routster logs [-f] [errors]   View agent/error logs
routster send                 One-off message through a gateway platform
routster pairing / plugins / insights / journey / computer-use
routster acp                  ACP server (IDE integration)
routster completion bash|zsh|fish
routster update / uninstall
```

Plugin- and provider-supplied subcommands (e.g. `routster photon setup`) only appear once their plugin is installed/active. Importing from OpenClaw, Claude Code, Codex CLI or Cursor (`routster import-agent <agent>`, plus the older `routster claw migrate|cleanup`) comes from the `agent-importers` plugin; a fresh `routster setup` that finds one of those agents offers to install it.

### Where to Find Things

| Looking for... | Location |
|---|---|
| Config options | `hermes config edit` · [Configuration docs](https://hermes-agent.nousresearch.com/docs/user-guide/configuration) |
| Tools / toolsets | `hermes tools list` · [Tools reference](https://hermes-agent.nousresearch.com/docs/reference/tools-reference) |
| Skills catalog | `hermes skills browse` · [Skills catalog](https://hermes-agent.nousresearch.com/docs/reference/skills-catalog) |
| Provider setup | `hermes model` · [Providers guide](https://hermes-agent.nousresearch.com/docs/integrations/providers) |
| Env variables | `hermes config env-path` · [Env vars reference](https://hermes-agent.nousresearch.com/docs/reference/environment-variables) |
| Gateway logs | `~/.hermes/logs/gateway.log` (or `routster logs`) |
| Sessions | `routster sessions browse` (reads state.db) |
