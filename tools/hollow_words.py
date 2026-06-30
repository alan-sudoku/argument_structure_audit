#!/usr/bin/env python3
"""Hollow-word pre-audit for argument documents.

Scans a document for words and phrases that weaken arguments by substituting
vague signal for concrete claim. Each hit identifies the word, the implied
question it leaves unanswered, and the line — so a practitioner can triage
before formal audit.

Rationale: hollow words are an argument-level defect, not just a style issue.
A claim built on "robust," "foundational," or "seamless" cannot be falsified
because no concrete property is asserted. The auditor cannot evaluate what the
author hasn't stated.

Exit code 0 for clean runs and runs with findings; 1 only on system errors (file not found, decode error).

Usage:
    python tools/hollow_words.py <document.md>
    python tools/hollow_words.py <document.md> --counts   # summary only
"""

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


# ---------------------------------------------------------------------------
# Word list
# Each entry: word/phrase (lowercase) → implied question the author must answer
# ---------------------------------------------------------------------------

HOLLOW: dict[str, str] = {
    # Drama verbs — AI prefers them over plain verbs
    "delve":                    "what specifically are you examining?",
    "foster":                   "what mechanism produces this outcome?",
    "leverage":                 "use — say 'use'",
    "utilize":                  "use — say 'use'",
    "underscore":               "say 'shows' or 'demonstrates'",
    "unleash":                  "what specifically becomes available?",
    "unlock":                   "what specifically becomes available?",
    "elevate":                  "what improves, and by what measure?",
    "supercharge":              "what improves, and by what measure?",
    "testament":                "state the evidence directly",
    "revolutionize":            "what specific mechanism changes, and how does it replace the existing standard?",
    "disrupt":                  "which established method is displaced, and by what mechanism?",
    "empower":                  "what action can the entity now perform that was previously impossible?",
    "demystify":                "what specific mechanism or concept are you explaining?",
    "streamline":               "what steps are removed, and what is the reduction in effort?",
    "optimize":                 "what is the baseline metric, the new metric, and the objective function?",

    # Importance assertions — assert that something matters without showing consequences
    "crucial":                  "what fails if this is omitted or incorrect?",
    "vital":                    "what fails if this is omitted or incorrect?",
    "paramount":                "paramount compared to what competing priorities?",
    "key":                      "which specific attribute makes this primary?",
    "critical path":            "critical path to what outcome? what is blocked if this step is delayed or absent?",
    "essential dependency":     "say what breaks: 'without X, Y cannot proceed' — name X and Y explicitly",

    # Vague quantifiers — borrow precision connotation without providing data
    "significantly":            "by how much? provide a threshold or quantitative bound",
    "substantially":            "by what measure or percentage?",
    "vastly":                   "by what order of magnitude?",
    "virtually":                "almost, or completely? state the actual rate or exception class",

    # Adjective inflation — sounds precise, asserts nothing
    "seamless":                 "seamless under which conditions, for which user?",
    "robust":                   "invariant under which perturbations?",
    "cutting-edge":             "which specific advance over what prior state?",
    "state-of-the-art":         "which specific advance over what prior state?",
    "transformative":           "what changes, in what direction, by how much?",
    "groundbreaking":           "what prior assumption does this break?",
    "dynamic":                  "varying on which dimension, over which range?",

    # Structural vocabulary — earns its place only if structure is named
    "structural":               "which arrangement? what would a different one look like?",
    "systematic":               "which system? what are its components?",
    "holistic":                 "as opposed to what decomposition?",
    "foundational":             "what rests on it?",
    "fundamental":              "fundamental to what? what depends on it?",
    "load-bearing":             "say what the condition does: 'X is what makes Y possible' or 'without X, Z fails'",
    "nuanced":                  "simpler than what view?",

    # Epistemic weasels — weaken the claim they attach to
    "essentially":              "stripped of what? state the precise claim",
    "effectively":              "same as, or approximately same as? say which",
    "arguably":                 "argued by whom, with what support?",
    "fully":                    "in all respects, or only in some? state which conditions are met and which are not",
    "in many ways":             "name the ways",

    # Abstract metaphors — say the actual thing
    "tapestry":                 "say the actual structure or set",
    "beacon":                   "say the actual property",
    "landscape":                "say the actual space, domain, or set",
    "realm":                    "say 'domain' or name the field",
    "plethora":                 "say 'many'",
    "myriad":                   "say 'many'",
    "synergy":                  "name the specific interaction",
    "paradigm shift":           "what assumption changes, and to what?",

    # Corporate filler
    "at its core":              "filler — state the claim directly",
    "in essence":               "filler — state the claim directly",
    "it is important to note":  "filler — make the point directly",
    "in conclusion":            "filler — omit or make the final claim directly",
    "ultimately":               "filler — make the claim without the preamble",
    "not only":                 "filler construction — often padded — trim",
    "in order to":              "filler — say 'to'",

    # -----------------------------------------------------------------------
    # Argument integrity markers — the word isn't hollow but makes an implicit
    # claim about epistemic status the argument may not satisfy. Three types:
    #
    #   Conclusion markers  — assert deductive entailment; verify the premises
    #                         actually close the gap
    #   Premise markers     — assert a claim is already established; verify
    #                         the source exists and is used consistently
    #   Terminology smuggling — borrow a field's formal authority; verify the
    #                         specific result applies without extra assumptions
    # -----------------------------------------------------------------------

    # Conclusion markers
    "therefore":                "asserts entailment — do the premises actually force this, or is the step inductive?",
    "thus":                     "asserts entailment — same question as 'therefore'",
    "definitively":             "what closes off the alternatives? name the proof or exhaustive case analysis",
    "conclusively":             "what excludes competing explanations?",
    "unconditionally":          "holds under all conditions, or only within the stated scope? name the domain",
    "rigorous":                 "by which standard? state the criteria that distinguish this from an informal treatment — or remove",
    "rigorously":               "by which standard? state the criteria that distinguish this from an informal treatment — or remove",
    "necessarily":              "logically necessary, or empirically contingent? state which",
    "it follows that":          "does it follow deductively, or by analogy or induction?",

    # Premise markers
    "grounded in":              "which specific result? confirm it is used consistently here",
    "well-established":         "established where, by whom, within what scope?",
    "by definition":            "whose definition? where stated? is it applied consistently?",
    "it is known that":         "known to whom? in which literature? within what scope?",
    "authoritative":            "authoritative by which standard, in which field, and for which claim?",

    # Terminology smuggling
    "mathematically":           "which result or theorem? state it — does it apply here without additional assumptions?",
    "formally":                 "in which formal system? state the definition or rule being applied",
    "provably":                 "by which proof? or is this a conjecture stated as established?",
    "information-theoretically": "which result (DPI, Shannon, rate-distortion)? does it apply directly or by analogy?",
    "thermodynamically":        "which law or theorem? state it",

    # Unanchored evidence claims — assert observational support without naming it;
    # distinct from terminology smuggling (misapplied formalism) — here the
    # evidence may not exist or may not support the strength of the claim
    "empirically":              "which observation? controlled under what conditions? what scope?",
    "observationally":          "which observation? is it systematic or anecdotal?",
    "experimentally":           "which experiment? what controls? what was measured?",
    "studies show":             "which studies? what population? what effect size?",
    "research suggests":        "which research? peer-reviewed? in what domain?",
    "evidence suggests":        "which evidence? direct observation or inference?",

    # False self-evidence markers — assert a step needs no explanation; often
    # where the actual argument gap is hidden
    "obviously":                "obvious to whom? state the reasoning step explicitly",
    "clearly":                  "clearly to whom? state the reasoning step explicitly",
    "trivially":                "trivial by which formal argument? state it",
    "of course":                "state the reasoning — 'of course' skips the gap",
    "it is clear that":         "state the reasoning — if it were clear, it would not need asserting",

    # Authority smuggling — invoke consensus without a source; weaker than
    # 'studies show' because no source is even implied
    "experts agree":            "which experts? in which field? cite the source or restate as your own claim",
    "it is widely accepted":    "accepted where, by whom, within what scope?",
    "consensus holds":          "which community? what is the evidence base for the consensus?",
    "it is generally understood": "understood by whom? state the claim as your own or cite the source",
    "everyone knows":           "appeal to popularity — provide the rate or citation; do not assume universal agreement",
    "common sense":             "bypasses analysis — state the underlying logical or physical principle directly",

    # Overconfidence markers — shut down legitimate debate by asserting
    # a claim is beyond challenge; same failure mode as 'definitively'
    "indisputable":             "if indisputable, state the proof — otherwise name and address the valid counterarguments",
    "undeniable":               "same as 'indisputable' — state the proof or address the counterarguments",

    # False dilemma markers — assert only two options exist without
    # eliminating the alternatives
    "only alternative":         "false dilemma — what other options were analysed? show why they were excluded",
    "sole solution":            "false dilemma — what other options were analysed? show why they were excluded",
    "inevitably":               "what causal chain guarantees this outcome? state the steps — distinguish logical from empirical necessity",
    "paves the way for":        "slippery slope — what specific mechanism links this action to the stated outcome?",

    # Appeals to intuition — assert correctness by feel rather than argument
    "intuitive":                "intuitive to whom? ground the claim in evidence, cognitive load data, or established standards",
}

