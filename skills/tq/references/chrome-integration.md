# tq Chrome Integration Reference

## Default Profile

tq launches claude with `--chrome` and opens **Chrome Profile 5** (halbotkirchner@gmail.com) automatically before connecting.

## Multiple Chrome Profiles / Extensions

To interact with a Chrome profile that has a different Claude extension instance (e.g., different account), use the `chrome-devtools` MCP with the `--isolated` flag. This runs isolated browser extension sessions that do not conflict across profiles.

## Setting the Browser Display Name

The Claude extension stores the browser name as `bridgeDisplayName` in the extension's `chrome.storage.local`. To set it for the first time on a profile:

- Right-click the Claude extension icon in the Chrome toolbar and select **Options**
- Or open the sidepanel and look for a settings/gear icon with a name field
