---
title: Argument Structure Audit — Interpretation Patterns
description: Findings that require interpretation before acting. Each pattern describes a tool output that looks actionable on its face but requires a triage step before repair.
---

# Argument Structure Audit — Interpretation Patterns

Findings that require interpretation before acting. Each pattern describes a tool output that looks actionable on its face but requires a triage step before repair.

---

## 1. `hollow_words.py` — high hit counts on domain vocabulary

**What the tool reports:** A word appearing ×N across the document, with implied questions for each instance.

**The false-positive risk:** `hollow_words.py` fires on surface form. A domain that legitimately uses a flagged word as a technical term will produce a high hit count that is almost entirely clean. Any word that is both a common vague intensifier and a named technical concept in the document's field will exhibit this pattern — the tool cannot distinguish domain use from hollow use.

**Triage rule:** Before treating a high-count word as a pattern, classify the instances into groups:

| Group | Description | Action |
|---|---|---|
| Domain term | Named technical property or established usage in the field | No action — confirm one representative instance, apply to the class |
| Genuine hollow use | Vague intensifier substituting for a specific claim | Repair |
| Named formula component | Part of a defined variable or operator name | No action |

The yield signal is not count but **proportion of genuine hollow uses within the count**. A word appearing many times with few genuine gaps warrants fixing the gaps — the raw count is not the signal.

**Cluster signal:** A concentration of conclusion markers (`therefore`, `necessarily`) or premise markers (`grounded in`, `well-established`) in one section is a prior that `LOGIC-TYPE` or `LOAD-TEST` will fire there. Use the section-level cluster as a drill-down signal, not the global count.

---

## 2. `t1_check.py CONSEQUENCE` — escalation count vs. actionable split

**What the tool reports:** `Escalated=N (T2 review required)` — a single number.

**The false-positive risk:** The escalation count conflates two structurally different classes:

| Class | Description | Expected rate |
|---|---|---|
| Single-sentence items | One sentence; tool cannot distinguish CLAIM-FIRST bypass from missing consequence | High false-positive — definitional, enumerative, legend, and notation items fall here |
| Domain-context items | Multiple sentences; final sentence validity requires domain judgment | Genuine T2 workload — substantive Argument and Scope items |

A document with a large open question register, formal definition tables, or enumeration sub-bullets will produce a high single-sentence escalation count that is structurally expected — these items are not consequence-bearing by design.

**Triage rule:** Run `t1_check.py --verbose` to expand the escalation list with line numbers and slugs. Sort by note type:

- `Single-sentence item — check if CLAIM-FIRST bypass applies` → audit for legend entries, notation tables, and register sub-questions; expect most to be N/A for this check.
- `Consequence validity requires domain context` → these are the genuine T2 items. Count these separately; this is the real review workload.

The actionable number is the domain-context escalation count, not the total.

---

## 3. `query.py mece` — all-Scope sibling set: two distinct diagnoses

**What the tool reports:** A section with N children, 0 Argument, 0 Closure — all Scope.

**The false-positive risk:** This structural pattern has two distinct causes that require different repairs:

| Cause | Description | Repair |
|---|---|---|
| Genuinely missing Argument | The section heading makes an inferential claim; no child carries the derivation | T2 — decide whether to write an explicit Argument child, split the heading, or accept the Scope-only structure |
| TYPE-LABEL mismatch | Argument content is present in one or more children but labeled `Scope` | Mechanical — relabel the mislabeled items; no content change |

**Triage rule:** Before staging a repair, read the body of each Scope child. Ask: does this item derive, justify, or defend the heading claim? If yes — the argument is present, the label is wrong; relabel. If no — the argument is absent; escalate to T2.

The mece tool sees only the label, not the content. A section where every child qualifies the heading but none defends it is a genuine structural gap. A section where a child's body contains a full conditional → consequence chain labeled as Scope is a TYPE-LABEL error. Both look identical in the tool output.

**Indicator:** If the Scope-only section has a heading with an inferential verb and at least one child is long with derivation language in the body, suspect TYPE-LABEL mismatch first — it is the cheaper repair and the more common cause.

---

## 4. `query.py shared` — N≥5 citations: two structurally different node classes

**What the tool reports:** Nodes cited from N distinct sections, flagged at N≥5 for human review.

**The false-positive risk:** The high-citation flag means different things depending on node type:

| Node type | What high citation means | Action |
|---|---|---|
| By-design anchor node | Wide citation is intentional — register entries, shared definitions, and cross-document anchors are designed to be cited broadly; citing sections are acknowledging the anchor, not depending on it argumentatively | No independence analysis required |
| Substantive argument or scope node | Trunk node — multiple sections depend on this claim holding; a retraction or weakening has a blast radius across all citing sections | Independence analysis required: verify that each citing section's argument holds if the trunk node is weakened |

**Triage rule:** Partition the N≥5 list by node role. For anchor nodes (open question entries, definition nodes, cross-document pointers), wide citation is structural bookkeeping — no action required. For substantive argument or scope nodes, the question is: *if this node were retracted, which citing sections would lose their supporting premise?* That is the blast radius for any future edit to the trunk node.

The `refs --target <slug>` command gives the inverted citation list for any specific node — use it to map the blast radius before any edit that touches a trunk node.

---

## 5. `query.py refs` — external dependencies and stale cross-references

**What the tool reports:** Cross-reference targets that do not resolve to any node in the current document graph.

**The false-positive risk:** Not all unresolved references are errors. Two distinct cases:

| Case | Description | Action |
|---|---|---|
| External dependency | Reference to a node in a separate document that exists and is current | Assess whether the dependency is necessary; if the separate document is not yet written, make the referencing item self-contained |
| Stale label | Reference to a node that was renamed, moved, or committed under a different identifier in a previous version | Remove or update — a stale label silently drops the intended cross-reference |

**Triage rule:** For each unresolved reference, determine whether the target document exists and is current. A reference to a planned-but-unwritten section creates an invisible dependency — the argument appears grounded but the grounding is absent. Repair: either make the referencing item self-contained (drop the provenance pointer, keep the mechanism), or add the target document to the active scope.

Stale labels are the harder case because they were once valid — the reference was correct at the time of writing but the target drifted. A `refs` scan after any rename operation is the detection mechanism.

---

## Applying these patterns together

The patterns interact in a fixed triage order:

1. `hollow_words` classification clears argument-signal noise before structural audit.
2. `t1_check --verbose` separates the mechanical TYPE-LABEL failures (direct repair) from the escalation bulk (sort into single-sentence vs. domain-context before sizing T2 workload).
3. `mece` all-Scope signals trigger a content inspection — TYPE-LABEL mismatch first, genuinely missing Argument second.
4. `shared` N≥5 partition separates by-design anchor citations from structural vulnerability candidates (trunk nodes).
5. `refs` unresolved targets separate external dependencies from stale labels — each requires a different resolution.

A finding that looks like a structural defect at the tool output layer may resolve to a label error, a false positive, or a by-design pattern at the content layer. The tool output is the starting point for triage, not the triage result.