# Single combined regex sorted longest-first so phrases match before their component words
_COMBINED_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in sorted(HOLLOW, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

FENCE_RE = re.compile(r"^(`{3,}|~{3,})")


def _iter_prose(lines: list[str]) -> Iterator[tuple[int, str]]:
    """Yield (1-based lineno, line) outside fenced code/mermaid blocks."""
    in_fence = False
    fence_marker = ""
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        m = FENCE_RE.match(stripped)
        if not in_fence and m:
            in_fence = True
            fence_marker = m.group(1)
            continue
        if in_fence:
            if stripped.startswith(fence_marker):
                in_fence = False
            continue
        yield i, line


def _clean(line: str) -> str:
    """Strip inline math and code spans — avoid false positives inside formulas."""
    line = re.sub(r"\$[^$]+\$", " ", line)
    line = re.sub(r"`[^`]+`",   " ", line)
    return line


# ---------------------------------------------------------------------------
# Finding
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    lineno: int
    word:   str
    hint:   str
    text:   str   # stripped source line for context

    def __lt__(self, other):
        return self.lineno < other.lineno


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

def scan(path: Path) -> list[Finding]:
    lines = path.read_text(encoding="utf-8").splitlines()
    findings: list[Finding] = []

    for lineno, line in _iter_prose(lines):
        check = _clean(line)
        source = line.strip()

        for m in _COMBINED_RE.finditer(check):
            word = m.group(0).lower()
            findings.append(Finding(lineno, word, HOLLOW[word], source))

    return sorted(findings)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _print_findings(findings: list[Finding], path: Path, counts_only: bool) -> None:
    if not findings:
        print(f"{path}: no hollow words found.")
        return

    by_word: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        by_word[f.word].append(f)

    if counts_only:
        print(f"\n{path} — {len(findings)} finding(s) across {len(by_word)} word(s)\n")
        for word in sorted(by_word, key=lambda w: -len(by_word[w])):
            hits = by_word[word]
            lines = ", ".join(str(f.lineno) for f in hits)
            print(f"  {word!r:30s}  ×{len(hits)}  (lines {lines})")
            print(f"  {'':30s}  → {hits[0].hint}")
        return

    print(f"\n{path} — {len(findings)} finding(s)\n")
    for f in sorted(findings):
        print(f"  line {f.lineno:4d}  '{f.word}'")
        print(f"         → {f.hint}")
        # Show context with the word highlighted in brackets
        highlighted = re.sub(
            r"\b" + re.escape(f.word) + r"\b",
            lambda m: f"[{m.group()}]",
            f.text,
            flags=re.IGNORECASE,
        )
        print(f"         {highlighted}")
        print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hollow-word pre-audit for argument documents.",
    )
    parser.add_argument("document", type=Path, help="Path to the Markdown document")
    parser.add_argument(
        "--counts", action="store_true",
        help="Summary mode: show word frequencies and line numbers, not full context",
    )
    args = parser.parse_args()

    if not args.document.exists():
        print(f"File not found: {args.document}", file=sys.stderr)
        return 1

    try:
        findings = scan(args.document)
    except (OSError, UnicodeDecodeError) as e:
        print(f"Error reading {args.document}: {e}", file=sys.stderr)
        return 1

    _print_findings(findings, args.document, args.counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
