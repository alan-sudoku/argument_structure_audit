#!/usr/bin/env python3
"""Run T1 structural checks against a single argument document.

T1 checks are the automatable subset of the Argument Structure Audit
(specification.md §5). They test syntactic and structural properties that a
blank AI can evaluate without domain knowledge. T2 checks (MECE, LOGIC-TYPE,
LOAD-TEST, HEADING-SYNTHESIS) require a human domain-expert auditor and are
not implemented here.

Checks run in specification-mandated phase order (specification.md §6):
  RC1           Heading hierarchy is present and correctly structured
  CONTENT-TYPE  Arguments and Closures are visually distinct from Claims
  CLAIM-FIRST   First sentence of every definition item is a standalone claim
  CONSEQUENCE   Last sentence of every sub-item states a consequence unit
  TYPE-LABEL    Every sub-item label uses *[Type] ([Topic]):* format
  RC2           Typed sub-items are list items, not flat paragraphs
  RC3           Numbered bold items are identified as Claims by a convention note

Output:
  1. Per-check severity-sorted findings (mirrors test_doc_quality.py format)
  2. Markdown summary table in T1 strip Execution Protocol format

No third-party dependencies.

Usage:
    python t1_check.py <document.md>
"""

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

# Fenced code/mermaid block opener — used to skip structural content inside blocks.
FENCE_RE = re.compile(r"^(`{3,}|~{3,})")

# ATX heading.
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)")

# Numbered bold definition item: "1. **Label** rest"
# e.g. "3. **Thermodynamic constraint** because X" → groups: ("3", "Thermodynamic constraint", "because X")
NUMBERED_RE = re.compile(r"^([0-9]+)\.\s+\*\*(.+?)\*\*\s*(.*)")

# Standalone **Claim:** paragraph (alternative definition_item form).
BOLD_CLAIM_RE = re.compile(r"^\*\*Claim:\*\*\s+(.*)")

# List item — captures (indent whitespace, body).
SUBITEM_RE = re.compile(r"^(\s*)- (.*)")

# TYPE-LABEL: "*Type (Topic):*"
# e.g. "*Argument (energy cost):*" → groups: ("Argument", "energy cost")
# (.+?) allows nested parens, e.g. "*Scope (difference (b) precondition):*"
LABEL_RE = re.compile(r"^\*([\w]+)\s*\((.+?)\):\*")

# Sentence boundary heuristic — splits on sentence-ending punctuation followed
# by a capital letter or markup delimiter.
# e.g. "X is true. Because Y" → splits before "Because"; "costs $3. Next" → splits before "Next".
# Used for lead/consequence extraction.
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z$\\\*\[])")

# A last sentence that is only a §N section reference with nothing after it —
# e.g. "...is covered in §6." or "...see §2.3." — is the invalid pointer-only consequence form.
SECTION_REF_RE = re.compile(r"§\d+(\.\d+)*\s*$")

# Last sentence containing an OQ- reference names an open question, which is a
# valid consequence form per specification.md §5 CONSEQUENCE check.
OQ_REF_RE = re.compile(r"\bOQ-")

# Convention note pattern for RC3: a sentence stating numbered bold items are Claims.
# e.g. "numbered bold items are Claims" or "numbered bold definition is a claim"
CONVENTION_RE = re.compile(r"numbered.{0,30}bold.{0,30}claim", re.I)

# The four valid content types from specification.md §3.
VALID_TYPES = {"Claim", "Scope", "Argument", "Closure"}

# Lead sentence patterns that are structurally non-claim starts.
# These indicate the block opens with a condition, qualification, or universal
# quantifier rather than a standalone claim — a detectable CLAIM-FIRST failure.
CLAIM_NON_STARTS = re.compile(r"^(Under |Whether |For all )", re.I)

# Severity ordering for sort — CRITICAL surfaces before SIGNIFICANT before MINOR.
SEV_RANK = {"CRITICAL": 0, "SIGNIFICANT": 1, "MINOR": 2}


# ---------------------------------------------------------------------------
# Finding dataclass
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    """A single audit finding from one check.

    result distinguishes outcome types:
      "Fail"      — detectable structural violation
      "Escalated" — requires domain context; routed to T2 reviewer
      "N/A"       — check is inapplicable for this document class
    """
    severity: str  # "CRITICAL" | "SIGNIFICANT" | "MINOR"
    file: str
    line: int
    check: str     # check name e.g. "RC1", "CLAIM-FIRST"
    result: str    # "Fail" | "Escalated" | "N/A"
    note: str

    def __lt__(self, other):
        return (SEV_RANK[self.severity], self.line) < (SEV_RANK[other.severity], other.line)


