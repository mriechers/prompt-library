# prompt-library

Stashed prompts for Claude projects in the chat app.

## Convention

Prompts live in `prompts/`. Each one starts with a header recording when it was last
checked and against which model:

```yaml
---
last_validated: 2026-09-05
validated_against: Claude Opus 5
status: current
---
```

`status` is `current` or `stale`. Mark a prompt `stale` when a new model ships and you
haven't re-checked it yet — the point is that opening the file tells you where it stands,
instead of you having to remember.

`CHANGELOG.md` logs what changed in each prompt and why.

## Re-checking a prompt

Run `/review-prompt <filename>` in Claude Code from this repo. It reads the header,
searches for prompting guidance published since that date, and proposes changes for you
to approve one at a time. On approval it applies the edits, bumps the header, and appends
a CHANGELOG entry.
