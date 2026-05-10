#!/usr/bin/env bash
# Launch the Database Structure Downloader, pulling the latest dev branch
# first when it's safe. The launch always succeeds — a failed git or fetch
# never blocks the app, it just runs whatever is currently checked out.

set -u

REPO="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
cd "$REPO"

if [ -d .git ]; then
    branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
    if [ "$branch" = "dev" ] \
        && git diff --quiet 2>/dev/null \
        && git diff --cached --quiet 2>/dev/null; then
        git fetch --quiet origin dev 2>/dev/null || true
        git merge --ff-only --quiet origin/dev 2>/dev/null || true
    fi
fi

exec ./.venv/bin/python -m db_structure_downloader
