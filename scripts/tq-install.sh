#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Step 1: Register marketplace and install Claude plugin
# ---------------------------------------------------------------------------
if command -v claude &>/dev/null; then
  echo "Adding codefilabs marketplace..."
  claude plugin marketplace add codefilabs/marketplace
  echo "Installing tq plugin..."
  claude plugin install tq@codefilabs
else
  echo "Warning: 'claude' CLI not found — skipping plugin registration." >&2
  echo "  Install Claude Code first: https://claude.ai/code" >&2
fi

# ---------------------------------------------------------------------------
# Step 2: Resolve plugin root for symlinking CLI tools
# ---------------------------------------------------------------------------
if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" ]]; then
  PLUGIN_ROOT="$CLAUDE_PLUGIN_ROOT"
elif [[ -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]]; then
  # Running directly from a cloned repo
  PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
else
  # Running via curl | bash — find the installed plugin cache
  CACHE_DIR="$HOME/.claude/plugins/cache/tq/codefilabs"
  PLUGIN_ROOT="$(ls -d "$CACHE_DIR"/*/ 2>/dev/null | sort -V | tail -1)"
  if [[ -z "${PLUGIN_ROOT:-}" ]]; then
    echo "Error: could not locate tq plugin files in $CACHE_DIR" >&2
    echo "  Try running: claude plugin marketplace add codefilabs/marketplace && claude plugin install tq@codefilabs" >&2
    exit 1
  fi
fi

# ---------------------------------------------------------------------------
# Step 3: Symlink CLI tools into PATH
# ---------------------------------------------------------------------------
if [[ -n "${TQ_INSTALL_DIR:-}" ]]; then
  INSTALL_DIR="$TQ_INSTALL_DIR"
elif [[ -d "/opt/homebrew/bin" ]]; then
  INSTALL_DIR="/opt/homebrew/bin"
elif [[ -d "/usr/local/bin" ]]; then
  INSTALL_DIR="/usr/local/bin"
else
  echo "Error: no suitable install directory found (tried /opt/homebrew/bin, /usr/local/bin)" >&2
  echo "Set TQ_INSTALL_DIR to override" >&2
  exit 1
fi

for SCRIPT in tq tq-message tq-setup tq-telegram-poll tq-telegram-watchdog; do
  SRC="$PLUGIN_ROOT/scripts/$SCRIPT"
  DEST="$INSTALL_DIR/$SCRIPT"
  if [[ -L "$DEST" ]]; then
    rm "$DEST"
  elif [[ -f "$DEST" ]]; then
    echo "Warning: $DEST exists and is not a symlink — skipping (remove manually to update)" >&2
    continue
  fi
  ln -s "$SRC" "$DEST"
  echo "  linked $DEST -> $SRC"
done

mkdir -p ~/.tq/queues ~/.tq/logs ~/.tq/config

echo ""
echo "tq installed. Crontab example (crontab -e):"
echo ""
echo "  0 9 * * * /opt/homebrew/bin/tq ~/.tq/queues/morning.yaml >> ~/.tq/logs/tq.log 2>&1"
echo "  */30 * * * * /opt/homebrew/bin/tq --status ~/.tq/queues/morning.yaml >> ~/.tq/logs/tq.log 2>&1"
echo ""
echo "To configure Telegram notifications:"
echo "  tq-setup"
echo ""
echo "Or from Claude Code: /setup-telegram"
echo ""
echo "To relay Telegram messages as tq tasks, add to crontab:"
echo "  * * * * * /opt/homebrew/bin/tq-telegram-poll >> ~/.tq/logs/tq-telegram.log 2>&1"
