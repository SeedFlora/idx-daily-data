#!/usr/bin/env bash
#
# Runs the scraper, then commits + pushes ONLY if data actually changed.
# Designed for cron. No fake/empty commits.
#
set -euo pipefail

REPO_DIR="/opt/idx-daily-data"
VENV_PY="$REPO_DIR/.venv/bin/python"

cd "$REPO_DIR"

# 1. scrape (writes/updates files under data/)
"$VENV_PY" "$REPO_DIR/scrape.py"

# 2. stage everything
git add -A

# 3. commit only if there's a real diff
if git diff --cached --quiet; then
    echo "no changes — skipping commit"
    exit 0
fi

DATE="$(date +%F)"
FILES="$(git diff --cached --name-only -- data/ | wc -l | tr -d ' ')"
git commit -q -m "data: ${DATE} (${FILES} files updated)"
git push -q origin main
echo "pushed commit for ${DATE} (${FILES} files)"
