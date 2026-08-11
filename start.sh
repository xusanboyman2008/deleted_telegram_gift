#!/usr/bin/env bash
# ════════════════════════════════════════════════════════
#  Deleted Gift Shop — Full Launcher
#  Usage: bash start.sh [ADMIN_TG_ID]
# ════════════════════════════════════════════════════════

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"

if [ -f "$ROOT/.env" ]; then
  export $(grep -v '^#' "$ROOT/.env" | xargs)
fi

echo ""
echo "  🎁  Deleted Gift Shop Launcher"
echo "  ══════════════════════════════"
echo ""

# ── 1. Admin ID ────────────────────────────────────────
if [ -n "$1" ]; then
  export ADMIN_ID="$1"
  echo "  ✅  Admin ID: $ADMIN_ID"
elif [ -z "$ADMIN_ID" ]; then
  echo "  ⚠️   No ADMIN_ID set."
  echo "      Pass your Telegram numeric ID as argument:"
  echo "      bash start.sh 123456789"
  echo ""
  read -rp "  Enter your Telegram ID (or press Enter to skip): " ADMIN_ID
  export ADMIN_ID="${ADMIN_ID:-0}"
fi

# ── 2. Remove broken venv if present ─────────────────────
rm -rf "$ROOT/.venv" 2>/dev/null || true
PY=$(which python3)

echo "  📦  Checking dependencies…"
if command -v npx &>/dev/null; then
  echo "  ⚡  Minifying frontend JS & CSS bundles…"
  npx terser "$ROOT/frontend/app.js" -o "$ROOT/frontend/app.min.js" --compress --mangle 2>/dev/null || true
  npx terser "$ROOT/frontend/chat.js" -o "$ROOT/frontend/chat.min.js" --compress --mangle 2>/dev/null || true
  npx clean-css-cli -o "$ROOT/frontend/style.min.css" "$ROOT/frontend/style.css" 2>/dev/null || true
fi

# ── 3. Base URL ──────────────────────────────────────────
export BASE_URL="${BASE_URL:-http://localhost:8000}"
echo ""
echo "  ┌─────────────────────────────────────────────────"
echo "  │  Base URL:  $BASE_URL"
echo "  │  Admin ID:  $ADMIN_ID"
echo "  └─────────────────────────────────────────────────"
echo ""

# ── 4. Update bot name/description via Telegram API ───
if [ -n "$BOT_TOKEN" ]; then
  curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setMyName" \
       -d "name=Deleted Gift Shop" > /dev/null
  curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setMyDescription" \
       -d "description=Buy and send rare deleted Telegram gifts to anyone using ⭐ Telegram Stars. Safe, fast, anonymous." > /dev/null
  curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setMyShortDescription" \
       -d "short_description=Send rare deleted Telegram gifts with ⭐ Stars" > /dev/null
  echo "  🤖  Bot name & description updated."
fi

# ── 5. Start FastAPI ───────────────────────────────────
echo "  🚀  Starting backend server…"
echo ""
fuser -k 8000/tcp 2>/dev/null || true
cd "$BACKEND"
exec "$PY" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
