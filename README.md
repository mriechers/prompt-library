# prompt-library

Stashed prompts for Claude projects in the chat app.

## prompt-architect.md

The base prompt for turning rough prompts into precise ones. **This root file is canonical** —
paste it into a Claude Project, and edit it here as models change.

The `expand-prompt` skill (`.claude/skills/expand-prompt/`) consumes it. A skill gets installed as
a self-contained directory, so it can't read a file outside its own folder; it carries a synced
copy at `.claude/skills/expand-prompt/references/prompt-architect.md` instead.

**After editing `prompt-architect.md`, re-run the sync:**

```bash
scripts/sync-base-prompt.sh
```

CI runs `scripts/sync-base-prompt.sh --check` on every push, so a forgotten sync fails the build
rather than shipping a stale skill.

## The expand-prompt skill

`.claude/skills/expand-prompt/` turns a rough prompt into a precise one and saves it as
`planning/expanded-prompt-<title>.md` in whatever directory you run it from.

It also files a copy in the Obsidian inbox, but only when it can reach the vault through the
[Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) plugin — it probes
first and skips the step with a one-line reason when Obsidian isn't running, which is the normal
case in a cloud session. The planning copy is always written either way. No vault filesystem path
appears anywhere in the skill.

The API key comes from `OBSIDIAN_LOCAL_REST_API_KEY` in the environment, or from the machine-ops
secrets rail (`get-secret.sh`) when it isn't.
