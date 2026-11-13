#!/usr/bin/env python3
"""
Render data/podcast-platform-specs.yml into the places that need it.

WHY THIS EXISTS
    Platform limits change far more often than the instructions for writing to
    them. When the limits lived inline in the prompt, every correction meant
    editing the prompt itself — and a stale number was indistinguishable from a
    current one. This script splits the two apart:

        data/podcast-platform-specs.yml   <- the only place a limit is written
                 |
                 +--> prompts/podcast-distribution-copywriter.md
                 |        (spliced between the PLATFORM SPECS markers, so the
                 |         prompt stays self-contained when pasted into a
                 |         Claude project's custom instructions)
                 |
                 +--> docs/podcast-platform-specs.md
                          (a standalone reference, for uploading to a Claude
                           project's knowledge or reading on GitHub)

    It is the same "canonical source -> generated copies -> CI drift check"
    pattern as scripts/generate_prompt_index.py and scripts/sync-base-prompt.sh.
    Anything you have to remember to update by hand goes stale.

USAGE
    python3 scripts/render_platform_specs.py           # rewrite both outputs
    python3 scripts/render_platform_specs.py --check   # write nothing; exit 1 on drift

EXIT CODES
    0  outputs current (or written)
    1  drift found (--check only)
    2  the data file is invalid, a marker is missing, or bad usage

DEPENDENCIES
    None. Standard library only, like every script in this repo, so it runs on a
    bare CI runner and on macOS's system python3 (3.9) with no pip install.
    That is why the YAML parser below is hand-rolled and deliberately narrow:
    the data file uses a small, documented subset of YAML (a flat list of flat
    records), and the parser rejects anything outside that subset loudly rather
    than guessing. The file is still valid YAML, so switching to PyYAML later
    changes nothing about the data.

DETERMINISM
    The output depends only on the data file — never on today's date. That
    matters: if the render included something like "12 days old", the CI drift
    check would start failing on its own as time passed, with no one having
    changed anything. Staleness is judged at *read* time instead: the prompt
    tells the model to compare each row's check date with the current date.
"""

import re
import sys
from pathlib import Path

# --- Configuration -----------------------------------------------------------
# Resolve paths from the repo root (this script's parent's parent), so the
# script works no matter which directory you run it from.
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "podcast-platform-specs.yml"
PROMPT_FILE = REPO_ROOT / "prompts" / "podcast-distribution-copywriter.md"
DOC_FILE = REPO_ROOT / "docs" / "podcast-platform-specs.md"

BEGIN_MARKER = "<!-- BEGIN PLATFORM SPECS -->"
END_MARKER = "<!-- END PLATFORM SPECS -->"

# Groups render in this order, each as its own table. A dict preserves insertion
# order (Python 3.7+), so this also fixes the output order.
GROUPS = {
    "directories": "Podcast directories and apps",
    "rss": "RSS feed",
    "hosts": "Hosting platforms",
    "social": "Social platforms",
    "web": "Web and CMS",
}

# The allowed status values, and the one-line meaning rendered into the legend.
# The legend is generated from this dict rather than written into the prompt by
# hand, so adding a status here can't leave the prompt describing the old set.
STATUSES = {
    "documented": "the platform's own docs, or the governing spec, state it",
    "secondary": "hosts, third-party testing or trade press state it; the platform is silent",
    "convention": "copywriting or SEO practice with no platform authority",
    "unverified": "no reliable source found; never present it as fact",
}

REQUIRED = ("id", "group", "platform", "field", "value", "status", "verified")
OPTIONAL = ("source", "note")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# --- Parsing -----------------------------------------------------------------

class DataError(Exception):
    """A problem with the data file. Always carries the line number."""