# ---------------------------------------------------------------------------
# Shared document iterators
# ---------------------------------------------------------------------------

# fence-skipping iterator — standalone duplicate of test_doc_quality.py pattern.
# Both files are standalone scripts (no shared imports), so this is intentionally
# duplicated rather than imported.
def _iter_prose(lines):
    """Yield (1-based lineno, line) for all lines outside fenced code blocks."""
    in_fence = False
    fence_marker = ""
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not in_fence and FENCE_RE.match(stripped):
            in_fence = True
            fence_marker = stripped[:3]
            continue
        if in_fence and stripped.startswith(fence_marker):
            in_fence = False
            continue
        if not in_fence:
            yield i, line


def _extract_headings(lines):
    """Return [(level, text, lineno)] for all headings outside code blocks."""
    result = []
    in_fence = False
    fence_marker = ""
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not in_fence and FENCE_RE.match(stripped):
            in_fence = True
            fence_marker = stripped[:3]
            continue
        if in_fence and stripped.startswith(fence_marker):
            in_fence = False
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if m:
            result.append((len(m.group(1)), m.group(2).strip(), i))
    return result


def _split_sentences(text):
    """Split prose into sentences using the punctuation-capital heuristic.

    >>> _split_sentences("X holds. Because Y follows.")
    ['X holds.', 'Because Y follows.']
    >>> _split_sentences("Single sentence only.")
    ['Single sentence only.']
    >>> _split_sentences("Contains $3. Next claim.")
    ['Contains $3.', 'Next claim.']
    >>> _split_sentences("")
    ['']
    """
    text = text.strip()
    if not text:
        return [""]
    parts = SENTENCE_SPLIT_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def _extract_definition_items(lines):
    """Return [(text, lineno)] for all definition items (numbered bold, **Claim:**).

    Definition items can span multiple continuation lines, so this accumulator
    collects prose lines until the next token boundary (heading, sub-item, or
    new definition item) before emitting each item.

    CLAIM-FIRST runs against these items: the first sentence of each should be a
    standalone claim without requiring the reader to continue into the body.
    """
    items = []
    in_fence = False
    fence_marker = ""
    accumulating = None
    acc_lineno = 0
    acc_lines = []

    def flush():
        if accumulating is not None:
            text = " ".join(acc_lines).strip()
            items.append((text, acc_lineno))

    for i, line in enumerate(lines, 1):
        stripped = line.rstrip()
        if not in_fence and FENCE_RE.match(stripped.strip()):
            in_fence = True
            fence_marker = stripped.strip()[:3]
            flush()
            accumulating = None
            acc_lines = []
            continue
        if in_fence:
            if stripped.strip().startswith(fence_marker):
                in_fence = False
            continue

        nm = NUMBERED_RE.match(stripped)
        bcm = BOLD_CLAIM_RE.match(stripped)
        sm = SUBITEM_RE.match(line)

        if nm or bcm:
            flush()
            accumulating = True
            acc_lineno = i
            acc_lines = [nm.group(3).strip() if nm else bcm.group(1).strip()]
        elif sm:
            # Sub-items belong to a definition item's children, not its body.
            flush()
            accumulating = None
            acc_lines = []
        elif HEADING_RE.match(stripped):
            flush()
            accumulating = None
            acc_lines = []
        elif accumulating and stripped:
            acc_lines.append(stripped)

    flush()
    return items


def _extract_sub_items(lines):
    """Return [(indent, body, lineno)] for all list items outside code blocks.

    Indent is the number of leading spaces; body is the text after "- ".
    CONSEQUENCE, TYPE-LABEL, and RC2 checks all operate at the sub-item level.
    """
    items = []
    in_fence = False
    fence_marker = ""
    for i, line in enumerate(lines, 1):
        stripped = line.rstrip()
        if not in_fence and FENCE_RE.match(stripped.strip()):
            in_fence = True
            fence_marker = stripped.strip()[:3]
            continue
        if in_fence:
            if stripped.strip().startswith(fence_marker):
                in_fence = False
            continue
        m = SUBITEM_RE.match(line)
        if m:
            indent = len(m.group(1))
            body = m.group(2).strip()
            items.append((indent, body, i))
    return items


# ---------------------------------------------------------------------------
# T1 checks
# ---------------------------------------------------------------------------

