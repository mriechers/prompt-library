---
description: Re-check a prompt against current model guidance and propose changes
argument-hint: <prompt filename, e.g. prompt-architect.md>
allowed-tools: Read, Edit, Write, WebSearch, WebFetch, Bash(ls:*), Bash(date:*)
---

<!--
  HOW THIS FILE WORKS (for the human reading it in six months)

  This is a Claude Code slash command. The filename sets the command name:
  review-prompt.md  ->  /review-prompt

  The YAML block above is command config, not part of the instructions:
    description    text shown in the /-menu
    argument-hint  greyed-out hint shown while typing the command
    allowed-tools  the ONLY tools this command may use. Anything not listed
                   here is unavailable, which is deliberate: a command that
                   can't run arbitrary shell commands can't surprise you.

  Everything below the second --- is a prompt sent to Claude when you run
  the command. $ARGUMENTS is replaced with whatever you typed after the
  command name. So `/review-prompt prompt-architect.md` substitutes
  "prompt-architect.md" wherever $ARGUMENTS appears.
-->

# Task

Re-validate the prompt file `$ARGUMENTS` against current published prompting
guidance, and propose changes for individual approval.

The file is in `prompts/`. If `$ARGUMENTS` is empty, list the files in `prompts/`
and ask which one. If it names a file that doesn't exist, say so and list what does
— do not guess at a near match.

## Step 1 — Read the header

Read `prompts/$ARGUMENTS` and pull `last_validated` and `validated_against` from the
YAML frontmatter at the top.

<!--
  Parsing note: this file uses --- as a horizontal rule in its prose, several
  times. Frontmatter is ONLY the block bounded by --- on line 1 and the next ---
  after it. Do not treat later --- lines as delimiters, and never truncate the
  prompt body at one.
-->

If there is no frontmatter, say so and stop. Offer to add a baseline header, but do
not review a file with no established baseline — there'd be no date to search from.

Report both values before continuing, so the search window is visible and correctable.

## Step 2 — Confirm web search works

This review is worthless without sources. Attempt a `WebSearch`. If the tool is
unavailable or returns nothing usable, **stop and say so plainly.** Do not fall back
on recalled knowledge and present it as a review — a review that consulted no sources
but looks thorough is the failure this command exists to prevent.

## Step 3 — Search for what changed

Find guidance published **since `last_validated`** that would affect this prompt.

Search in this order, and weight them in this order:

1. **Official vendor documentation** — restrict with
   `allowed_domains: ["docs.anthropic.com", "anthropic.com"]`. Model cards, prompting
   guides, release notes, migration notes.
2. **Official guidance for whichever model the prompt now targets**, if that differs
   from `validated_against`.
3. **Everything else** — only to corroborate something from 1 or 2, never as the sole
   basis for a proposed change.

Ignore undated posts, and anything published before `last_validated` — it was already
in effect at the last review.

If the search turns up nothing substantive, say that. "No changes needed" is a valid
and useful outcome; bump `last_validated` and log it. Do not manufacture changes to
justify the run.

## Step 4 — Propose a diff, do not rewrite

Present each proposed change **separately and numbered**, in this shape:

> **N. <short label>**
> **Current:** <the exact existing text>
> **Proposed:** <the replacement>
> **Why:** <what specifically changed in the guidance, with the source URL>
> **Confidence:** high / medium / low

Rules:
- One concern per numbered item, so each can be accepted or rejected on its own.
- Quote real text from the file. Never paraphrase what's currently there.
- Every item cites a source. An item you can't source is an opinion — drop it or
  label it clearly as your own judgment, not as guidance.
- Do not output a rewritten file. The whole point is approving changes individually.

Then **stop and wait.** Do not edit anything yet.

## Step 5 — Apply what's approved

Only after explicit approval, and only the approved items:

1. Apply the approved edits to `prompts/$ARGUMENTS`.
2. Update the header: set `last_validated` to today's date and `validated_against`
   to the model reviewed against. Set `status: current`.
3. Append an entry to `CHANGELOG.md` under that prompt's section, newest first:

   ```
   ### YYYY-MM-DD — <short label>
   <What changed.>
   <Why — the guidance that drove it, so this isn't relitigated later.>
   ```

   Two or three lines. The "why" is the part worth writing; it's what git history
   won't give back.

4. If some items were rejected, note that in the CHANGELOG entry too — a rejected
   change that gets re-proposed every six months is its own kind of waste.

Do not commit. Leave the changes staged in the working tree for review.