def parse_scalar(raw, lineno):
    """
    Turn the text after "key: " into a value.

    Two forms are accepted:
      - bare text:       4,000 characters
      - double-quoted:   "description, media:description — not itunes:summary"

    Quoting is required only when the value contains ": " (colon-space), which is
    the one thing that would make a real YAML parser read it differently. Single
    quotes are rejected rather than half-supported: one quoting style is easier
    to get right by hand than two.
    """
    raw = raw.strip()
    if raw.startswith('"'):
        if len(raw) < 2 or not raw.endswith('"'):
            raise DataError(f"line {lineno}: unterminated double quote")
        inner = raw[1:-1]
        # Supporting \" and \\ covers every escape a copywriter would plausibly need.
        return inner.replace('\\"', '"').replace("\\\\", "\\")
    if raw.startswith("'"):
        raise DataError(f"line {lineno}: use double quotes, not single quotes")
    if ": " in raw:
        raise DataError(f"line {lineno}: value contains ': ' — wrap it in double quotes")
    return raw


def parse_records(text):
    """
    Parse the data file's YAML subset into a list of dicts.

    The grammar, in full:
        blank lines and whole-line # comments are ignored
        "- key: value"   starts a new record
        "  key: value"   (exactly two spaces) adds a field to the current record

    Each record remembers the line it started on, so validation errors can point
    at the exact place to fix.
    """
    records = []
    current = None

    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        if line.startswith("- "):
            current = {"_line": lineno}
            records.append(current)
            body = line[2:]
        elif line.startswith("  ") and not line.startswith("   "):
            if current is None:
                raise DataError(f"line {lineno}: field appears before any '- id:' record")
            body = line[2:]
        else:
            raise DataError(
                f"line {lineno}: expected '- key: value' or '  key: value' "
                f"(two-space indent). Got: {line!r}"
            )

        key, sep, raw = body.partition(":")
        key = key.strip()
        if not sep or not key or (raw and not raw.startswith(" ")):
            raise DataError(f"line {lineno}: expected 'key: value'. Got: {line!r}")
        if key in current:
            raise DataError(f"line {lineno}: duplicate key '{key}' in one record")
        current[key] = parse_scalar(raw, lineno)

    return records


def validate(records):
    """
    Check every record against the schema documented at the top of the data file.

    Collects every problem before failing, so one run tells you everything that
    needs fixing instead of making you fix-and-rerun one error at a time.
    """
    problems = []
    seen_ids = {}

    for r in records:
        where = f"record at line {r['_line']}"
        rid = r.get("id")
        if rid:
            where = f"'{rid}' (line {r['_line']})"
            if rid in seen_ids:
                problems.append(f"{where}: duplicate id, first used at line {seen_ids[rid]}")
            seen_ids.setdefault(rid, r["_line"])

        for key in REQUIRED:
            if not r.get(key):
                problems.append(f"{where}: missing required field '{key}'")
        for key in r:
            if key != "_line" and key not in REQUIRED + OPTIONAL:
                problems.append(f"{where}: unknown field '{key}'")

        if r.get("group") and r["group"] not in GROUPS:
            problems.append(f"{where}: group '{r['group']}' is not one of {', '.join(GROUPS)}")
        if r.get("status") and r["status"] not in STATUSES:
            problems.append(f"{where}: status '{r['status']}' is not one of {', '.join(STATUSES)}")
        if r.get("verified") and not DATE.match(r["verified"]):
            problems.append(f"{where}: verified must be YYYY-MM-DD, got '{r['verified']}'")
        # A fact with no source can't be re-checked, so only a convention may omit one.
        if r.get("status") in ("documented", "secondary") and not r.get("source"):
            problems.append(f"{where}: status '{r['status']}' requires a source URL")
        if r.get("source") and not r["source"].startswith("https://"):
            problems.append(f"{where}: source must be an https:// URL")

    if problems:
        raise DataError("invalid data file:\n  " + "\n  ".join(problems))


# --- Rendering ---------------------------------------------------------------

def cell(text):
    """Make text safe for one markdown table cell: one line, pipes escaped."""
    return re.sub(r"\s+", " ", text or "").replace("|", r"\|").strip()


