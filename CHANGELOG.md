# Changelog

Dated entries, newest first, grouped by what they changed — the repository itself,
then one section per prompt. Each entry records **what changed and why** —
the "why" is the part `git log` won't give you back in six months.

Keep entries short — but never at the cost of the reasoning.

---

## Repository

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
