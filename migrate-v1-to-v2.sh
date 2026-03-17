#!/usr/bin/env bash
set -euo pipefail

# tq v1 → v2 migration script
# Removes v1 bash scripts, promotes v2 Python to root, installs `tq` CLI.
#
# What it does:
#   1. Stops any running tq v1 daemon/conversations
#   2. Removes v1 symlinks from PATH
#   3. Removes v1 scripts/, skills/, .claude/, docs/, tools/, tests/ directories
#   4. Moves v2/ contents (tq/ package, plugins, skills) to repo root
#   5. Creates a `tq` wrapper script in /opt/homebrew/bin (or /usr/local/bin)
#   6. Updates all `tq2` references to `tq`
#
# What it preserves:
#   - ~/.tq/ runtime state (config.json, tq.db, hooks, daemon.pid)
#   - ~/.tq/queues/ queue files
#   - ~/.tq/config/ message config
#   - ~/.tq/conversations/ conversation state
#   - Git history (no force pushes)
#
# Run from the tq repo root:
#   bash migrate-v1-to-v2.sh

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
TQ_PACKAGE="$REPO_ROOT/tq"
INSTALL_DIR="${TQ_INSTALL_DIR:-/opt/homebrew/bin}"

echo "=== tq v1 → v2 migration ==="
echo "Repo: $REPO_ROOT"
echo "Install dir: $INSTALL_DIR"
echo ""

# ── Step 1: Stop v1 processes ────────────────────────────────────────────────
echo "1. Stopping v1 processes..."
if command -v tq-converse &>/dev/null; then
    tq-converse stop-all 2>/dev/null || true
fi
# Kill any running tq-telegram-poll cron processes
pkill -f tq-telegram-poll 2>/dev/null || true
pkill -f tq-telegram-watchdog 2>/dev/null || true

# Stop v2 daemon if running
if [ -f ~/.tq/daemon.pid ]; then
    PID=$(cat ~/.tq/daemon.pid 2>/dev/null || echo "")
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null || true
        echo "  Stopped v2 daemon (pid $PID)"
    fi
fi
echo "  Done."

# ── Step 2: Remove v1 symlinks ──────────────────────────────────────────────
echo "2. Removing v1 symlinks from $INSTALL_DIR..."
for SCRIPT in tq tq-converse tq-cron-sync tq-message tq-setup tq-telegram-poll tq-telegram-watchdog; do
    TARGET="$INSTALL_DIR/$SCRIPT"
    if [ -L "$TARGET" ]; then
        # Only remove if it points to our v1 scripts dir
        LINK_TARGET=$(readlink "$TARGET" 2>/dev/null || echo "")
        if [[ "$LINK_TARGET" == *"/scripts/"* ]]; then
            rm "$TARGET"
            echo "  Removed $TARGET → $LINK_TARGET"
        fi
    fi
done
# Also remove from npm global (nvm)
NVM_TQ="$HOME/.nvm/versions/node/v24.7.0/bin/tq"
if [ -L "$NVM_TQ" ]; then
    rm "$NVM_TQ"
    echo "  Removed $NVM_TQ"
fi
echo "  Done."

# ── Step 3: Clean v1-only crontab entries ────────────────────────────────────
echo "3. Cleaning v1-only crontab entries..."
# Only remove entries for v1 helper scripts that no longer exist in v2.
# Queue run/status entries (e.g. `tq ~/.tq/queues/morning.yaml`) are preserved.
V1_ONLY_PATTERN='tq-cron-sync\|tq-telegram-poll\|tq-telegram-watchdog'
if crontab -l 2>/dev/null | grep -q "$V1_ONLY_PATTERN"; then
    crontab -l 2>/dev/null | grep -v "$V1_ONLY_PATTERN" | crontab -
    echo "  Removed v1 helper crontab entries (tq-cron-sync, tq-telegram-poll, tq-telegram-watchdog)."
else
    echo "  No v1 helper crontab entries found."
fi

# Warn about any remaining entries that reference the old scripts/ path
if crontab -l 2>/dev/null | grep -q 'scripts/tq'; then
    echo ""
    echo "  WARNING: Your crontab still has entries referencing 'scripts/tq'."
    echo "  These will break now that scripts/ is removed. Update them to use"
    echo "  the new tq path ($INSTALL_DIR/tq). Affected lines:"
    crontab -l 2>/dev/null | grep 'scripts/tq' | sed 's/^/    /'
    echo ""
fi

# ── Step 4: Remove v1 files from repo ───────────────────────────────────────
echo "4. Removing v1 files from repo..."
cd "$REPO_ROOT"
rm -rf scripts/
rm -rf tools/
rm -rf tests/
rm -rf docs/
rm -rf thoughts/
rm -f AGENTS.md
rm -f package.json
echo "  Removed scripts/, tools/, tests/, docs/, thoughts/, AGENTS.md, package.json"

# Remove v1 .claude/ (will be replaced by v2's)
rm -rf .claude/
rm -rf .claude-plugin/
rm -rf skills/
echo "  Removed .claude/, .claude-plugin/, skills/"

# ── Step 5: Promote v2 to root ──────────────────────────────────────────────
echo "5. Promoting v2/ contents to repo root..."

# Move the Python package
if [ -d "v2/tq" ]; then
    cp -R v2/tq/ tq/
    echo "  Copied v2/tq/ → tq/"
fi

# Move plugin dirs
if [ -d "v2/.claude-plugin" ]; then
    cp -R v2/.claude-plugin/ .claude-plugin/
    echo "  Copied v2/.claude-plugin/"
fi
if [ -d "v2/.claude" ]; then
    cp -R v2/.claude/ .claude/
    echo "  Copied v2/.claude/"
