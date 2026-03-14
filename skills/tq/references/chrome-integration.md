# tq Chrome Integration Reference

## When to Use Chrome

Chrome integration is for tasks that interact with web pages (scraping, form filling, visual verification). Most queue tasks that only modify code do **not** need Chrome.

## How `--chrome` Works

When a queue task runs, tq generates a `.launch.py` launcher script that:

1. Opens Chrome with the configured profile directory
2. Passes `--chrome` to the `claude` CLI, connecting to the Chrome browser extension
3. Claude interacts with web pages through the browser

```python
# In the generated .launch.py:
subprocess.Popen(["open", "-a", "Google Chrome", "--args", "--profile-directory=<ProfileDir>"])
time.sleep(2)
os.execvp('claude', ['claude', '--settings', settings_file, '--dangerously-skip-permissions', '--chrome', prompt])
```

Note: `subprocess.Popen` is correct here (launches Chrome as a sibling process). `os.execvp` replaces the Python process with Claude (per `anti-patterns.md`).

## Chrome Profile Configuration

The Chrome profile directory is hardcoded in `scripts/tq` in the launcher generation section. To find which profile directory maps to which account:

```bash
for d in ~/Library/Application\ Support/Google/Chrome/Profile*/; do
  python3 -c "import json; p=json.load(open('$d/Preferences')); print('$(basename $d):', p.get('account_info',[{}])[0].get('email','unknown'))" 2>/dev/null
done
```

To use a different profile, edit the `--profile-directory` argument in `scripts/tq`. The profile is not yet configurable per-queue.

## Browser Display Name

The Claude browser extension identifies itself via `bridgeDisplayName` in `chrome.storage.local`. Set it via the extension's Options page (right-click extension icon > Options).

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Chrome doesn't open | Chrome not installed or not at expected path | Verify: `ls /Applications/Google\ Chrome.app` |
| Extension not connecting | Claude extension not installed in the target profile | Install the Claude Code extension in Chrome, then retry |
| Wrong profile used | Hardcoded profile doesn't match intended account | Run the profile discovery command above, update `scripts/tq` |
| `--chrome` flag ignored | Task launched without Chrome integration | Check the launcher generation section in `scripts/tq` |

## Related

- **SKILL.md** — overview of tq modes and CLI usage
- **session-naming.md** — how tmux session names are derived
