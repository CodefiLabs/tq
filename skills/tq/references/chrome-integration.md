# tq Chrome Integration Reference

## Overview

tq passes `--chrome` to every spawned `claude` CLI session, enabling browser automation via the Claude extension. The generated `.launch.py` launcher opens Chrome before connecting Claude to it.

## Launcher Flow

1. Launcher opens Chrome with the configured profile directory
2. Waits 2 seconds for Chrome to initialize
3. Runs `claude` with `--chrome` flag (connects to the browser extension)

```python
# Generated .launch.py (simplified):
subprocess.Popen(["open", "-a", "Google Chrome", "--args", "--profile-directory=Profile 5"])
time.sleep(2)
os.execvp('claude', ['claude', '--settings', settings_file,
           '--dangerously-skip-permissions', '--chrome', prompt])
```

## Chrome Profile Configuration

**Default**: Profile 5 — hardcoded in `scripts/tq` launcher generation (~line 396).

**Not per-queue configurable** — changing the profile requires editing `scripts/tq` directly.

### Discovering Profiles

```bash
for d in ~/Library/Application\ Support/Google/Chrome/Profile*/; do
  python3 -c "import json; p=json.load(open('$d/Preferences')); \
    print('$(basename $d):', p.get('account_info',[{}])[0].get('email','unknown'))" 2>/dev/null
done
```

## Browser Display Name

The Claude extension identifies each browser by `bridgeDisplayName` in `chrome.storage.local`. Set it via the extension's Options page (right-click extension icon > Options).

## When Chrome Is Needed

| Task Type | Chrome Required |
|-----------|----------------|
| Code changes, file edits, git ops | No |
| Web scraping, form filling | Yes |
| Visual verification, screenshots | Yes |
| Browser-based testing | Yes |

Most queue tasks only modify code and do not use Chrome. The `--chrome` flag is always passed but has no effect unless a task uses browser tools.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Chrome not opening | Verify Chrome is installed: `open -a "Google Chrome"` |
| Wrong profile | Check profile mapping with discovery script above |
| Extension not connecting | Ensure Claude extension is installed in the target profile |
| Multiple conflicting sessions | Use `chrome-devtools` MCP with `--isolated` flag |

## Related

- `scripts/tq` lines ~396-403 — launcher generation controlling `--chrome`
- SKILL.md — overview of queue mode and launcher behavior
