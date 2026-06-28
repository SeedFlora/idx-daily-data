#!/usr/bin/env bash
#
# Scrapes, then commits per market group (IDX / Japan / US-Global / Crypto) so
# trading days show several real commits. A group is committed only if its data
# changed (no fake/empty commits). Pushes once at the end.
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

commit_group "IDX"       'data/*.JK.csv' 'data/JKSE.csv'
commit_group "Japan"     'data/*.T.csv'  'data/N225.csv'
commit_group "US-Global" 'data/GSPC.csv' 'data/IXIC.csv' 'data/DJI.csv'

# Crypto + manifest + anything else
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
