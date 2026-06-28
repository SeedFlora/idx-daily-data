#!/usr/bin/env bash
#
# Scrapes, then commits in up to 3 groups (IDX / Japan / Crypto) so trading days
# show ~3 real commits. No fake/empty commits — a group is committed only if its
# data actually changed. Pushes once at the end.
#
set -euo pipefail

REPO_DIR="/opt/idx-daily-data"
VENV_PY="$REPO_DIR/.venv/bin/python"
cd "$REPO_DIR"

"$VENV_PY" "$REPO_DIR/scrape.py"

DATE="$(date +%F)"
COMMITS=0

commit_group() {
    local label="$1"; shift
    shopt -s nullglob
    local files=()
    for pat in "$@"; do files+=( $pat ); done
    shopt -u nullglob
    [ ${#files[@]} -eq 0 ] && return 0
    git add -- "${files[@]}"
    if git diff --cached --quiet; then return 0; fi
    git commit -q -m "data(${label}): ${DATE}"
    COMMITS=$((COMMITS+1))
}

# IDX + Jakarta index
commit_group "IDX"   'data/*.JK.csv' 'data/_JKSE.csv'
# Japan + Nikkei index
commit_group "Japan" 'data/*.T.csv'  'data/_N225.csv'
# Crypto + manifest + anything else left
git add -A
if ! git diff --cached --quiet; then
    git commit -q -m "data(Crypto): ${DATE}"
    COMMITS=$((COMMITS+1))
fi

if [ "$COMMITS" -gt 0 ]; then
    git push -q origin main
    echo "pushed ${COMMITS} commit(s) for ${DATE}"
else
    echo "no changes — nothing to push"
fi
