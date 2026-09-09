#!/usr/bin/env python3
"""
Generate the prompt index table in README.md from the files in prompts/.

WHY THIS EXISTS
    A hand-maintained list of prompts goes stale the first time you add a prompt
    in a hurry. This script makes the README a *view* of prompts/ rather than a
    parallel copy of it, so the two cannot disagree.

HOW IT WORKS
    1. Read every prompts/*.md file.
    2. Pull its metadata out of the YAML frontmatter at the top of the file
       (the block fenced by --- on the first line and --- again below it).
    3. Render a markdown table.
    4. Splice that table into README.md between two HTML-comment markers.

    Step 4 is the important design choice: the script does not own the whole
    README, only the region between the markers. Everything else in the README
    stays hand-written prose. This is a common pattern for generated docs — it
    keeps automation and authorship in the same file without either clobbering
    the other.

USAGE
    python3 scripts/generate_prompt_index.py            # rewrite README.md in place
    python3 scripts/generate_prompt_index.py --check    # exit 1 if README is out of date

    --check writes nothing. It is what CI runs on a pull request to prove the
    README matches prompts/ before the change lands.

DEPENDENCIES
    None. Standard library only, so it runs on a bare GitHub Actions runner and
    on your Mac's system python3 with no `pip install` step and no virtualenv.
    (That is also why the frontmatter parsing below is hand-rolled instead of
    using PyYAML — the headers are simple key/value pairs, and avoiding a
    dependency is worth more here than handling YAML's exotic corners.)
"""

import re
import sys
from pathlib import Path

# --- Configuration -----------------------------------------------------------
# Paths are resolved relative to the repo root, which is the parent of the
# directory this script lives in. That means the script works no matter which
# directory you run it from — a small thing that saves a lot of "file not found".
REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts"
README = REPO_ROOT / "README.md"

# The markers the generated block gets spliced between. These are HTML comments,
# so they are invisible in rendered markdown on GitHub but easy to find in the
# raw file.
BEGIN_MARKER = "<!-- BEGIN PROMPT INDEX -->"
END_MARKER = "<!-- END PROMPT INDEX -->"

# How long a description may run in the table before it gets trimmed. Table cells
# that wrap to three lines make the table unreadable on GitHub.
MAX_DESCRIPTION = 180


# --- Parsing -----------------------------------------------------------------

