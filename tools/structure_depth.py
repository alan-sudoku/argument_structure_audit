#!/usr/bin/env python3
"""Indentation depth and encoding audit for a Markdown argument document.

Reports, for a given file (and optionally a section anchor), what depth
levels are present and which encoding method is used at each level.

Encoding methods detected:
  heading    — ## / ### / #### section headings (depth derived from # count)
  bullet     — "  - " list item (depth = leading spaces // 2, +1 for heading base)
  numbered   — "1. " / "2. " list item at line start or after indent
  inline     — (a)/(b)/(c) or (i)/(ii)/(iii)/(iv) tokens embedded in prose
  prose      — paragraph text with no structural marker

Inline tokens are the key blind-spot: extract_graph.py treats them as
undifferentiated body text, making their sub-items invisible to the graph.

Usage:
    python tools/structure_depth.py <document.md>
    python tools/structure_depth.py <document.md> --section "OQ-EC.23"
    python tools/structure_depth.py <document.md> --lines 620 660
    python tools/structure_depth.py <document.md> --annotate
    python tools/structure_depth.py <document.md> --section "8" --annotate

Scope assumptions (EC corpus, 2-space indent, hyphen bullets — 2026-05):
  - Bullet markers: hyphen only (`- `); `*` and `+` not detected
  - Indentation: 2 spaces per level; 4-space documents will misreport depth
  - Roman numeral false positives: short roman-letter words in parens e.g. (vi), (ix) may trigger
  - LABEL_RE: single-asterisk italic only; **bold** labels fall through to OQ_HDR_RE or prose
  - extract_scope calls sys.exit directly; refactor to ValueError if script is imported
  - LaTeX: $...$ spans are stripped before inline detection; display math ($$) not handled
  - Tables: | row | cells | are skipped entirely; inline tokens in table cells not detected
  - Inline action suppressed for count=1 (single token cannot be split into a list)
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

HEADING_RE   = re.compile(r"^(#{1,6})\s+(.*)")
BULLET_RE    = re.compile(r"^(\s*)- (.+)")
NUMBERED_RE  = re.compile(r"^(\s*)(\d+)\.\s+(.+)")
INLINE_ABC   = re.compile(r"\(([a-z])\)\s+\S")
INLINE_ROM   = re.compile(r"\(([ivxlc]{1,4})\)\s+\S")
INLINE_UPP   = re.compile(r"\(([A-Z])\)\s+[a-zA-Z\*\$]")

# Explicit type label: "*Label (topic):*" or "*Label:*"
LABEL_RE     = re.compile(r"^\*([^*:()]+?)(?:\s*\([^)]+\))?:\*")
# Bold OQ header: "**OQ-EC.N — ..."
OQ_HDR_RE    = re.compile(r"^\*\*(OQ-EC\.\d+)[^*]*\*\*")
# Numbered item number prefix
NUM_PREFIX_RE = re.compile(r"^\d+")
# Strip $...$ inline math before token detection to avoid LaTeX false positives
MATH_INLINE_RE = re.compile(r"\$[^$\n]+?\$")


def _strip_math(text):
    return MATH_INLINE_RE.sub("", text)


def _slug(text):
    text = re.sub(r"[§#]", "", text)
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s-]+", "-", text).strip("-")


# ---------------------------------------------------------------------------
# Inline token detection — two versions
# (audit: returns display string; annotate: returns structured dict)
# ---------------------------------------------------------------------------

def _inline_tokens(text):
    """Return display string describing inline tokens, or ''."""
    text = _strip_math(text)
    found = []
    if INLINE_ROM.search(text):
        tokens = INLINE_ROM.findall(text)
        found.append("(" + ")/(".join(tokens[:4]) + ")")
    if INLINE_ABC.search(text):
        tokens = INLINE_ABC.findall(text)
        found.append("(" + ")/(".join(tokens[:4]) + ")")
    if INLINE_UPP.search(text):
        tokens = INLINE_UPP.findall(text)
        found.append("(" + ")/(".join(tokens[:3]) + ")")
    return ", ".join(found)


def _inline_info(text):
    """Return (has_inline, scheme, count) for annotation mode.

    scheme: 'roman' | 'abc' | 'upper' | 'mixed' | None
    count: number of distinct tokens found
    """
    text = _strip_math(text)
    roman = INLINE_ROM.findall(text)
    abc   = INLINE_ABC.findall(text)
    upper = INLINE_UPP.findall(text)

    total = len(roman) + len(abc) + len(upper)
    if total == 0:
        return False, None, 0

    kinds = sum([bool(roman), bool(abc), bool(upper)])
    if kinds > 1:
        scheme = "mixed"
    elif roman:
        scheme = "roman"
    elif abc:
        scheme = "abc"
    else:
        scheme = "upper"

    return True, scheme, total


def _extract_label(body, encoding, num=None):
    """Return the item's explicit label string, or None.

    For numbered items: return the number as string if no explicit label.
    For bullets/prose: extract from *Label:* or *Label (topic):* pattern.
    """
    m = LABEL_RE.match(body.strip())
    if m:
        return m.group(1).strip()
    if encoding == "numbered" and num is not None:
        return f"SQ{num}" if num else str(num)
    return None


# ---------------------------------------------------------------------------
# Line classifier
# ---------------------------------------------------------------------------

def classify_line(line):
    """Return (raw_depth, method, label) for a single line."""
    stripped = line.rstrip()
    if not stripped:
        return None, "blank", ""

    # Skip Markdown table rows — | cell | cell | — inline tokens inside cells
    # are not structural enumeration and produce false positives.
    if stripped.lstrip().startswith("|"):
        return 0, "prose", stripped[:80]

    m = HEADING_RE.match(stripped)
    if m:
        level = len(m.group(1))
        return level - 1, "heading", f"{'#' * level} {m.group(2)[:60]}"

    m = BULLET_RE.match(stripped)
    if m:
        indent = len(m.group(1))
        depth  = indent // 2
        body   = m.group(2)[:80]
        inline = _inline_tokens(m.group(2))
        if inline:
            return depth, "bullet+inline", f"- {body}  [inline: {inline}]"
        return depth, "bullet", f"- {body}"

    m = NUMBERED_RE.match(stripped)
    if m:
        indent = len(m.group(1))
        depth  = indent // 2
        num    = m.group(2)
        body   = m.group(3)[:70]
        inline = _inline_tokens(m.group(3))
        if inline:
            return depth, "numbered+inline", f"{num}. {body}  [inline: {inline}]"
        return depth, "numbered", f"{num}. {body}"

    inline = _inline_tokens(stripped)
    if inline:
        return 0, "prose+inline", f"{stripped[:80]}  [inline: {inline}]"

    return 0, "prose", stripped[:80]


# ---------------------------------------------------------------------------
# Scope extraction
# ---------------------------------------------------------------------------

def extract_scope(lines, section_slug=None, line_start=None, line_end=None):
    """Return (scoped_lines, start_lineno)."""
    if line_start is not None:
        sl = max(0, line_start - 1)
        el = line_end if line_end else len(lines)
        return lines[sl:el], line_start

    if section_slug:
        start = None
        end   = len(lines)
        in_code = False
        for i, line in enumerate(lines):
            if line.strip().startswith("```"):
                in_code = not in_code
            if in_code:
                continue
            m = HEADING_RE.match(line.rstrip())
            if m:
                slug = _slug(m.group(2))
                if start is None:
                    if section_slug.lower() in slug:
                        start = i
                elif len(m.group(1)) <= len(HEADING_RE.match(lines[start].rstrip()).group(1)):
                    end = i
                    break
        if start is None:
            print(f"Section '{section_slug}' not found.", file=sys.stderr)
            sys.exit(1)
        return lines[start:end], start + 1

    return lines, 1


# ---------------------------------------------------------------------------
# Audit analysis (summary mode)
# ---------------------------------------------------------------------------

def analyse(scoped_lines, start_lineno):
    """Return (per_depth, findings)."""
    per_depth = defaultdict(lambda: {"methods": set(), "count": 0, "lines": [], "inline_lines": 0})
    in_code   = False
    findings  = []

    for i, line in enumerate(scoped_lines):
        lineno = start_lineno + i
        if line.strip().startswith("```"):
            in_code = not in_code
        if in_code:
            continue

        depth, method, label = classify_line(line)
        if method == "blank":
            continue

        per_depth[depth]["methods"].add(method)
        per_depth[depth]["count"]  += 1
        per_depth[depth]["lines"].append(lineno)
        if "+inline" in method:
            per_depth[depth]["inline_lines"] += 1

    for depth, info in sorted(per_depth.items()):
        structural = {m.split("+")[0] for m in info["methods"]
                      if m.split("+")[0] not in ("prose", "heading")}
        if len(structural) > 1:
            findings.append(
                f"  Depth {depth}: mixed structural encoding — "
                f"{', '.join(sorted(info['methods']))}"
            )
        if any("+inline" in m for m in info["methods"]):
            findings.append(
                f"  Depth {depth}: inline tokens present (parser-blind) — "
                f"{info['inline_lines']} line(s) affected"
            )

    return per_depth, findings


# ---------------------------------------------------------------------------
# Annotation mode — one JSON record per structural line
# ---------------------------------------------------------------------------

def annotate(scoped_lines, start_lineno):
    """Yield one dict per non-blank, non-code line.

    Fields:
      lineno       — 1-indexed source line number
      section      — nearest OQ or heading label (ancestry without re-scanning)
      depth        — nesting level (0 = directly under heading)
      encoding     — heading | bullet | numbered | prose
      has_inline   — True if inline tokens detected inside body text
      inline_scheme— roman | abc | upper | mixed | null
      inline_count — number of inline tokens found (= hidden sub-items)
      label        — explicit item label if present, else null
      action       — one-line instruction for a blank AI parser
    """
    in_code       = False
    current_section = None

    for i, raw_line in enumerate(scoped_lines):
        lineno  = start_lineno + i
        stripped = raw_line.rstrip()

        if stripped.strip().startswith("```"):
            in_code = not in_code
        if in_code:
            continue
        if not stripped.strip():
            continue

        # Track current section: ## headings and bold OQ headers
        hm = HEADING_RE.match(stripped)
        if hm:
            current_section = hm.group(2).strip()

        oq_m = OQ_HDR_RE.match(stripped)
        if oq_m:
            current_section = oq_m.group(1)

        # Classify
        depth, method, _ = classify_line(raw_line)
        base_encoding = method.split("+")[0]

        # Extract body text for inline/label analysis
        body = ""
        num  = None
        bm = BULLET_RE.match(stripped)
        nm = NUMBERED_RE.match(stripped)
        if bm:
            body = bm.group(2)
        elif nm:
            body = nm.group(3)
            num  = nm.group(2)
        elif not hm:
            body = stripped

        has_inline, scheme, count = _inline_info(body)

        # Label extraction
        label = _extract_label(body, base_encoding, num)

        # Action
        if has_inline and count >= 2:
            action = (
                f"DO NOT treat as single item. "
                f"Scan for {scheme} tokens; split into {count} sub-item(s) at depth {depth + 1}."
            )
        elif has_inline and count == 1:
            action = f"Single inline token ({scheme}) detected — likely parenthetical, not a list. Verify before splitting."
        elif base_encoding == "numbered":
            action = f"Index as cross-referenceable item {num} within current section."
        elif base_encoding == "bullet" and depth > 0:
            action = "Attach to nearest depth-0 parent above; subordinate, not standalone."
        elif base_encoding == "prose":
            action = "Read for context; do not extract as argument node."
        elif base_encoding == "heading":
            action = "Section boundary; update section context."
        else:
            action = "Read as structural item at this depth."

        yield {
            "lineno":        lineno,
            "section":       current_section,
            "depth":         depth,
            "encoding":      base_encoding,
            "has_inline":    has_inline,
            "inline_scheme": scheme,
            "inline_count":  count,
            "label":         label,
            "action":        action,
        }


# ---------------------------------------------------------------------------
# Report (summary mode)
# ---------------------------------------------------------------------------

METHOD_LABELS = {
    "heading":         "heading  (##/###)",
    "bullet":          "bullet   (-)",
    "bullet+inline":   "bullet   (-) + inline tokens  ← parser-blind",
    "numbered":        "numbered (N.)",
    "numbered+inline": "numbered (N.) + inline tokens  ← parser-blind",
    "prose":           "prose    (paragraph)",
    "prose+inline":    "prose    + inline tokens  ← parser-blind",
}

def report(per_depth, findings, scope_label):
    print(f"\nStructure depth report — {scope_label}")
    print("=" * 60)

    if not per_depth:
        print("  No structured content found in scope.")
        return

    max_depth = max(per_depth.keys())
    print(f"  Depth levels present: 0 – {max_depth}  ({max_depth + 1} level(s))\n")

    print(f"  {'Depth':<7} {'Count':>5}   Encoding method(s)")
    print(f"  {'-'*6} {'-'*5}   {'-'*40}")

    for depth in sorted(per_depth.keys()):
        info    = per_depth[depth]
        methods = sorted(info["methods"])
        first   = True
        for method in methods:
            label = METHOD_LABELS.get(method, method)
            if first:
                print(f"  {depth:<7} {info['count']:>5}   {label}")
                first = False
            else:
                print(f"  {'':7} {'':>5}   {label}")

    if findings:
        print(f"\n  Findings:")
        for f in findings:
            print(f)
    else:
        print(f"\n  No encoding inconsistencies detected.")

    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Audit indentation depth and encoding method in a Markdown document."
    )
    parser.add_argument("document", help="Path to Markdown file")
    parser.add_argument("--section", metavar="SLUG",
        help="Scope to section whose heading contains this string (case-insensitive)")
    parser.add_argument("--lines", nargs=2, type=int, metavar=("START", "END"),
        help="Scope to line range (1-indexed, inclusive)")
    parser.add_argument("--annotate", action="store_true",
        help="Output one JSON record per structural line for AI parser consumption")
    args = parser.parse_args()

    if args.lines and args.lines[0] > args.lines[1]:
        parser.error(f"START line ({args.lines[0]}) must be <= END line ({args.lines[1]})")

    path = Path(args.document)
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

    line_start = args.lines[0] if args.lines else None
    line_end   = args.lines[1] if args.lines else None

    scoped, start_lineno = extract_scope(lines, args.section, line_start, line_end)

    if args.section:
        scope_label = f"section '{args.section}'"
    elif args.lines:
        scope_label = f"lines {args.lines[0]}–{args.lines[1]}"
    else:
        scope_label = path.name

    if args.annotate:
        for record in annotate(scoped, start_lineno):
            print(json.dumps(record))
    else:
        per_depth, findings = analyse(scoped, start_lineno)
        report(per_depth, findings, scope_label)


if __name__ == "__main__":
    main()

