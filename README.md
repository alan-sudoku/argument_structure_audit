# Argument Structure Audit

A structured audit method for structured argument documents. It verifies that a document's argument is correctly encoded — claims are visible, content types are distinct, consequence is explicit, and the document is navigable by a blank AI receiver without full linear parsing.

---

## When to use

The audit is diagnostically useful for documents with **at least two levels of explicit argument hierarchy** — a parent claim with named sub-items at the level below.

**Do not apply to:**
- Flat prose with no definition items or named sub-paragraphs
- Mathematical proofs — premises necessarily precede the conclusion
- Dialectical arguments — claim is deferred until after hypothesis weighing
- Abductive reasoning (troubleshooting guides, incident reports) — lead claim is tentative until diagnosis is complete

---

## Quick start

The audit has two tiers. T1 checks are executable by a blank AI. T2 checks require a human auditor with domain knowledge of the document.

**Step 1 — Human: fill §0**
Open `specification.md` and fill in the §0 parameter table for your document: compliance target, consequence unit, numbered item convention, document class. Note which checks to suspend from the scope-out table.

**Step 2 — Human: copy §0 into the strip**
The strip's §0 contains only the parameters that T1 checks reference directly. Copy those values from Step 1 into `t1_strip.md`. The remaining spec §0 parameters — compliance target definition, failure name, L0/L1 content, audit tier — feed T2 checks and rationale sections; they stay in the spec and are used in Step 4.

**Step 3 — AI: run T1 checks**
Give `t1_strip.md` to a blank AI. It runs: `RC1` → `CONTENT-TYPE` → `CLAIM-FIRST` → `CONSEQUENCE` → `TYPE-LABEL` → `RC2` → `RC3`. Output: a findings table and a repaired document. Items requiring semantic judgment are marked `[Escalated]` for T2 review.

**Step 4 — Human: resolve T2 checks and escalations**
Use `specification.md` — §5 T2 checks, §5.1 decision maps, §6 recovery edge table — to run `MECE`, `LOGIC-TYPE`, `LOAD-TEST`, `HEADING-SYNTHESIS` and resolve any escalated T1 items.

**Step 5 — Generative repairs: use the staging guide**
For repairs that rewrite or reorder prose, use `repair_guide.md` to stage, audit, and commit candidates rather than writing directly to the source document.

---

## Files

| File | Role |
| :--- | :--- |
| `t1_strip.md` | Start here — the T1 execution instrument; hand to a blank AI with §0 filled |
| `specification.md` | Canonical reference — full check definitions, T2 checks, decision maps, phase ordering, recovery edges |
| `repair_guide.md` | Workflow for staging generative repairs before committing to the source document |
| `retraction_log.md` | Log of retracted and amended check definitions; §Rxx entries (removed) and §Axx entries (precision amendments) |
| `t1_checklist.md` | Verify the strip remains self-sufficient and executable after any modification |
| `assess_specification.md` | Adversarial quality gate — run when proposing changes to the specification |
| `assess_usage.md` | Post-execution probe — assess how well an AI processed and applied the methodology |

---

## Checks

| Check | Tier | What it tests |
| :--- | :--- | :--- |
| `RC1` | T1 | Heading hierarchy is present and correctly structured |
| `CONTENT-TYPE` | T1 | Arguments and Closures are visually distinct from Claims and Scope |
| `CLAIM-FIRST` | T1 | First sentence of every definition item is a standalone claim |
| `CONSEQUENCE` | T1 | Last sentence of every sub-item states a consequence unit |
| `TYPE-LABEL` | T1 | Every sub-item label identifies content type using `*[Type] ([Topic]):*` format |
| `RC2` | T1 | Typed sub-items are list items, not flat paragraphs |
| `RC3` | T1 | Numbered bold items are explicitly identified as Claims |
| `MECE` | T2 | Sibling items are mutually exclusive and collectively exhaustive |
| `LOGIC-TYPE` | T2 | Horizontal logic within each sibling group is consistent and explicit |
| `LOAD-TEST` | T2 | Every block defines, constrains, or opens; every sentence in a passing block is load-bearing |
| `HEADING-SYNTHESIS` | T2 | Each heading synthesises its children; document is reconstructable from headings alone |

T1 checks are applicable by any blank AI receiver. T2 checks require a human auditor with domain knowledge of the document under audit — blank-AI application of T2 checks produces inconsistent results.
