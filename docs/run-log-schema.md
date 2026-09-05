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

## Schema

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
| `surface` | `claude-code` \| `claude-ai-project` | Distinguishes implementations writing to the same log |
| `reviewed_against` | model name | What the review was measured against |
| `sources` | `prompt-audit` \| `websearch` \| `webfetch` \| `models-api` | Which research paths were actually available; a review with `["websearch"]` alone is weaker evidence than one with all four |
| `items[].label` | short string | Human-readable handle for the proposed change |
| `items[].confidence` | `high` \| `medium` \| `low` | What the reviewer claimed *before* seeing the verdict |
| `items[].verdict` | `accepted` \| `rejected` | The decision |
| `items[].note` | string | Reasoning on rejection. Optional on acceptance |

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
