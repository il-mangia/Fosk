#!/usr/bin/env bash
# ─────────────────────────────────────────────
#  Fosk — start server
#  Usage: ./start.sh [port]
# ─────────────────────────────────────────────
set -e

PORT=${1:-8000}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Create venv if not present
if [ ! -d ".venv" ]; then
  echo "📦 Creating virtual environment…"
  python3 -m venv .venv
fi

source .venv/bin/activate
echo "📦 Checking dependencies…"
pip install -r requirements.txt -q --break-system-packages

echo "
╔══════════════════════════════════════════╗
║    🎵  Fosk Music Server  v1.0           ║
╠══════════════════════════════════════════╣
║  LAN:  http://$(hostname -I | awk '{print $1}'):${PORT}          ║
║  Local: http://127.0.0.1:${PORT}              ║
╚══════════════════════════════════════════╝
"

exec uvicorn main:app --host 0.0.0.0 --port "$PORT"
