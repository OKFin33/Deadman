#!/usr/bin/env bash
#
# 看剧搭子 / Deadman — one-click local launch (macOS double-click or `bash start.command`).
#
# What it does:
#   1. installs the Python backend deps (best-effort);
#   2. installs + builds the React frontend (frontend/dist);
#   3. starts the Local Server (uvicorn) at http://127.0.0.1:7861 (foreground);
#   4. opens the 观众端 Stage demo in your browser.
#
# The Stage 观众端 demo runs with NO API keys — preset echoes are baked into the
# reviewed packs. Keys are ONLY needed for Studio LIVE authoring / custom echo /
# ASR upload (copy .env.example -> .env).

set -uo pipefail

# --- cd to this script's own directory (works for double-click + `bash start.command`) -------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
cd "$SCRIPT_DIR" || { echo "✗ Could not cd into the project directory ($SCRIPT_DIR)." >&2; exit 1; }

HOST="127.0.0.1"
PORT="7861"
STAGE_URL="http://${HOST}:${PORT}/Stage/"

say()  { printf '\n\033[1;36m▶ %s\033[0m\n' "$*"; }
ok()   { printf '\033[1;32m  ✓ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m  ! %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

say "看剧搭子 / Deadman — 一键启动 / one-click launch"
echo "  project: $SCRIPT_DIR"

# --- prerequisites ---------------------------------------------------------------------------
command -v python3 >/dev/null 2>&1 || die "python3 not found. Install Python 3, then re-run."
command -v npm     >/dev/null 2>&1 || die "npm not found. Install Node.js (which provides npm), then re-run."
ok "python3: $(python3 --version 2>&1)"
ok "node:    $(node --version 2>&1 || echo '?')  /  npm: $(npm --version 2>&1)"

# --- credentials note (Stage needs none) -----------------------------------------------------
if [ ! -f .env ]; then
  warn "No .env found."
  echo "    The Stage 观众端 demo runs with NO keys — preset echoes are baked into reviewed packs."
  echo "    Studio LIVE authoring / custom echo / ASR upload need creds:  cp .env.example .env  (then fill it in)."
fi

# --- 1. Python backend deps (best-effort; tolerate already-installed) -------------------------
say "1/3 · Installing Python deps (requirements.txt)"
if python3 -m pip install -r requirements.txt; then
  ok "Python deps ready."
else
  warn "pip install reported an issue — continuing (deps may already be installed)."
fi

# --- 2. Frontend install + build -------------------------------------------------------------
say "2/3 · Building the frontend (npm install && npm run build)"
(
  set -e
  cd frontend
  npm install
  npm run build
) || die "Frontend build failed. Fix the error above, then re-run start.command."
ok "Frontend built → frontend/dist"

# --- 3. Start the Local Server (foreground) + open the browser -------------------------------
say "3/3 · Starting the Local Server at http://${HOST}:${PORT}"
echo "  • 观众端 Stage : ${STAGE_URL}"
echo "  • 制作端 Studio: http://${HOST}:${PORT}/studio/"
echo "  (press Ctrl+C to stop)"

# Open the Stage demo once the server answers (background poll → `open`); the server then runs
# in the foreground. If the browser-open helper is missing we just print the URL.
(
  for _ in $(seq 1 60); do
    if curl -fsS "http://${HOST}:${PORT}/api/deadman/health" >/dev/null 2>&1; then
      if command -v open >/dev/null 2>&1; then
        open "${STAGE_URL}"
      else
        printf '\n  Open this in your browser: %s\n' "${STAGE_URL}"
      fi
      exit 0
    fi
    sleep 1
  done
  printf '\n  Server did not answer yet — open this manually: %s\n' "${STAGE_URL}"
) &

exec python3 -m uvicorn server:app --host "${HOST}" --port "${PORT}"
