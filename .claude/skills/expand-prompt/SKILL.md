---
name: expand-prompt
description: >
  Use when turning a rough prompt, half-formed idea, or task description into a precise,
  structured prompt meant to be run in a different session — expanding it, interrogating it,
  critiquing it, or tightening it — then saving it with a launch one-liner, and to the Obsidian
  inbox when that vault is reachable. Triggers on "expand prompt", "expand this prompt",
  "improve this prompt", "prompt engineering", "/grillme", "/audit", "/tighten". NOT for
  executing the prompt it produces.
---

# expand-prompt

This skill owns the **workflow**: load the base prompt, present the result for review, save it
somewhere you can launch it from.

It does not own the **craft**. How to expand, interrogate, critique, or tighten a prompt lives
entirely in `references/prompt-architect.md` — a synced copy of `prompt-architect.md` at the root
of this repo. That root file is the one you paste into a Claude Project and the one you revise as
models change. Revising it changes how this skill behaves; nothing in this file needs a second
edit.

## 1. Load the base prompt — first, always

Read `references/prompt-architect.md` (sitting next to this file) and adopt it as your operating
instructions for the expansion.

**If it is missing or unreadable, stop and say so.** Do not fall back on general prompt-engineering
knowledge. A remembered approximation of the base prompt is exactly the drift this skill was
rebuilt to eliminate — and it fails silently, which is worse than not running.

## 2. Local overrides

Everything the base prompt says applies here unchanged, except this:

> The base prompt tells you that when the input reads like a task rather than a prompt, you should
> return a prompt for doing it and then **"offer once at the end to run it."**
>
> **Here, never offer to run it.** The expanded prompt is destined for a *fresh* session with its
> own working directory, permissions, and context. Running it in this one would execute it under
> the wrong ones — and this session is already loaded with prompt-writing context that would skew
> the result.

This is stated as an explicit override rather than a quiet contradiction so the two instructions
are not read as a coin-flip.

## 3. Modes

The base prompt defines the modes — Default, `/grillme`, `/audit`, `/tighten` — and this file does
not restate what they do. A mode word appearing in the input selects that mode; otherwise Default.

**Resolving the input:** the text following the invocation is the prompt to work on. Invoked as a
slash command, that text arrives as `$ARGUMENTS`; triggered from conversation, it is simply what
was said. Treat both the same way.

**With no input at all,** ask what they want to expand, plus one or two questions about the target
context — which model or tool will consume it, and whether it is single-use or a reusable template.
Then continue on the Default path.

## 4. Present for review

Show the expanded prompt. Revise on request, as many rounds as they want.

**Nothing is written anywhere before approval.**

## 5. Save — the planning copy always, the vault note only if it is reachable

### a. The planning copy (always)

Write `planning/expanded-prompt-<kebab-case-title>.md`, relative to the current working directory
(create `planning/` if it does not exist):

````markdown
# <short descriptive title>

## Launch

Run this from this directory to start a plan-mode session:

```bash
claude --model opus "Enter plan mode for this task, dispatching research agents in Phase 1:

$(cat planning/expanded-prompt-<kebab-case-title>.md)"
```

## Original

> <the original prompt, quoted>

## Expanded

<the full expanded prompt>
````

This file is the deliverable. It is repo-relative, so it works in every session — local, cloud, or
someone else's checkout — and it is what the launch one-liner reads. Everything below is a bonus
copy filed somewhere more findable.

### b. The Obsidian vault note (only when the vault answers)

The vault is reached through the **Obsidian Local REST API**, never through a filesystem path. Probe
it first:

```bash
.claude/skills/expand-prompt/scripts/obsidian-put.sh --probe
```

| Probe result | What to do |
|---|---|
| exit `0` | Write the note (below). |
| exit `1` | **Skip this step.** Report the one-line reason the script printed, say the planning copy is the result, and finish normally. |

**Exit 1 is not an error and never needs fixing mid-task.** It is the expected outcome in a cloud
session, on a machine where Obsidian is closed, or before the API key is on the secrets rail. Say
so in one line and move on.

To write, render the note to a temp file and PUT it:

```bash
.claude/skills/expand-prompt/scripts/obsidian-put.sh \
  "0 - INBOX/Expanded Prompt - <short descriptive title>.md" "$TMPFILE"
```

The path is **vault-relative** — `0 - INBOX/…`, not `~/Developer/…`. The script handles URL
encoding, the self-signed certificate, and resolving `OBSIDIAN_LOCAL_REST_API_KEY` from the
environment or the machine-ops secrets rail. Honor `$OBSIDIAN_INBOX` as the folder if it is set;
otherwise use `0 - INBOX`.

The note body is the planning copy from step (a) with Obsidian frontmatter on top:

```yaml
---
tags: [prompt, prompt-engineering, expanded]
date: <YYYY-MM-DD>
---
```

**Confirm the write before reporting it.** A non-zero exit from a PUT means the note is not in the
vault — say that, do not report it as saved. A prompt you believe is filed and is not is worse than
one you know never got there.

## What this skill deliberately does not do

- **Execute the expanded prompt.** See § 2.
- **Restate the base prompt's craft guidance.** Output structure, specificity, near-miss examples,
  length scaling, delimiter choice, deployment adaptation — one owner, `prompt-architect.md`.
  Copying any of it here recreates the drift.
- **Write to a hardcoded vault path.** An absolute path is true on one machine; the REST API is
  true wherever the vault is. If the API is unreachable, the answer is to skip, never to guess at
  a directory.
- **Let anyone hand-edit `references/prompt-architect.md`.** It is generated. Edit
  `prompt-architect.md` at the repo root, then run `scripts/sync-base-prompt.sh`.
