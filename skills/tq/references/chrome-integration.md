# tq Chrome Integration Reference

## How `--chrome` Works

When a queue task runs, tq generates a `.launch.py` launcher script. If Chrome integration is enabled, the launcher:

1. Opens Chrome with the configured profile directory before connecting
2. Passes `--chrome` to the `claude` CLI, which connects to the Chrome browser extension
3. Claude can then interact with web pages through the browser

The `--chrome` flag is added to the `claude` CLI args in the generated launcher:

```python
# In the generated .launch.py:
subprocess.Popen(["open", "-a", "Google Chrome", "--args", "--profile-directory=Profile 5"])
time.sleep(2)
os.execvp('claude', ['claude', '--settings', settings_file, '--dangerously-skip-permissions', '--chrome', prompt])
```

## Default Profile

tq uses **Chrome Profile 5** (`--profile-directory=Profile 5`) which corresponds to halbotkirchner@gmail.com. This is hardcoded in the `scripts/tq` launcher generation (line ~396).

To find which Chrome profile directory maps to which account:

```bash
# List all Chrome profiles and their email addresses
for d in ~/Library/Application\ Support/Google/Chrome/Profile*/; do
  python3 -c "import json; p=json.load(open('$d/Preferences')); print('$(basename $d):', p.get('account_info',[{}])[0].get('email','unknown'))" 2>/dev/null
done
```

## Multiple Chrome Profiles

To use a different Chrome profile for specific tasks, modify the `--profile-directory` argument in the generated launcher. Currently, this requires editing `scripts/tq` directly (the profile is not configurable per-queue).

For running isolated browser extension sessions across profiles without conflicts, use the `chrome-devtools` MCP with the `--isolated` flag.

## Setting the Browser Display Name

The Claude browser extension stores its display name as `bridgeDisplayName` in `chrome.storage.local`. This name identifies the browser in Claude's connected browsers list.

To set or change it:

1. Open Chrome with the target profile
2. Right-click the Claude extension icon in the toolbar and select **Options**
3. Look for the browser name / display name field and set it
4. The name persists in the extension's local storage

## When Chrome Is Used

Chrome integration is used when tasks need to interact with web pages (e.g., scraping, form filling, visual verification). Most queue tasks that only modify code do not need Chrome.

The `--chrome` flag is controlled in the launcher generation section of `scripts/tq` (~line 396-403).
