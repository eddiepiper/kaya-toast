#!/bin/bash
set -euo pipefail

PROJECT_DIR="/Users/edwardchiang/Documents/AI PM news agent/kaya-toast"
PROJECT_PARENT="/Users/edwardchiang/Documents/AI PM news agent"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/daily_update.log"
SUBTREE_PREFIX="kaya-toast"

mkdir -p "$LOG_DIR"
exec >> "$LOG_FILE" 2>&1

echo "[$(date -Iseconds)] Starting kaya-toast daily update"

cd "$PROJECT_DIR"

echo "[$(date -Iseconds)] Running daily workflow"
python3 -m kaya_toast daily

echo "[$(date -Iseconds)] Running weekly workflow"
python3 -m kaya_toast weekly

echo "[$(date -Iseconds)] Running strategy workflow"
python3 -m kaya_toast strategy

echo "[$(date -Iseconds)] Staging generated outputs"
git add \
  data/feedback.json \
  data/run_history.json \
  data/thinking_memory.json \
  reports/ \
  drafts/

echo "[$(date -Iseconds)] Committing generated outputs"
if git diff --cached --quiet; then
  echo "[$(date -Iseconds)] No generated output changes to commit"
else
  git commit -m "Update kaya-toast daily reports"
fi

REMOTE_URL="$(git remote get-url origin 2>/dev/null || true)"
if [ -z "$REMOTE_URL" ]; then
  echo "[$(date -Iseconds)] ERROR: git remote 'origin' is not configured"
  exit 1
fi

GIT_ROOT="$(git rev-parse --show-toplevel)"
if [ "$GIT_ROOT" = "$PROJECT_DIR" ]; then
  echo "[$(date -Iseconds)] Pushing standalone repo to origin main"
  git push origin main
else
  echo "[$(date -Iseconds)] Pushing kaya-toast subtree to origin main"
  cd "$PROJECT_PARENT"
  SUBTREE_COMMIT="$(git subtree split --prefix="$SUBTREE_PREFIX" HEAD)"
  git push origin "$SUBTREE_COMMIT:main"
fi

echo "[$(date -Iseconds)] kaya-toast daily update complete"