fi
if [ -d "v2/skills" ]; then
    cp -R v2/skills/ skills/
    echo "  Copied v2/skills/"
fi
if [ -d "v2/openclaw-plugin" ]; then
    cp -R v2/openclaw-plugin/ openclaw-plugin/
    echo "  Copied v2/openclaw-plugin/"
fi

# Copy v2 CLAUDE.md as the new project CLAUDE.md
if [ -f "v2/CLAUDE.md" ]; then
    cp v2/CLAUDE.md CLAUDE.md
    echo "  Copied v2/CLAUDE.md → CLAUDE.md"
fi

# Copy v2 README.md as the new README
if [ -f "v2/README.md" ]; then
    cp v2/README.md README.md
    echo "  Copied v2/README.md → README.md"
fi

# Remove the v2 directory (now promoted)
rm -rf v2/
echo "  Removed v2/"

# Clean pycache
find "$REPO_ROOT" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# ── Step 6: Rename tq2 → tq in all files ────────────────────────────────────
echo "6. Renaming tq2 → tq in all text files..."

# CLAUDE.md
if [ -f CLAUDE.md ]; then
    sed -i '' 's/python3 tq2/python3 -m tq/g' CLAUDE.md
    sed -i '' 's/tq2 /tq /g' CLAUDE.md
    echo "  Updated CLAUDE.md"
fi

# README.md
if [ -f README.md ]; then
    sed -i '' 's/python3 tq2/tq/g' README.md
    sed -i '' 's/tq2 /tq /g' README.md
    sed -i '' 's|  tq2 |  tq |g' README.md
    sed -i '' 's/tq2$/tq/' README.md
    echo "  Updated README.md"
fi

# Skills
if [ -f skills/tq/SKILL.md ]; then
    sed -i '' 's/tq2 /tq /g' skills/tq/SKILL.md
    echo "  Updated skills/tq/SKILL.md"
fi

# Claude commands
if [ -f .claude/commands/tq-reply.md ]; then
    sed -i '' 's/Bash(tq2,python3)/Bash(tq,python3)/g' .claude/commands/tq-reply.md
    sed -i '' 's/tq2 reply/tq reply/g' .claude/commands/tq-reply.md
    sed -i '' 's/tq2 is not/tq is not/g' .claude/commands/tq-reply.md
    sed -i '' 's|python3 /path/to/v2/tq2|python3 -m tq|g' .claude/commands/tq-reply.md
    echo "  Updated .claude/commands/tq-reply.md"
fi

# OpenClaw plugin
if [ -f openclaw-plugin/openclaw.plugin.json ]; then
    sed -i '' 's/"tq2"/"tq"/g' openclaw-plugin/openclaw.plugin.json
    echo "  Updated openclaw-plugin/openclaw.plugin.json"
fi
if [ -f openclaw-plugin/src/tq-bridge.ts ]; then
    sed -i '' 's/"tq2"/"tq"/g' openclaw-plugin/src/tq-bridge.ts
    echo "  Updated openclaw-plugin/src/tq-bridge.ts"
fi
if [ -f openclaw-plugin/src/index.ts ]; then
    sed -i '' 's/"tq2"/"tq"/g' openclaw-plugin/src/index.ts
    echo "  Updated openclaw-plugin/src/index.ts"
fi

# ── Step 7: Install `tq` wrapper ────────────────────────────────────────────
echo "7. Installing tq wrapper to $INSTALL_DIR..."

TQ_WRAPPER="$INSTALL_DIR/tq"
cat > "$TQ_WRAPPER" <<'WRAPPER'
#!/usr/bin/env bash
# tq — Claude Code sessions via Telegram + tmux
# Wrapper that invokes the tq Python package
set -euo pipefail
TQ_ROOT="@@TQ_ROOT@@"
exec python3 -m tq "$@"
WRAPPER

# Patch in the actual repo root (for PYTHONPATH if needed)
sed -i '' "s|@@TQ_ROOT@@|$REPO_ROOT|" "$TQ_WRAPPER"

# Add PYTHONPATH so `python3 -m tq` finds the package
sed -i '' "s|exec python3 -m tq|export PYTHONPATH=\"\$TQ_ROOT:\${PYTHONPATH:-}\"\nexec python3 -m tq|" "$TQ_WRAPPER"

chmod +x "$TQ_WRAPPER"
echo "  Installed $TQ_WRAPPER"

# ── Step 8: Update .gitignore ────────────────────────────────────────────────
echo "8. Updating .gitignore..."
cat > "$REPO_ROOT/.gitignore" <<'EOF'
# Runtime state — contains OAuth tokens
.tq/

# Python
__pycache__/
*.pyc

# AI onboarding scratch
.ai-onboard-scratch/
EOF
echo "  Done."

# ── Verify ───────────────────────────────────────────────────────────────────
echo ""
echo "=== Verification ==="
if command -v tq &>/dev/null; then
    echo "✓ tq is on PATH: $(which tq)"
    tq --help 2>/dev/null && echo "✓ tq --help works" || echo "✗ tq --help failed"
else
    echo "✗ tq not found on PATH — check $INSTALL_DIR is in \$PATH"
fi

echo ""
echo "=== Migration complete ==="
echo ""
echo "Next steps:"
echo "  1. Run 'tq setup' to configure Telegram (reuses existing ~/.tq/config.json if present)"
echo "  2. Run 'tq daemon start' to start the Telegram daemon"
echo "  3. Commit the changes: git add -p && git commit -m 'migrate to tq v2'"
echo "  4. Delete this script: rm migrate-v1-to-v2.sh"
