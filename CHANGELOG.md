# Changelog

Dated entries, newest first, grouped by what they changed — the repository itself,
then one section per prompt. Each entry records **what changed and why** —
the "why" is the part `git log` won't give you back in six months.

Keep entries short — but never at the cost of the reasoning.

---

## Repository

### 2026-09-20 — Platform specs as data; Cowork's place in the git workflow
Added `data/podcast-platform-specs.yml`, `scripts/render_platform_specs.py`, and
`.github/workflows/platform-specs.yml`. The copywriter prompt's limits now come from one
data file, rendered into the prompt's marked region and into `docs/podcast-platform-specs.md`.
It's the same canonical-source, generated-copy, CI-check pattern as the index and the skill sync.

Why data rather than prose: a fact-check of the original prompt found its most important
number (Spotify, 500 characters) off by two orders of magnitude, and every "visible
preview" figure unsourced. Nothing in the prompt showed which numbers were solid and
which were folklore. Every record now carries a status, a source and a check date, so the
model can say how much to trust a limit, and a correction is a one-line data edit
instead of a prompt rewrite.

The renderer is standard-library only. It parses a documented subset of YAML and rejects
anything outside it, which keeps the zero-dependency rule. Its output never depends on
today's date, so the drift check can't start failing just because time passed.

The README also gained a "Working from Cowork and Claude Code" section. The first Cowork
session to work here found that git can't run in the connected folder: the Cowork shell
can't delete `.git/index.lock` and has no SSH key. That session left behind a stale lock
file. The documented workflow is now for Cowork to commit in its own clone of `main` and
hand over a patch, and for you to push.

### 2026-09-16 — expand-prompt skill: portable when invoked from another repo
The skill addressed its own helper scripts as `.claude/skills/expand-prompt/scripts/…`, a path
relative to the *working directory*. That is only true inside this repo; invoked from any
other checkout (its normal use) the scripts did not resolve and the vault step skipped with a
misleading reason. Every self-reference is now relative to the skill's base directory.

Same pass, same rule: `obsidian-put.sh` no longer falls back to a hardcoded path into the
machine-ops clone to find `get-secret.sh`. It resolves the rail by name on `PATH` (or a
`GET_SECRET` override) and skips cleanly when absent — a dependency on an interface, not on
another repo's layout. Pointers to files that live in this repo but not in the skill (the
canonical prompt, the run-log schema, the sync script) became GitHub URLs, which stay true
after the skill is vendored elsewhere.

Why it matters: the previous `/expand-prompt` this one replaces rotted exactly this way — an
absolute vault path that was true on one machine and silently wrong later. A skill that
encodes where it lives cannot survive being moved, and this skill is about to be distributed
from a different repo than the one it is authored in.

### 2026-09-09 — expand-prompt skill, and its README integration
Merged `main` into the expand-prompt branch and resolved the README conflict by
integrating the skill into the rewritten README rather than appending to it — the repo
now holds prompts *and* two tools that read them, so the structure names both.

Three fixes the merge surfaced, none of which the branch could have known about:
the skill shipped a copy of `prompt-architect.md` synced before PR #1, so it carried
exactly the guidance PR #1 removed ("reasoning models", the closing-recap advice) and
lacked what PR #1 added — re-ran the sync; `SKILL.md` still named the repo root as the
canonical location, which would send an editor to create a competing file — corrected
to `prompts/`; and `docs/run-log-schema.md` documented only review records while
`log-run.sh` was already writing a second shape into the same file — added a `kind`
discriminator and an expansion-record section.

Also made the sync banner name the source file it actually read, instead of stating a
path resolved before the lookup happens.

Why the stale-copy fix matters most: the skill's own CI caught it, which is the design
working. But had it merged, the skill would have operated on the outdated prompt while
the repo's index reported the prompt as `current` — the precise drift both PRs exist to
prevent.

### 2026-09-05 — README rewrite and generated prompt index
Rewrote the README to lead with what the repo is for (prompts that tell you whether
they're still good) instead of opening on file conventions. Added a generated index of
the prompts, built by `scripts/generate_prompt_index.py` and kept current by
`.github/workflows/prompt-index.yml` — the workflow fails a pull request whose README
doesn't match `prompts/`, and regenerates the table after a push to `main`.
Why generated rather than hand-written: a list you have to remember to update goes
stale, which is the exact failure the `last_validated` headers exist to prevent. Having
the README go stale while the headers stayed current would be an embarrassing way to
lose the argument.

---

## prompts/podcast-distribution-copywriter.md

### 2026-09-20 — Added, fact-checked, with an audit mode
New prompt, reworked from an existing podcast-copy prompt. Its platform table was
checked claim by claim against primary sources, and these corrections landed in the data file:

- **Spotify's 500-character description limit is not current.** The May 2025 delivery spec
  exempts descriptions from its length rules, and provider support cites 60,000. The prompt's
  advice to set up a "Spotify-specific shorter description" rested on that number and was
  removed. No such Spotify field exists; Libsyn's per-destination override is host-side.
- **LinkedIn About is 2,600, not 2,000.** The X Premium post limit is 25,000 on web but 4,000
  on mobile. Facebook's 255 is the Page About field; a personal bio is 101.
- **Every per-platform "visible preview" number was dropped.** None is documented, and the
  only measurements (one iPhone, 2020) contradicted the prompt. The prompt now teaches the
  behavior: the opening has to stand alone, because nobody documents where the cut falls.
- **YouTube is the exception to "RSS wins."** A Studio edit blocks all future RSS updates to
  that episode.
- **RSS descriptions are 4,000 bytes, not characters** (PSP-1), so typographic punctuation costs extra.
- **Amazon Music's 4,000 has no public source.** It's now marked `unverified`, and the
  tagline range of 100-255 became Dovetail's documented 150.

Prompt changes: every limit now has to come from the table, cited with its basis and check
date, and a row older than 12 months gets flagged. Counting has to be done with code, or
labeled approximate, in each platform's own unit. The biggest addition is **Audit mode**
(`/audit`), which reviews a show's live copy: inventory, measure, test the opening, check
known traps, compare across platforms, rank findings as Breaks, Weakens or Polish, and
propose rewrites. Real trade-offs are offered as options rather than decided. The RSS feed
is the preferred input, and YouTube copy is audited separately.

Why an audit mode: the fact-check changed the rules under copy that's already live, and a
show is more likely to need its existing descriptions checked than new ones written.

## prompts/prompt-architect.md

### 2026-09-05 — Added a `description` header field
Added a one-line `description` to the frontmatter, used to build the README's prompt
index. Why in the header rather than inferred from the body: the generator can fall back
to the first paragraph, but that paragraph is written for a reader who is already inside
the file — the index needs a line written for someone who isn't. No change to the prompt
text.

### 2026-09-05 — Re-validated against Claude Opus 5
Fixed stale model categories ("reasoning" vs "non-reasoning" — that split collapsed once
adaptive thinking became the default), cut the closing-recap advice, added a principle
against carrying anti-laziness prompting forward, and added a `recommended_effort` header.
Why: the prompt body stays model-agnostic, since these go to whichever model is selected
per-request — so model/effort recommendations are emitted as a note for the project
description rather than baked into the instructions. All four changes accepted.

### 2026-09-05 — Versioning baseline
Added a `last_validated` / `validated_against` header and moved the file into `prompts/`.
No changes to the prompt text itself. This is a declared baseline, not a re-test —
it records the model the prompt is believed current for, so future reviews have a starting date.