def check_rc1(lines, rel):
    """RC1 — Heading Hierarchy (precondition gate for Phase 1).

    A skipped heading level (e.g. ## → ####) breaks the structural hierarchy
    that HEADING-SYNTHESIS and parent-child edge extraction depend on.
    Flagged as SIGNIFICANT rather than CRITICAL because RC1 failures are local:
    they block synthesis checks for the affected section but not the full audit.
    """
    headings = _extract_headings(lines)
    findings = []
    for idx in range(1, len(headings)):
        prev_level = headings[idx - 1][0]
        curr_level, _, lineno = headings[idx]
        if curr_level > prev_level + 1:
            findings.append(Finding(
                severity="SIGNIFICANT", file=rel, line=lineno,
                check="RC1", result="Fail",
                note=(
                    f"Heading level skipped: h{prev_level} → h{curr_level} "
                    f"(expected h{prev_level + 1} or shallower)"
                ),
            ))
    return findings


def check_content_type(lines, rel):
    """CONTENT-TYPE — Visual separation of content types (Phase 1).

    Arguments and Closures at the same visual weight as Claims force the reader
    to read the full block to determine relevance. Detection here is structural:
    a TYPE-LABEL that is Argument or Closure appearing in flat prose (not a
    list item) is the clearest mechanical signal of the separation failure.
    """
    findings = []
    for lineno, line in _iter_prose(lines):
        stripped = line.strip()
        # Skip lines that are already correctly structured.
        if SUBITEM_RE.match(line):
            continue
        if HEADING_RE.match(stripped) or NUMBERED_RE.match(stripped) or BOLD_CLAIM_RE.match(stripped):
            continue
        m = LABEL_RE.match(stripped)
        if m:
            label_type = m.group(1)
            # Only Argument and Closure in flat prose are the separation failure.
            # Scope in flat prose is less severe and may be intentional.
            if label_type in ("Argument", "Closure"):
                findings.append(Finding(
                    severity="SIGNIFICANT", file=rel, line=lineno,
                    check="CONTENT-TYPE", result="Fail",
                    note=(
                        f"*{label_type}* label found in flat prose (not a list item) "
                        f"— should be a sub-item under its parent claim"
                    ),
                ))
    return findings


def check_claim_first(lines, rel):
    """CLAIM-FIRST — Inverted pyramid at the definition-item level (Phase 1).

    The first sentence of each definition item must be a standalone claim the
    receiver can hold without reading further. Mechanical detection covers two
    clear non-claim patterns:
      - Starts with "Under / Whether / For all" → conditional or universal opener
      - Ends with ":" → setup clause, not a claim

    Everything else is Escalated: whether a sentence constitutes a standalone
    claim requires semantic judgment that a blank AI cannot apply reliably.
    Escalated findings are routed to the T2 reviewer.
    """
    findings = []
    def_items = _extract_definition_items(lines)
    for text, lineno in def_items:
        if not text:
            findings.append(Finding(
                severity="CRITICAL", file=rel, line=lineno,
                check="CLAIM-FIRST", result="Fail",
                note="Definition item has no body text",
            ))
            continue
        sentences = _split_sentences(text)
        lead = sentences[0] if sentences else ""
        if CLAIM_NON_STARTS.match(lead):
            findings.append(Finding(
                severity="SIGNIFICANT", file=rel, line=lineno,
                check="CLAIM-FIRST", result="Fail",
                note=f"Lead sentence starts with non-claim pattern: '{lead[:80]}'",
            ))
        elif lead.rstrip().endswith(":"):
            findings.append(Finding(
                severity="SIGNIFICANT", file=rel, line=lineno,
                check="CLAIM-FIRST", result="Fail",
                note=(
                    f"Lead sentence ends with ':' — setup clause, not a standalone claim: "
                    f"'{lead[:80]}'"
                ),
            ))
        else:
            # Cannot determine standalone claim status without domain context.
            findings.append(Finding(
                severity="MINOR", file=rel, line=lineno,
                check="CLAIM-FIRST", result="Escalated",
                note="Cannot determine standalone claim status without domain context — escalate to T2",
            ))
    return findings


