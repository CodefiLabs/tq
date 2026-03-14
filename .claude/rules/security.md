# Security Rules

## Never Commit `.tq/` Directories

The `.tq/` directories written at runtime contain **live OAuth tokens in plaintext**:

- `<queue-dir>/.tq/<queue-name>/<hash>.launch.py` — each launcher embeds the OAuth token as:
  ```python
  os.environ["CLAUDE_CODE_OAUTH_KEY"] = "<live-token-value>"
  ```
- These files are ephemeral and local-only, but the `.gitignore` does not currently exclude them.

**Action**: Never `git add` any `.tq/` directory. Add `.tq/` to `.gitignore` if not already present.

## The `--dangerously-skip-permissions` Flag Is Intentional

Every spawned Claude session receives `--dangerously-skip-permissions`. Do not remove this flag.
It is required for headless, unattended automation — without it, Claude will prompt for permission
confirmations that no human is present to answer.

## OAuth Token Handling

Tokens are sourced from the macOS keychain at queue-run time:

```bash
security find-generic-password -s 'Claude Code-credentials' -a $USER -w
```

The `claudeAiOauth.accessToken` field is extracted and written into the launcher script.
Fallback: `CLAUDE_CODE_OAUTH_KEY` or `ANTHROPIC_API_KEY` environment variables.

Rules:
- Never hardcode tokens in source files
- Never log token values
- Never add token-containing files to git

## `.env` File Protection

No `.env` files currently exist, but the `.claude/settings.json` denies reading them anyway.
If `.env` files are added in future, they must be in `.gitignore` immediately.

## Conversation Mode Security

The conversation registry (`~/.tq/conversations/registry.json`) contains session metadata
but **no credentials**. However, the orchestrator and child sessions use the same
`--dangerously-skip-permissions` flag as queue mode tasks.

The Telegram bot token lives in `~/.tq/config/message.yaml`. This file should:
- Never be committed to git
- Never be shared or logged
- Be readable only by the owning user

Conversation session hooks (`~/.tq/conversations/sessions/<slug>/hooks/`) may contain
paths that reference the user's home directory but do not contain credentials directly.

## Sensitive Path Reference

| Path | Contains | Risk |
|------|----------|------|
| `<queue-dir>/.tq/<name>/<hash>.launch.py` | Plaintext OAuth token | Do not commit or share |
| `~/.tq/sessions/<hash>/settings.json` | Claude hook config | Low — no credentials |
| `<queue-dir>/.tq/<name>/<hash>` | Task state (status only) | Low |
| `~/.tq/config/message.yaml` | Telegram bot token, user ID | Do not commit or share |
| `~/.tq/conversations/registry.json` | Session metadata, msg IDs | Low — no credentials |
| `~/.tq/conversations/sessions/<slug>/` | Conversation state | Low — no credentials |
