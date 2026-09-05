# prompt-library
Stashed prompts for Claude projects in the chat app.

## The expand-prompt skill

`.claude/skills/expand-prompt/` turns a rough prompt into a precise one. It does not
carry its own prompt-engineering guidance — it reads `prompt-architect.md` and applies
it, so revising that file is what changes how the skill behaves.

A skill is installed as a self-contained directory and cannot read a file outside its
own folder, so it carries a synced copy at
`.claude/skills/expand-prompt/references/prompt-architect.md`. **After editing the
canonical prompt, re-run the sync:**

```bash
scripts/sync-base-prompt.sh
```

CI runs `scripts/sync-base-prompt.sh --check` on every push, so a forgotten sync fails
the build rather than shipping a stale skill.

Output goes to `planning/expanded-prompt-<title>.md` in whatever directory you run it
from. It also files a copy in the Obsidian inbox, but only when it can reach the vault
through the [Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api)
plugin — it probes first and skips with a one-line reason when Obsidian isn't running,
which is the normal case in a cloud session. No vault filesystem path appears anywhere
in the skill. The API key comes from `OBSIDIAN_LOCAL_REST_API_KEY`, or from the
machine-ops secrets rail when that isn't set.

Each run also appends one line to `~/prompt-library-notes/runs.jsonl` — the mode used,
how many revision rounds it took, and which version of the base prompt was in force.
That last field is the point: it ties outcomes to a specific `last_validated` date, so
`/review-prompt` has evidence to act on rather than impressions. Modes and counts only;
the script takes no free-text parameter, so no prompt content can reach the log.
