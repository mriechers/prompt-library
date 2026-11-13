# Changelog

Dated entries, newest first, grouped by what they changed — the repository itself,
then one section per prompt. Each entry records **what changed and why** —
the "why" is the part `git log` won't give you back in six months.

Keep entries short — but never at the cost of the reasoning.

---

## Repository

### 2026-09-20 — sync-base-prompt.sh: portable on BSD awk, and no longer truncates on failure
`--check` failed on any Mac. The generated-file banner is three lines, and it reached awk as
`-v banner="$BANNER"`. A `-v` assignment may not contain a literal newline: BSD awk — the awk
macOS ships — rejects it with "newline in string" and exits having printed nothing. `render`
therefore produced an empty file, the diff showed the whole committed copy as deleted, and the
script reported DRIFT that did not exist. gawk accepts the same assignment, so CI stayed green
and the failure only ever appeared off-CI. The banner now crosses into awk through the
environment and is read once in `BEGIN` via `ENVIRON`, which is POSIX and behaves the same in
both awks.

The second half is the one with teeth. Write mode was `render > "$DEST"`, and the script runs
under `set -uo pipefail` with no `-e`. The shell truncates `$DEST` when it opens the redirect,
*before* the renderer runs — so a renderer that died left an empty tracked file behind, and
execution continued to print `synced:` and exit 0. Silent data loss reported as success, and
`--check`'s own failure message told you to run exactly that command. Rendering now goes to a
temp file that is moved into place only on success; a non-zero renderer exits 2 and says the
destination was left untouched.

Why it matters: a guard that cannot run on the maintainer's own machine gets read as noise and
worked around, and the documented way to work around this one destroyed the file the guard
exists to protect. Verified both ways on macOS — `--check` now exits 0 against stock BSD awk,
and with a deliberately failing awk the destination survives at full length instead of going
to zero bytes.

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

## prompts/treedix-cable-tester.md

### 2026-09-16 — Re-validated against Claude Sonnet 5, plus a live test
Header now records Claude Sonnet 5 and `recommended_effort: high`. Why: Anthropic
says Sonnet 5 respects effort strictly and can under-think at low/medium on
moderately complex tasks, and says to raise effort rather than prompt around it.

From the Sonnet 5 guidance (it follows instructions literally and does not
generalize a rule from one case to another):
- Added a general "expected dark LEDs are not faults" rule. The prompt previously
  said this for five specific cases, so an unlisted one (dark TX1±/RX1±/SBU on a
  USB 3.x cable) could have been reported as a problem.
- Made step 5 agree with the output format: ask the closing question only when it
  would change the verdict. The two sections previously disagreed.

From a test run on a real photo (Sonnet, same prompt, no hints): the verdict,
Power In handling and format were right, but the model merged each pinrow pair
into one table line, reported Pinrow A's D+/D− as lit when they were dark, and
concluded from the resulting "symmetry" that one end was Type-C. Fixes:
- Every LED gets its own line; never merge two LEDs into one.
- The one-pinrow D+/D− pattern now also lists the Type-C single-pair explanation,
  not just the non-Type-C one.

All five changes accepted.

### 2026-09-15 — Hardcoded to this board's wiring
The board has no model number, so the prompt now identifies it by its printed
name ("Usb Cable Checker"), acrylic case, and power options. Replaced the claim
that every non-Type-C connector routes to Pinrow B with the actual wiring from
the back-of-board silkscreen. Lightning's data lines also reach A6/A7, so a
Lightning reading can light Pinrow A without being a fault. Corrected the ID LED:
it's wired only to Micro-B/Mini-B pin 4, and Lightning's ACC1/ACC2 go to separate
pads. Extended "these instructions win" over the manual to cover port labels,
and dropped the silkscreen diagram from the reasons to open the manual.
Why: Treedix's current manual (EN-TRX5-0865-A) is for a board version with
different port letters, so the prompt can't defer to it for this board. The
silkscreen on the board itself is the only authoritative wiring source. All
three changes accepted.

### 2026-09-15 — Reviewed against Claude Opus 5
Fixed three factual errors in the cable-type inference rules, plus three clarity
issues. Accepted:
- **SuperSpeed LEDs don't prove a Type-C end.** A-3.0-to-Micro-B-3.0 and Type-B 3.0
  cables carry TX/RX too. Only CC and SBU are unique to Type-C.
- **CC rules corrected.** A C-to-C cable carries a single CC wire, so one lit CC is
  normal. The manufacturer's own USB 3.x row shows CC2 alone. Non-C connectors have
  no CC pin, so C-to-A cables leave both CC LEDs dark. The old rule would have read
  a normal C-to-C 3.x cable as C-to-A.
- **Worked example fixed.** 3A isn't a default; it's advertised over CC, and a
  Type-C charger won't turn on VBUS until it detects a device on CC. Examples get
  copied by the model, so a wrong fact there spreads into answers.
- **Circuit description decoupled from pinrow names.** Pinrow A/B are the two rows
  of a USB-C connector, not the two cable ends; both rows have LEDs.
- **ID LED:** a dark ID on Type-A/Type-C cables is expected.
- **E-marker caveat:** separated from the manufacturer's warning, which doesn't
  name e-markers. Clarified wording used instead of the proposed "likely count".

Earlier proposals to read ports from the photo and not block on the cable label
were covered by the author's own rewrite (the "When you can't tell which ports are
in use" section).

Rejected: a generic "if the board is labeled differently" check, and extending
the manual-precedence rule to port labels. The author will hardcode the specific
board model instead. Why it came up: Treedix's current manual (EN-TRX5-0865-A)
uses different port letters than this board.

### 2026-09-15 — Added to the library
Claude.ai project instructions for reading a photo of a Treedix USB Cable Tester
Board. Header is a declared baseline, not a re-test.

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
