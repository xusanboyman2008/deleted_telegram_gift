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
# Use system python3 directly (venv not needed)
PY=$(which python3)

echo "  📦  Installing dependencies (system pip)…"
pip3 install --break-system-packages -q -r "$BACKEND/requirements.txt" 2>/dev/null || \
  pip3 install -q -r "$BACKEND/requirements.txt" 2>/dev/null || true

# ── 3. ngrok ───────────────────────────────────────────
if ! command -v ngrok &>/dev/null; then
  echo ""
  echo "  ❌  ngrok not found! Install it:"
  echo "      https://ngrok.com/download"
  echo "      Or: snap install ngrok"
  echo ""
  exit 1
fi

# Check if ngrok is already active
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for t in data.get('tunnels', []):
        if t.get('proto') == 'https':
            print(t['public_url'])
            break
except:
    pass
" || true)

if [ -z "$NGROK_URL" ]; then
  echo "  🌐  Starting ngrok tunnel on port 8000…"
  ngrok http 8000 --log=stdout > /tmp/ngrok_gift.log 2>&1 &
  NGROK_PID=$!
  sleep 3
  NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for t in data.get('tunnels', []):
        if t.get('proto') == 'https':
            print(t['public_url'])
            break
except:
    pass
")
fi

if [ -z "$NGROK_URL" ]; then
  echo "  ❌  Could not get ngrok URL. Check /tmp/ngrok_gift.log"
  kill $NGROK_PID 2>/dev/null
  exit 1
fi

export BASE_URL="$NGROK_URL"
echo ""
echo "  ✅  Tunnel active: $NGROK_URL"
echo ""
echo "  ┌─────────────────────────────────────────────────"
echo "  │  Mini App URL:  $NGROK_URL/index.html"
echo "  │  Admin ID:      $ADMIN_ID"
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
cd "$BACKEND"
exec "$PY" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# cleanup on exit
trap "kill $NGROK_PID 2>/dev/null; echo '  👋  Stopped.'" EXIT