def parse_frontmatter(text):
    """
    Extract the YAML frontmatter block from a markdown file.

    Returns a (metadata_dict, body) tuple. If there is no frontmatter, returns
    an empty dict and the whole text as the body.

    The parser is deliberately narrow: it handles `key: value` lines and nothing
    else. It does NOT handle nested structures, multi-line values, or lists —
    if a prompt header ever needs those, replace this with PyYAML and accept the
    dependency. Until then, narrow and dependency-free wins.

    Note the guard on the closing delimiter: prompt files in this repo use `---`
    as a horizontal rule throughout their prose. Frontmatter is only the block
    bounded by the `---` on line 1 and the *next* `---` after it, so we stop at
    the first closing delimiter and never scan further.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    meta = {}
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            # Found the closing delimiter. Everything after it is the body.
            return meta, "\n".join(lines[i + 1:])
        if ":" in line:
            key, _, value = line.partition(":")
            # .strip('"\'') removes surrounding quotes if the value was quoted.
            meta[key.strip()] = value.strip().strip("\"'")

    # No closing delimiter found — the file opened a frontmatter block and never
    # closed it. Treat it as having no frontmatter rather than silently eating
    # the entire file as metadata.
    return {}, text


def extract_title(body, fallback):
    """
    Use the file's first H1 heading as the prompt's display name.

    Falls back to a title-cased version of the filename, so a prompt with no
    heading still gets a sensible name instead of a blank cell.
    """
    match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return fallback.replace("-", " ").replace("_", " ").title()


def extract_description(meta, body):
    """
    Get the one-line description for the table.

    Two sources, in priority order:

      1. A `description:` field in the frontmatter. This is the preferred source
         because the author controls exactly what the index says.
      2. The first prose paragraph after the H1 heading. This is the fallback so
         that a prompt without a `description` field still shows up usefully
         rather than with an empty cell.

    Preferring an explicit field but falling back to inference is a pattern worth
    remembering: it gives you precise control where you want it without making
    the metadata mandatory everywhere.
    """
    if meta.get("description"):
        return truncate(collapse(meta["description"]))

    # Walk the body looking for the first real paragraph after the H1.
    lines = body.splitlines()
    seen_heading = False
    paragraph = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("# "):
            seen_heading = True
            continue
        if not seen_heading:
            continue

        # Skip blank lines, further headings, horizontal rules, and HTML
        # comments — none of these are the description we want.
        if not stripped or stripped.startswith("#") or stripped.startswith("---") or stripped.startswith("<!--"):
            if paragraph:
                break  # We already collected a paragraph; this blank ends it.
            continue

        paragraph.append(stripped)

    if paragraph:
        return truncate(collapse(" ".join(paragraph)))
    return "_No description._"


def collapse(text):
    """
    Flatten text into a single table-safe line.

    Two things happen here:
      - All runs of whitespace (including newlines) become single spaces, because
        a markdown table cell cannot contain a line break.
      - Literal pipes are escaped, because an unescaped `|` would be read as a
        column separator and shred the table.
    """
    return re.sub(r"\s+", " ", text).replace("|", r"\|").strip()


def truncate(text, limit=MAX_DESCRIPTION):
    """
    Trim a description that would otherwise blow out the table's row height.

    Prefers to cut at a sentence boundary so the result still reads as a
    complete thought; falls back to a word boundary with an ellipsis.
    """
    if len(text) <= limit:
        return text

    window = text[:limit]
    sentence_end = max(window.rfind(". "), window.rfind("! "), window.rfind("? "))
    if sentence_end > limit // 2:
        return window[:sentence_end + 1]

    return window[:window.rfind(" ")].rstrip(",;:") + "…"


# --- Rendering ---------------------------------------------------------------

def collect_prompts():
    """Read every prompt file and return a list of dicts, sorted by title."""
    prompts = []

    # sorted() on the glob gives deterministic output. Without it, filesystem
    # ordering could vary between your Mac and the CI runner, and the script
    # would produce a spurious diff every other run.
    for path in sorted(PROMPTS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        prompts.append({
            "filename": path.name,
            "path": f"{PROMPTS_DIR.name}/{path.name}",
            "title": extract_title(body, path.stem),
            "description": extract_description(meta, body),
            "status": meta.get("status", "unknown"),
            "last_validated": meta.get("last_validated", "—"),
            "validated_against": meta.get("validated_against", "—"),
        })

    return sorted(prompts, key=lambda p: p["title"].lower())


def render_index(prompts):
    """Build the markdown block that goes between the two markers."""
    lines = [
        BEGIN_MARKER,
        "<!-- Generated by scripts/generate_prompt_index.py — do not edit by hand. -->",
        "",
    ]

    if not prompts:
        lines += ["_No prompts yet._", "", END_MARKER]
        return "\n".join(lines)

    lines += [
        "| Prompt | What it does | Status | Last validated | Against |",
        "|---|---|---|---|---|",
    ]

    for p in prompts:
        # A `stale` prompt gets bolded so the eye lands on it when scanning the
        # table. That is the whole point of carrying status into the index.
        status = f"**{p['status']}**" if p["status"] == "stale" else p["status"]
        lines.append(
            f"| [{p['title']}]({p['path']}) | {p['description']} "
            f"| {status} | {p['last_validated']} | {p['validated_against']} |"
        )

    lines += ["", END_MARKER]
    return "\n".join(lines)


def splice(readme_text, block):
    """
    Replace the region between the markers with the freshly generated block.

    Raises SystemExit with a readable message if the markers are missing, since
    silently appending the table to the end of the README would be worse than
    failing loudly.
    """
    pattern = re.compile(
        re.escape(BEGIN_MARKER) + r".*?" + re.escape(END_MARKER),
        re.DOTALL,  # so `.` matches across the newlines inside the block
    )

    if not pattern.search(readme_text):
        sys.exit(
            f"error: could not find the index markers in {README.name}.\n"
            f"Add these two lines where the table should appear:\n\n"
            f"  {BEGIN_MARKER}\n  {END_MARKER}\n"
        )

    # A lambda replacement avoids re.sub interpreting backslashes or \1 style
    # group references inside the generated block. Worth knowing: passing a
    # plain string here is a classic source of mangled output.
    return pattern.sub(lambda _: block, readme_text, count=1)


# --- Entry point -------------------------------------------------------------

def main():
    check_only = "--check" in sys.argv

    if not PROMPTS_DIR.is_dir():
        sys.exit(f"error: {PROMPTS_DIR} does not exist.")

    current = README.read_text(encoding="utf-8")
    updated = splice(current, render_index(collect_prompts()))

    if current == updated:
        print("Prompt index is up to date.")
        return 0

    if check_only:
        print(
            "Prompt index is OUT OF DATE.\n"
            "Run: python3 scripts/generate_prompt_index.py\n"
            "then commit the updated README.md."
        )
        return 1

    README.write_text(updated, encoding="utf-8")
    print("Prompt index updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
