---
description: Re-check a prompt against current model guidance and propose changes
argument-hint: <prompt filename, e.g. prompt-architect.md>
allowed-tools: Read, Edit, Write, Skill, WebSearch, WebFetch, Bash(ls:*), Bash(date:*), Bash(curl:*), Bash(mkdir:*), Bash(cat:*)
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
                   `Bash(curl:*)` is here only for the Models API check in
                   Step 2; `Skill` is here only for Step 3.

  Everything below the second --- is a prompt sent to Claude when you run
  the command. $ARGUMENTS is replaced with whatever you typed after the
  command name. So `/review-prompt prompt-architect.md` substitutes
  "prompt-architect.md" wherever $ARGUMENTS appears.

  STEP ORDER MATTERS. Anthropic's own bundled reference (Step 3) is consulted
  BEFORE web search (Step 4), because it is a better source: purpose-built,
  versioned with the tooling, and it carries a keep list that stops the audit
  from turning into a length contest. Search fills gaps; it does not lead.
-->

# Task

Re-validate the prompt file `$ARGUMENTS` against current published prompting
guidance, and propose changes for individual approval.

The file is in `prompts/`. If `$ARGUMENTS` is empty, list the files in `prompts/`
and ask which one — unless there is exactly one, in which case name it and ask for
a yes. If it names a file that doesn't exist, say so and list what does — do not
guess at a near match.

## Step 1 — Read the header

Read `prompts/$ARGUMENTS` and pull `last_validated`, `validated_against`, and
`recommended_effort` from the YAML frontmatter at the top.

<!--
  Parsing note: this file uses --- as a horizontal rule in its prose, several
  times. Frontmatter is ONLY the block bounded by --- on line 1 and the next ---
  after it. Do not treat later --- lines as delimiters, and never truncate the
  prompt body at one.
-->

If there is no frontmatter, say so and stop. Offer to add a baseline header, but do
not review a file with no established baseline — there'd be no date to search from.

Report the values before continuing, so the search window is visible and correctable.

## Step 2 — Establish what research you can actually do

Check each of these and **report what you found before going further.** A review is
only as good as its sources, and the reader needs to know which ones were available.

1. **`WebSearch`** — attempt one search.
2. **`WebFetch`** — attempt one fetch against a docs URL. This is checked separately
   because it can be blocked (egress proxy, sandbox) while search still works. When
   fetch is blocked you get search summaries instead of full pages: usable, but say
   so plainly rather than letting the review look better-sourced than it is.
3. **Models API** — if an API key exists, confirm `validated_against` is still a
   current model. This turns "is this model current?" from inference into fact:

   ```
   curl -s https://api.anthropic.com/v1/models \
     -H "x-api-key: $ANTHROPIC_API_KEY" \
     -H "anthropic-version: 2023-06-01"
   ```

   No key (401, or `ANTHROPIC_API_KEY` unset) → say so and continue. This step is a
   bonus, not a gate. But if the key IS present and `validated_against` is absent
   from the list, that is a headline finding: the prompt is baselined against a
   retired model.

**Stop only if Step 3 and every research path here are unavailable.** If Step 3
works, the review can proceed on the bundled reference alone — say that's what
happened. Never fall back on recalled knowledge and present it as a sourced review.

## Step 3 — Consult the bundled Anthropic reference first

Invoke the `claude-api` skill and read its `shared/prompt-audit.md`.

This is Anthropic's own checklist for exactly this job — finding instructions written
for older models. Work through its anti-pattern groups against the prompt file:
pressure language, scaffolds replaced by API features, over-specification, and
fossils (text that outlived its model).

**Read its keep list too, and honor it.** The audit's job is to find *specific dated
instructions*, not to make the prompt shorter. Context the author knows and the model
doesn't — audience, quality bar, the reasons behind constraints — is never cruft. A
naive shortening pass deletes exactly the highest-value words.

Also check `shared/model-migration.md` for behavioral shifts in the target model that
the prompt should account for.

## Step 4 — Search for anything the reference didn't cover

Find guidance published **since `last_validated`** that would affect this prompt.

**Floor the window at one model generation back**, even when `last_validated` is
recent. A prompt validated last week against a model that shipped six months ago still
has six months of guidance to check, and a literal "since last Tuesday" window returns
nothing while looking like a clean bill of health.

Search in this order, and weight them in this order:

1. **Official vendor documentation** — restrict with
   `allowed_domains: ["docs.anthropic.com", "anthropic.com"]`. Model cards, prompting
   guides, release notes, migration notes.
2. **Official guidance for whichever model the prompt now targets**, if that differs
   from `validated_against`.
3. **Everything else** — only to corroborate something from 1 or 2, never as the sole
   basis for a proposed change.

Ignore undated posts. If the search adds nothing beyond Step 3, say so — that is a
useful result, not a failed step.

If nothing substantive turns up anywhere, say that. "No changes needed" is a valid
outcome; bump `last_validated` and log it. Do not manufacture changes to justify the run.

## Step 5 — Propose a diff, do not rewrite

Present each proposed change **separately and numbered**, in this shape:

> **N. <short label>**
> **Current:** <the exact existing text>
> **Proposed:** <the replacement>
> **Why:** <what specifically changed in the guidance, with the source>
> **Confidence:** high / medium / low

Rules:
- One concern per numbered item, so each can be accepted or rejected on its own.
- Quote real text from the file. Never paraphrase what's currently there.
- Every item cites a source. An item you can't source is an opinion — drop it or
  label it clearly as your own judgment, not as guidance.
- **Say what you considered and did not flag.** A visible brake is how the reader
  knows the audit had one.
- Do not output a rewritten file. The whole point is approving changes individually.

Then **stop and wait.** Do not edit anything yet.

## Step 6 — Apply what's approved, and record the decisions

Only after explicit approval, and only the approved items:

1. Apply the approved edits to `prompts/$ARGUMENTS`.
2. Update the header: set `last_validated` to today's date and `validated_against`
   to the model reviewed against. Set `status: current`. If the approved edits
   changed what the prompt *does*, update `description` to match — it's the line
   that shows up in the README's index table. Don't touch it for wording-level
   edits. The README itself regenerates on push; you don't need to edit it here.
3. Append an entry to `CHANGELOG.md` under that prompt's section, newest first:

   ```
   ### YYYY-MM-DD — <short label>
   <What changed.>
   <Why — the guidance that drove it, so this isn't relitigated later.>
   ```

   Short, but never at the cost of the reasoning. The "why" is the part worth
   writing; it's what git history won't give back.

4. Note rejected items in the CHANGELOG entry too — a rejected change that gets
   re-proposed every six months is its own kind of waste.

5. **Append one line to the run log** at `~/prompt-library-notes/runs.jsonl`
   (`mkdir -p` the directory first; it lives outside the repo on purpose). Schema
   and rationale: `docs/run-log-schema.md`. Accept/reject decisions are the highest-
   value signal this workflow produces — they are a graded record of which advice was
   actually good. Do not skip this step because the review was small.

Do not commit. Leave the changes in the working tree for review.