def render_block(records):
    """
    Build the markdown that goes between the markers — and, verbatim, into the
    reference doc. One renderer for both outputs, so the prompt and the doc can
    never disagree with each other.
    """
    checked = sorted(r["verified"] for r in records)
    out = [
        BEGIN_MARKER,
        "<!-- Generated by scripts/render_platform_specs.py from "
        "data/podcast-platform-specs.yml. Do not edit by hand. -->",
        "",
        f"Specs last checked between {checked[0]} and {checked[-1]}. "
        "The **Basis** column says how far to trust each row:",
        "",
    ]
    out += [f"- **{name}** — {meaning}" for name, meaning in STATUSES.items()]

    for group, title in GROUPS.items():
        rows = [r for r in records if r["group"] == group]
        if not rows:
            continue
        out += [
            "",
            f"#### {title}",
            "",
            "| Platform | Field | Value | Basis | Checked | Note |",
            "|---|---|---|---|---|---|",
        ]
        for r in rows:
            # Link the basis to its source, so every claim is one click from
            # its evidence. A convention with no source renders unlinked.
            basis = f"[{r['status']}]({r['source']})" if r.get("source") else r["status"]
            out.append(
                f"| {cell(r['platform'])} | {cell(r['field'])} | {cell(r['value'])} "
                f"| {basis} | {r['verified']} | {cell(r.get('note'))} |"
            )

    out += ["", END_MARKER]
    return "\n".join(out)


def render_doc(block):
    """The standalone reference: a short header, then the same block."""
    return "\n".join([
        "<!-- GENERATED FILE — DO NOT EDIT.",
        "     Rendered by scripts/render_platform_specs.py from data/podcast-platform-specs.yml.",
        "     Edit the data file, then re-run the script. -->",
        "",
        "# Podcast platform specs",
        "",
        "Character limits and display behavior for podcast directories, hosts, social",
        "platforms and the web. This is the reference behind",
        "[prompts/podcast-distribution-copywriter.md](../prompts/podcast-distribution-copywriter.md).",
        "Upload it to a Claude project's knowledge so the copywriter can cite it.",
        "",
        "To change a value, edit",
        "[data/podcast-platform-specs.yml](../data/podcast-platform-specs.yml) and run",
        "`python3 scripts/render_platform_specs.py`.",
        "",
        block,
        "",
    ])


def splice(text, block, path):
    """Replace the marked region of `text` with `block`. Fail loudly if absent."""
    pattern = re.compile(re.escape(BEGIN_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL)
    if not pattern.search(text):
        raise DataError(
            f"{path.relative_to(REPO_ROOT)} has no PLATFORM SPECS markers. Add:\n"
            f"  {BEGIN_MARKER}\n  {END_MARKER}"
        )
    # A lambda replacement stops re.sub from reading backslashes in the block
    # as group references — a classic source of silently mangled output.
    return pattern.sub(lambda _: block, text, count=1)


# --- Entry point -------------------------------------------------------------

def main(argv):
    if argv not in ([], ["--check"]):
        print("usage: render_platform_specs.py [--check]", file=sys.stderr)
        return 2
    check_only = argv == ["--check"]

    try:
        records = parse_records(DATA_FILE.read_text(encoding="utf-8"))
        if not records:
            raise DataError("the data file contains no records")
        validate(records)
        block = render_block(records)
        wanted = {
            PROMPT_FILE: splice(PROMPT_FILE.read_text(encoding="utf-8"), block, PROMPT_FILE),
            DOC_FILE: render_doc(block),
        }
    except (DataError, FileNotFoundError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 2

    drifted = [p for p, text in wanted.items()
               if not p.exists() or p.read_text(encoding="utf-8") != text]

    if not drifted:
        print(f"Platform specs are current ({len(records)} records).")
        return 0

    names = ", ".join(str(p.relative_to(REPO_ROOT)) for p in drifted)
    if check_only:
        print(f"DRIFT: {names} out of date with data/podcast-platform-specs.yml.\n"
              "Fix:   python3 scripts/render_platform_specs.py, then commit the result.",
              file=sys.stderr)
        return 1

    for path in drifted:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(wanted[path], encoding="utf-8")
    print(f"Rendered {len(records)} records into: {names}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
