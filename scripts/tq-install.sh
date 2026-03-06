#!/usr/bin/env bash
set -euo pipefail

# Resolve the plugin root (one level up from scripts/)
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
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

# Symlink plugin scripts into PATH
for SCRIPT in tq tq-status; do
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

mkdir -p ~/.claude/queues ~/.claude/logs

echo ""
echo "tq installed. Crontab example (crontab -e):"
echo ""
echo "  0 9 * * * /opt/homebrew/bin/tq ~/.claude/queues/morning.yaml >> ~/.claude/logs/tq.log 2>&1"
echo "  */30 * * * * /opt/homebrew/bin/tq-status ~/.claude/queues/morning.yaml >> ~/.claude/logs/tq.log 2>&1"
