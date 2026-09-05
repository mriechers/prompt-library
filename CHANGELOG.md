# Changelog

Dated entries per prompt, newest first. Each entry records **what changed and why** —
the "why" is the part `git log` won't give you back in six months.

Keep entries short — but never at the cost of the reasoning.

---

## prompts/prompt-architect.md

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
