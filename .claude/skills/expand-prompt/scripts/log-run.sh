#!/usr/bin/env bash
# log-run.sh <mode> <revision-rounds> — append one expansion run to the run log.
#
#   mode             default | grillme | audit | tighten
#   revision-rounds  how many times the user asked for changes before accepting (0+)
#
# Writes one JSONL line to ~/prompt-library-notes/runs.jsonl — outside the repo, per
# docs/run-log-schema.md. Append-only; never rewrites earlier lines.
#
# THIS SCRIPT CANNOT LEAK PROMPT CONTENT, BY CONSTRUCTION. Every field is either
# generated here or drawn from a fixed allowlist — there is no free-text parameter to
# pass a prompt body, transcript, or conversation excerpt through. The schema's rule
# ("labels and verdicts only, never content") is enforced by the interface rather than
# by remembering to follow it.
#
# base_prompt_validated ties the run to a version of the base prompt, read from the
# synced reference copy's frontmatter. Null until the versioning header lands — a run
# logged before then is honestly marked as untied to a version, not guessed at.
#
# Exit: 0 logged - 1 could not write (caller should mention it and carry on) - 2 usage.

set -uo pipefail

MODE="${1:-}"
ROUNDS="${2:-}"

case "$MODE" in
  default|grillme|audit|tighten) ;;
  *) echo "usage: log-run.sh <default|grillme|audit|tighten> <revision-rounds>" >&2; exit 2 ;;
esac
case "$ROUNDS" in
  ''|*[!0-9]*) echo "revision-rounds must be a non-negative integer, got: '$ROUNDS'" >&2; exit 2 ;;
esac

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REF="$HERE/../references/prompt-architect.md"

# Pull last_validated out of the reference copy's YAML frontmatter, if it has one.
# Only the block bounded by --- on line 1 and the next --- counts; the prompt body
# uses --- as a horizontal rule several times, and treating one of those as the
# closing delimiter would read a date out of prose.
read_validated() {
  [ -r "$REF" ] || return 1
  [ "$(head -1 "$REF")" = "---" ] || return 1
  awk '
    NR == 1 { next }
    /^---[[:space:]]*$/ { exit }
    /^last_validated:/ { sub(/^last_validated:[[:space:]]*/, ""); gsub(/"/, ""); print; exit }
  ' "$REF"
}

VALIDATED="$(read_validated || true)"
if [ -n "$VALIDATED" ]; then VALIDATED_JSON="\"$VALIDATED\""; else VALIDATED_JSON="null"; fi

DIR="${PROMPT_LIBRARY_NOTES_DIR:-$HOME/prompt-library-notes}"
LOG="$DIR/runs.jsonl"

mkdir -p "$DIR" 2>/dev/null || {
  echo "SKIP: could not create $DIR — run not logged" >&2; exit 1; }

printf '{"ts":"%s","kind":"expansion","prompt":"prompt-architect.md","surface":"expand-prompt-skill","base_prompt_validated":%s,"mode":"%s","revision_rounds":%s}\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$VALIDATED_JSON" "$MODE" "$ROUNDS" >> "$LOG" 2>/dev/null || {
  echo "SKIP: could not append to $LOG — run not logged" >&2; exit 1; }

echo "logged: $MODE run, $ROUNDS revision round(s) -> $LOG"
