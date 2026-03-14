# tq Chrome Integration Reference

## How tq Uses Chrome

Every spawned Claude session receives the `--chrome` flag, which connects Claude Code to a running Chrome browser via the Claude extension. This enables browser automation tools (chrome-devtools MCP, playwright MCP) within task sessions.

## Default Profile

tq opens **Chrome Profile 5** (halbotkirchner@gmail.com) automatically before connecting. The profile is launched via `open -a "Google Chrome" --args --profile-directory="Profile 5"` in the generated launcher script.

## Chrome Profile Configuration

To use a different Chrome profile, set the profile directory in the queue file or launcher:

| Profile | Directory | Use Case |
|---------|-----------|----------|
| Default | `Default` | Personal browsing |
| Profile 1-N | `Profile N` | Work accounts, separate extensions |

Find available profiles:
```bash
ls ~/Library/Application\ Support/Google/Chrome/ | grep -E "^(Default|Profile)"
```

## Multiple Profiles / Isolated Sessions

To interact with a Chrome profile that has a different Claude extension instance (e.g., different account), use the `chrome-devtools` MCP with the `--isolated` flag. This runs isolated browser extension sessions that do not conflict across profiles.

## Setting the Browser Display Name

The Claude extension stores the browser name as `bridgeDisplayName` in the extension's `chrome.storage.local`. To set it:

1. Right-click the Claude extension icon in the Chrome toolbar → **Options**
2. Or open the sidepanel → settings/gear icon → name field

The display name helps identify which Chrome instance is connected when running multiple profiles.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Chrome not launching | Verify Chrome is installed: `ls /Applications/Google\ Chrome.app` |
| Extension not connecting | Check the Claude extension is installed and enabled in the target profile |
| Wrong profile opening | Update the `--profile-directory` argument in the launcher or queue config |
| "No browser connected" in Claude | Restart Chrome with the correct profile, then retry the task |