def check_consequence(lines, rel):
    """CONSEQUENCE — Consequence sentence at the end of each sub-item (Phase 3).

    The last sentence must state what is now ruled out, permitted, required, or
    left as an open question. Two patterns are mechanically detectable:
      - Last sentence is a bare §N reference (pointer-only invalid form)
      - Last sentence contains OQ- (open question reference — valid form)

    Everything else is Escalated: whether a sentence satisfies a valid consequence
    form requires understanding the document's domain boundary conditions.
    """
    findings = []
    sub_items = _extract_sub_items(lines)
    for indent, body, lineno in sub_items:
        sentences = _split_sentences(body)
        if not sentences:
            continue
        last = sentences[-1]

        if len(sentences) == 1:
            # Single-sentence item: the CLAIM-FIRST bypass may apply (the lead
            # claim already states the consequence). Human judgment required.
            findings.append(Finding(
                severity="MINOR", file=rel, line=lineno,
                check="CONSEQUENCE", result="Escalated",
                note="Single-sentence item — check if CLAIM-FIRST bypass applies (lead = consequence)",
            ))
            continue

        if SECTION_REF_RE.search(last) and not OQ_REF_RE.search(last):
            # Ends with "...§N." — pointer without a conclusion.
            findings.append(Finding(
                severity="SIGNIFICANT", file=rel, line=lineno,
                check="CONSEQUENCE", result="Fail",
                note=f"Last sentence appears to be a pointer-only section reference: '{last[:100]}'",
            ))
        elif OQ_REF_RE.search(last):
            pass  # names open question — valid consequence form per spec §5
        else:
            findings.append(Finding(
                severity="MINOR", file=rel, line=lineno,
                check="CONSEQUENCE", result="Escalated",
                note="Consequence validity requires domain context — escalate to T2",
            ))
    return findings


def check_type_label(lines, rel):
    """TYPE-LABEL — Label function check for all sub-items (Phase 4).

    Every sub-item must open with *[Type] ([Topic]):* where Type is one of
    {Claim, Scope, Argument, Closure}. Two failure modes:
      - No label at all: the receiver cannot triage without reading the full block
      - Pseudo-functional label: lead word exists but is outside the taxonomy
        (e.g. *Example:*, *Consequence:*) — classifies presentation, not content type
    """
    findings = []
    sub_items = _extract_sub_items(lines)
    for indent, body, lineno in sub_items:
        m = LABEL_RE.match(body)
        if not m:
            findings.append(Finding(
                severity="SIGNIFICANT", file=rel, line=lineno,
                check="TYPE-LABEL", result="Fail",
                note=(
                    f"Sub-item has no TYPE-LABEL — "
                    f"expected *[Type] ([Topic]):* format: '{body[:80]}'"
                ),
            ))
        elif m.group(1) not in VALID_TYPES:
            findings.append(Finding(
                severity="SIGNIFICANT", file=rel, line=lineno,
                check="TYPE-LABEL", result="Fail",
                note=(
                    f"Pseudo-functional label '*{m.group(1)}:*' — "
                    f"lead word not in {{Claim, Scope, Argument, Closure}}"
                ),
            ))
    return findings


def check_rc2(lines, rel):
    """RC2 — List structure for typed sub-items (post-Phase 4 encoding check).

    TYPE-LABEL ensures sub-items carry the right label. RC2 ensures they are
    also encoded as list items ("- *Type...*") rather than flat paragraphs.
    Flat paragraphs with typed labels pass TYPE-LABEL visually but fail the
    structural encoding test: an AI processing raw tokens cannot recover the
    parent-child containment relationship from a flat paragraph.
    """
    findings = []
    for lineno, line in _iter_prose(lines):
        stripped = line.strip()
        if SUBITEM_RE.match(line):
            continue  # correctly formatted — skip
        m = LABEL_RE.match(stripped)
        if m and m.group(1) in VALID_TYPES:
            findings.append(Finding(
                severity="SIGNIFICANT", file=rel, line=lineno,
                check="RC2", result="Fail",
                note=(
                    f"Typed label in flat paragraph (not a list item) — "
                    f"convert to '- *{m.group(1)}...*': '{stripped[:80]}'"
                ),
            ))
    return findings


def check_rc3(lines, rel):
    """RC3 — Numbered item type convention (post-Phase 4 encoding check).

    When a document uses numbered bold items (e.g. "1. **Entailment map**"),
    an AI receiver cannot infer these are Claims without an explicit convention
    note. If the document has such items but no convention statement near §0,
    flag it: the type is structurally ambiguous to a blank-AI receiver.
    """
    full_text = "\n".join(lines)
    has_numbered = bool(NUMBERED_RE.search(full_text))
    if not has_numbered:
        return []  # N/A — no numbered bold items in this document
    has_convention = bool(CONVENTION_RE.search(full_text))
    if has_convention:
        return []
    return [Finding(
        severity="SIGNIFICANT", file=rel, line=1,
        check="RC3", result="Fail",
        note=(
            "Document contains numbered bold items but no convention note "
            "stating they are Claims — add a note near §0 or apply explicit "
            "*Claim:* lead to each item"
        ),
    )]


