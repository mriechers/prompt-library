# Run log schema

A shared contract for recording what happened on each prompt review, so that
runs feed back into improving the prompts instead of evaporating.

**Send this file to any other implementation of the review workflow.** Agreeing on
four field names now is cheaper than reconciling two formats later.

## Location

```
~/prompt-library-notes/runs.jsonl
```

**Outside the repo, deliberately.** A `.gitignore` inside the repo is one `git add -f`
away from a public commit, and this log records what you thought about your own
prompts. If you later decide the log is safe to publish, moving it into the repo is a
one-line change in `.claude/commands/review-prompt.md` — but start private and relax
later, not the other way around.

## Format

One JSON object per line (JSONL). Append only; never rewrite earlier lines.

JSONL rather than a single JSON array because appending is a one-line operation with
no parse-modify-write cycle, so two implementations writing concurrently can't
clobber each other's work.

## Record kinds

Two writers append to this log, and they write different shapes. Every line carries a
`kind` saying which it is, so a reader can dispatch on one field instead of guessing
from which keys happen to be present.

| `kind` | Written by | Answers |
|---|---|---|
| `review` | `/review-prompt` | Which proposed changes were accepted or rejected, and how confident the reviewer was |
| `expansion` | the `expand-prompt` skill | How much revision an expansion needed, against which version of the base prompt |

`kind` is absent on lines written before this field existed. Treat a missing `kind` as
`review` — that was the only shape at the time.

## Review records

```json
{
  "ts": "2026-09-05T16:18:00Z",
  "prompt": "prompt-architect.md",
  "surface": "claude-code",
  "reviewed_against": "Claude Opus 5",
  "sources": ["prompt-audit", "websearch"],
  "items": [
    {
      "label": "stale model categories",
      "confidence": "high",
      "verdict": "accepted",
      "note": ""
    },
    {
      "label": "closing recap",
      "confidence": "medium",
      "verdict": "rejected",
      "note": "already the careful version; caps recap at 2-3 constraints"
    }
  ]
}
```

| Field | Values | Why it's here |
|---|---|---|
| `ts` | ISO 8601 UTC | Ordering, and measuring review cadence against model releases |
| `prompt` | filename | Which prompt; group by this to see a prompt's history |
| `surface` | `claude-code` \| `claude-ai-project` \| `expand-prompt-skill` | Distinguishes implementations writing to the same log |
| `reviewed_against` | model name | What the review was measured against |
| `sources` | `prompt-audit` \| `websearch` \| `webfetch` \| `models-api` | Which research paths were actually available; a review with `["websearch"]` alone is weaker evidence than one with all four |
| `items[].label` | short string | Human-readable handle for the proposed change |
| `items[].confidence` | `high` \| `medium` \| `low` | What the reviewer claimed *before* seeing the verdict |
| `items[].verdict` | `accepted` \| `rejected` | The decision |
| `items[].note` | string | Reasoning on rejection. Optional on acceptance |

## Expansion records

Written by `.claude/skills/expand-prompt/scripts/log-run.sh` after each expansion.

```json
{
  "ts": "2026-09-09T03:19:57Z",
  "kind": "expansion",
  "prompt": "prompt-architect.md",
  "surface": "expand-prompt-skill",
  "base_prompt_validated": "2026-09-05",
  "mode": "default",
  "revision_rounds": 2
}
```

| Field | Values | Why it's here |
|---|---|---|
| `base_prompt_validated` | date, or `null` | The `last_validated` of the base prompt this run used, read from the skill's synced copy. `null` when that copy has no header. This is the field that makes the record useful rather than merely present — without it an outcome can't be attributed to a version. |
| `mode` | `default` \| `grillme` \| `audit` \| `tighten` | Which mode ran. Revision counts are only comparable within a mode. |
| `revision_rounds` | integer ≥ 0 | How many times the user asked for changes before accepting. `0` means the first pass landed. |

`ts`, `prompt`, and `surface` carry the same meaning as in a review record.

**There is deliberately no free-text field.** The script takes a mode from a fixed
allowlist and an integer, so the "labels and counts only, never content" rule below is
enforced by the interface rather than by remembering it.

Grouped by `base_prompt_validated`, these records answer the question a changelog
can't: did the last revision to the base prompt actually make expansions land in fewer
rounds? That is the evidence `/review-prompt` exists to act on.

## What this is for

`confidence` paired with `verdict` is the point. Over enough runs it answers a
question nothing else here can: **is the reviewer's confidence calibrated?** A pattern
of high-confidence items getting rejected means the review process is overconfident
and its criteria need tightening. A pattern of low-confidence items getting accepted
means it's sandbagging and burying good findings under hedges.

That signal only exists if rejections are recorded as carefully as acceptances.
A log of accepted changes is a changelog; a log of both is evidence.

## Rules for implementers

- Write the line **after** the user decides, never before — the verdict is the payload.
- Record rejections. A log that only captures accepted changes throws away half the
  signal and all of the calibration data.
- Never write prompt bodies, transcript excerpts, or conversation content into this
  file. Labels and verdicts only. It stays small and stays safe to keep around.
- One line per review run, not per item.
