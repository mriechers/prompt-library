#!/usr/bin/env bash
# sync-base-prompt.sh [--check]
#
# The prompt-architect base prompt is CANONICAL in this repo — the one you paste
# into a Claude Project, and the one /review-prompt re-validates and versions.
# The expand-prompt skill needs its own copy of that text, because a skill is
# installed as a self-contained directory: anything outside the skill folder is
# not there at runtime.
#
# This script is the only thing allowed to write that copy.
#
#   (no args)  copy the base prompt -> skill
#   --check    regenerate to a temp file and diff; exit 1 if the committed copy
#              has drifted. READ-ONLY. CI runs this mode, so an edit to the base
#              prompt that forgets to sync fails the build instead of silently
#              shipping a stale skill.
#
# Exit: 0 in sync (or written) - 1 drifted (--check only) - 2 usage/missing source.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/.claude/skills/expand-prompt/references/prompt-architect.md"
REL_DEST="${DEST#"$ROOT/"}"

# Two locations, in precedence order. prompts/ is where the versioning convention
# put it; the repo root is where it lived before. Accepting both means this script
# does not care whether the prompts/ move has landed yet — no flag day, and no
# window where a rebase leaves the sync pointing at a file that isn't there.
find_src() {
  local c
  for c in "$ROOT/prompts/prompt-architect.md" "$ROOT/prompt-architect.md"; do
    [ -r "$c" ] && { printf '%s' "$c"; return 0; }
  done
  return 1
}

BANNER='<!-- GENERATED FILE — DO NOT EDIT.
     Synced by scripts/sync-base-prompt.sh from the canonical prompt-architect.md.
     Edit the canonical file, then re-run the script. -->'

MODE="write"
case "${1:-}" in
  --check) MODE="check" ;;
  "")      ;;
  -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
  *) echo "usage: sync-base-prompt.sh [--check]" >&2; exit 2 ;;
esac

SRC="$(find_src)" || {
  echo "FAIL: no prompt-architect.md in $ROOT/prompts/ or $ROOT/" >&2
  exit 2
}
REL_SRC="${SRC#"$ROOT/"}"

# One renderer for both modes, so "what --check compares against" and "what a write
# produces" can never be two different things.
#
# The banner goes AFTER the YAML frontmatter, never above it. Frontmatter is only
# frontmatter when it starts on line 1 — prepending anything demotes the header
# (last_validated, validated_against, recommended_effort) to body text, which is
# exactly the mis-parse /review-prompt's own parsing note warns about.
render() {
  if [ "$(head -1 "$SRC")" = "---" ]; then
    awk -v banner="$BANNER" '
      NR == 1        { print; next }                       # opening ---
      !ins && /^---[[:space:]]*$/ {                        # closing ---
        print; print ""; print banner; ins = 1; next
      }
      { print }
    ' "$SRC"
  else
    printf '%s\n\n' "$BANNER"; cat "$SRC"
  fi
}

if [ "$MODE" = "check" ]; then
  [ -r "$DEST" ] || {
    echo "DRIFT: $REL_DEST is missing. Run: scripts/sync-base-prompt.sh" >&2
    exit 1
  }
  TMP="$(mktemp)"
  trap 'rm -f "$TMP"' EXIT
  render > "$TMP"
  if diff -u "$DEST" "$TMP" --label "$REL_DEST (committed)" --label "$REL_SRC (current)"; then
    echo "OK: $REL_DEST is in sync with $REL_SRC"
    exit 0
  fi
  echo "" >&2
  echo "DRIFT: $REL_SRC changed without re-running the sync." >&2
  echo "Fix:   scripts/sync-base-prompt.sh && git add $REL_DEST" >&2
  exit 1
fi

mkdir -p "$(dirname "$DEST")"
render > "$DEST"
echo "synced: $REL_SRC -> $REL_DEST"