# ---------------------------------------------------------------------------
# Check registry — defines execution order per specification.md §6
# ---------------------------------------------------------------------------

CHECKS = [
    ("RC1",          check_rc1),
    ("CONTENT-TYPE", check_content_type),
    ("CLAIM-FIRST",  check_claim_first),
    ("CONSEQUENCE",  check_consequence),
    ("TYPE-LABEL",   check_type_label),
    ("RC2",          check_rc2),
    ("RC3",          check_rc3),
]

SEV_LABEL = {
    "CRITICAL":    "CRITICAL   ",
    "SIGNIFICANT": "SIGNIFICANT",
    "MINOR":       "MINOR      ",
}


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _print_findings(findings):
    """Print severity-sorted findings in the same format as test_doc_quality.py."""
    for f in sorted(findings):
        tag = SEV_LABEL.get(f.severity, f.severity)
        print(f"  [{tag}] {f.file}:{f.line}")
        print(f"           {f.note}")


def collect_results(lines, rel):
    """Run all T1 checks in phase order and return results dict.

    Returns {check_name: (findings, counts)} where counts is
    {severity: int}. Does not print anything.
    """
    check_results = {}
    for name, fn in CHECKS:
        findings = fn(lines, rel)
        counts = defaultdict(int)
        for f in findings:
            counts[f.severity] += 1
        check_results[name] = (findings, counts)
    return check_results


def _print_check_block(name, findings, counts):
    """Print the per-check status block to stdout."""
    fails     = [f for f in findings if f.result == "Fail"]
    escalated = [f for f in findings if f.result == "Escalated"]

    if not fails:
        status = "PASS" if not escalated else "INFO"
    else:
        status = "FAIL" if any(f.severity == "CRITICAL" for f in fails) else "WARN"

    print(f"[{status}] {name}")
    if fails:
        c = counts.get("CRITICAL", 0)
        s = counts.get("SIGNIFICANT", 0)
        m = counts.get("MINOR", 0)
        print(f"       Critical={c}  Significant={s}  Minor={m}")
        _print_findings(fails)
    elif escalated:
        print(f"       Escalated={len(escalated)} (T2 review required)")
    print()


def _print_summary(check_results):
    """Print the totals line and Markdown summary table."""
    total_c = sum(v.get("CRITICAL", 0)    for _, v in check_results.values())
    total_s = sum(v.get("SIGNIFICANT", 0) for _, v in check_results.values())
    total_m = sum(v.get("MINOR", 0)       for _, v in check_results.values())
    print("─" * 60)
    print(f"Total  Critical={total_c}  Significant={total_s}  Minor={total_m}")

    print()
    print("| Check | Result | Notes |")
    print("| :--- | :--- | :--- |")
    for name, (findings, counts) in check_results.items():
        fails     = [f for f in findings if f.result == "Fail"]
        escalated = [f for f in findings if f.result == "Escalated"]
        if not fails and not escalated:
            result_cell, notes = "[Pass]", ""
        elif escalated and not fails:
            result_cell = "[Escalated]"
            notes = f"{len(escalated)} items require T2 review"
        else:
            result_cell = "[Fail]"
            sigs  = counts.get("CRITICAL", 0) + counts.get("SIGNIFICANT", 0)
            notes = f"{sigs} failure(s)"
        print(f"| {name} | {result_cell} | {notes} |")

    return total_c


def run_all(path):
    """Orchestrate T1 checks: read → collect → print → summarise → exit code.

    Returns 1 if any CRITICAL findings exist, 0 otherwise.
    """
    p = Path(path)
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        print(f"Error: could not read file — {path} ({e.strerror})", file=sys.stderr)
        sys.exit(1)
    rel = p.name
    print(f"Running T1 checks on: {path}\n")

    check_results = collect_results(lines, rel)

    for name, (findings, counts) in check_results.items():
        _print_check_block(name, findings, counts)

    total_c = _print_summary(check_results)

    if total_c > 0:
        print("\nExit 1 — CRITICAL issues must be resolved.")
        return 1
    print("\nExit 0.")
    return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run T1 structural checks on an argument document."
    )
    parser.add_argument("document", help="Path to the Markdown document")
    args = parser.parse_args()
    sys.exit(run_all(args.document))


if __name__ == "__main__":
    main()
