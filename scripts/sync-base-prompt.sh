#!/usr/bin/env bash
# sync-base-prompt.sh [--check]
#
# prompt-architect.md at the repo root is the CANONICAL base prompt — the one you
# paste into a Claude Project, and the one you revise as models change. The
# expand-prompt skill needs its own copy of that text, because a skill gets vendored
# and installed as a self-contained directory: anything outside the skill folder is
# not there at runtime.
#
# This script is the only thing allowed to write that copy.
#
#   (no args)  copy root -> skill, prepending a generated-file header
#   --check    regenerate to a temp file and diff; exit 1 if the committed copy has
#              drifted. READ-ONLY — it reports, it never writes. CI runs this mode,
#              so a root edit that forgets to sync fails the build instead of
#              silently shipping a stale skill.
#
# Exit: 0 in sync (or written) - 1 drifted (--check only) - 2 usage/missing source.

set -euo pipefail

# Resolve the repo root from this script's own location, not the caller's cwd, so
# the script works the same from anywhere (a CI runner, a git hook, your shell).
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/prompt-architect.md"
DEST="$ROOT/.claude/skills/expand-prompt/references/prompt-architect.md"
REL_DEST="${DEST#"$ROOT/"}"

HEADER='<!-- GENERATED FILE — DO NOT EDIT.
     Synced from prompt-architect.md at the repo root by scripts/sync-base-prompt.sh.
     Edit the root file, then re-run the script. -->'

MODE="write"
case "${1:-}" in
  --check) MODE="check" ;;
  "")      ;;
  -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
  *) echo "usage: sync-base-prompt.sh [--check]" >&2; exit 2 ;;
esac

[ -r "$SRC" ] || { echo "FAIL: no base prompt at $SRC" >&2; exit 2; }

# One renderer, used by both modes — so "what --check compares against" and "what a
# write produces" can never be two different things.
render() { printf '%s\n\n' "$HEADER"; cat "$SRC"; }

if [ "$MODE" = "check" ]; then
  [ -r "$DEST" ] || {
    echo "DRIFT: $REL_DEST is missing. Run: scripts/sync-base-prompt.sh" >&2
    exit 1
  }
  TMP="$(mktemp)"
  trap 'rm -f "$TMP"' EXIT
  render > "$TMP"
  if diff -u "$DEST" "$TMP" --label "$REL_DEST (committed)" --label "prompt-architect.md (current)"; then
    echo "OK: $REL_DEST is in sync with prompt-architect.md"
    exit 0
  fi
  echo "" >&2
  echo "DRIFT: prompt-architect.md changed without re-running the sync." >&2
  echo "Fix:   scripts/sync-base-prompt.sh && git add $REL_DEST" >&2
  exit 1
fi

mkdir -p "$(dirname "$DEST")"
render > "$DEST"
echo "synced: prompt-architect.md -> $REL_DEST"
