---
title: T1 Execution Strip — Verification Checklist
description: Verification checklist after t1_strip.md run.
---

# T1 Execution Strip — Verification Checklist

*Purpose: targeted yes/no verification of known failure modes in [t1_strip.md](t1_strip.md) . Use after any revision to the strip. Replaces open-ended blank-AI assessment (archived) for ongoing maintenance.*

*How to use: for each item, read the referenced location in the strip and answer yes or no. A single No is a gap — repair before releasing the strip version.*

---

## 0 — Receiver Specification

The preamble must define who is executing and under what operating constraint before the first check runs.

- [ ] **Preamble** — defines blank AI as an AI with no prior exposure to this methodology and normal language and document competence assumed
- [ ] **Preamble** — includes role instruction (structural auditor), task (apply T1 checks to §0 target, produce Execution Protocol output), and operating constraint (use only what this document defines; do not import external methodology or domain knowledge)

---

## 1 — Terminology in Executable Logic

Terms that appear in pass conditions, N/A guards, repair instructions, or escalation clauses must be resolvable without external context.

- [ ] **Execution Protocol step 5** — "N/A guard" is defined at point of use via parenthetical: `(N/A if: or Suspend if: condition listed under the check)`
- [ ] **RC1 fail instruction** — uses "section currently under repair" (not "current audit scope" or any other unanchored scope term)
- [ ] **RC1 escalation clause** — includes a default for when narrative vs. structural dependency cannot be determined
- [ ] **CONTENT-TYPE repair step 2** — "affected section" is defined as the innermost heading level (`###` if present, otherwise `##`)
- [ ] **CONTENT-TYPE repair step 2** — "original location" in the retraction log entry is defined as `[Heading title — item description]`
- [ ] **Sub-item definition** — depth described in plain structural terms; no scheme-derived labels (e.g. `L3`, `L4`) that imply a numbering scheme with undefined predecessors
- [ ] **§1 taxonomy Scope row** — function description covers examples, analogies used as structural illustrations, and application instantiations; label form column includes `*Scope (example — topic):*` and `*Scope (analogy — topic):*` pattern variants

---

## 2 — Escalation Completeness

Every check that requires semantic judgment must name the condition that triggers escalation and provide an explicit path.

- [ ] **RC1** — escalation path present for narrative dependency; default fallback present for ambiguous cases
- [ ] **CONTENT-TYPE** — escalation path present when content types are not identifiable from structure alone
- [ ] **CLAIM-FIRST** — escalation path present when standalone claim vs. specification requires domain context
- [ ] **CONSEQUENCE** — escalation path present when valid consequence form requires domain context
- [ ] **RC3** — escalation path present when classifying numbered items requires domain judgment

---

## 3 — Repair Specification

Every repair must produce deterministic output structure. Generative content must be routed to T2 via the flag mechanism.

- [ ] **Execution Protocol** — T2-review flag format is defined once, in full (findings table marker + inline document marker)
- [ ] **CLAIM-FIRST repair** — references "T2-review flag format defined in the Execution Protocol" (no inline format redefinition)
- [ ] **CONSEQUENCE repair** — references "T2-review flag format defined in the Execution Protocol"
- [ ] **TYPE-LABEL repair** — references "T2-review flag format defined in the Execution Protocol"; includes topic wording confirmation instruction
- [ ] **RC3 repair** — references "T2-review flag format defined in the Execution Protocol"
- [ ] **RC2 identification criterion** — type label (`*[Type] ([Topic]):*`) is named as the sole syntactic marker for conversion eligibility
- [ ] **RC2 identification criterion** — explicitly states unlabelled flat paragraphs are out of scope
- [ ] **RC2 repair** — references "sub-items identified above" (repair scope bounded to identified candidates only)
- [ ] **RC3 repair** — placement anchor specified: opening line of §0; top of document if §0 absent
- [ ] **TYPE-LABEL failure detection** — strip explicitly names pseudo-functional labels (lead word outside Claim/Scope/Argument/Closure) as a distinct failure sub-type; names at least one example (`*Example:*`, `*Biological model:*`, `*Analogy:*`, `*Consequence:*`)

---

## 4 — Output Format

The executing AI must be able to produce a complete, structured output without inferring format.

- [ ] **Execution Protocol** — two output sections specified: findings table and repaired document
- [ ] **Execution Protocol** — findings table columns specified: `Check | Result | Notes`
- [ ] **Execution Protocol** — Result values enumerated: `[Pass]`, `[Fail]`, `[N/A]`, `[Escalated]`
- [ ] **Execution Protocol** — T2-review inline marker specified: `*[T2 review pending]*`
- [ ] **Execution Protocol** — T2-review table marker specified: `[T2 review pending — <check name>: <description>]`

---

## 5 — Execution Order Coverage

Assumed preconditions must be covered by N/A guards or recovery edges — not left exposed.

- [ ] **CONSEQUENCE** — explicit N/A guard for flat-paragraph sub-items (not yet `-` list items)
- [ ] **TYPE-LABEL** — explicit N/A guard for flat-paragraph sub-items
- [ ] **T1 Recovery Edge table** — `RC2 → CONSEQUENCE` edge present
- [ ] **T1 Recovery Edge table** — `RC2 → TYPE-LABEL` edge present
- [ ] **T1 Recovery Edge table** — edges form a DAG: no check triggers a chain that returns to itself (verify by tracing each edge forward — no path should reach its own source). Current edges: `TYPE-LABEL → CONTENT-TYPE`, `CONTENT-TYPE → CLAIM-FIRST`, `CONTENT-TYPE → CONSEQUENCE`, `RC2 → CONSEQUENCE`, `RC2 → TYPE-LABEL`. If any new edge is added, re-trace all paths from its source before accepting.
- [ ] **Execution Protocol step 6** — blank §0 parameters: AI must not infer unfilled placeholders; all checks referencing that parameter are marked `[Escalated]` with note `§0 parameter not provided`

---

## 6 — Scope-Out Table

- [ ] **Scope-out table** — opens with classification ownership note: document class is a human pre-step using the spec; §0 overrides take precedence; table is fallback only
- [ ] **Scope-out table** — lists only T1 checks in the "T1 checks to suspend" column (no T2 checks: no `MECE`, `LOGIC-TYPE`, `HEADING-SYNTHESIS`)
- [ ] **Scope-out table** — `CONTENT-TYPE`, `TYPE-LABEL`, `RC2`, `RC3` explicitly noted as not suspended for any class

---

## 7 — Cross-Document Consistency

- [ ] **Spec (`specification.md`) AI usage modes** — references [t1_strip.md](t1_strip.md)  (correct filename)
- [ ] **Repair guide (`repair_guide.md`) companion statement** — references [t1_strip.md](t1_strip.md)  (correct filename)
