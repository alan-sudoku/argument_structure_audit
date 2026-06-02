---
title: T1 Execution Strip
description: AI template to apply the T1 run phase of the argument structure audit framework. See specification.md for more guidelines.
---

# Argument Structure Audit — T1 Execution Strip

*v2.0 · Retraction log: [retraction_log.md](retraction_log.md)*

*Receiver: blank AI — an AI with no prior exposure to this methodology; normal language and document competence assumed. Role: structural auditor — apply the T1 checks defined in this document to the target document specified in §0, produce the output defined in the Execution Protocol, and use only what this document defines. Do not import external methodology or domain knowledge. Scope: T1 checks only (`CONTENT-TYPE`, `CLAIM-FIRST`, `CONSEQUENCE`, `TYPE-LABEL`, `RC2`–`RC3`). T2 checks (`MECE`, `LOGIC-TYPE`, `LOAD-TEST`, `HEADING-SYNTHESIS`) require a human domain-expert auditor — do not apply them from this document.*

---

## Execution Protocol

0. **Node enumeration (pre-T1):** Before binding §0 parameters, run `python tools/structure_depth.py <document> --annotate --section <target>`. Any line with `has_inline: true` and `inline_count >= 2` contains hidden sub-items — split those items into separate structural nodes before applying T1. T1 applied to an unsplit inline item audits one node when two or more exist; the audit will appear complete but will not be.
1. Bind §0 parameters before any check. All `[value — from §0]` references resolve here.
2. Check the scope-out table. If the document class matches, suspend the listed checks before starting.
3. Apply checks in this order: `RC1` → `CONTENT-TYPE` → `CLAIM-FIRST` → `CONSEQUENCE` → `TYPE-LABEL` → `RC2` → `RC3`.
4. After each repair, consult the T1 recovery edge table.
5. Record inapplicable checks as **N/A**, not as failures. State which N/A guard applies (N/A guard = the *N/A if:* or *Suspend if:* condition listed under the check that makes it inapplicable).
6. If a §0 parameter has no value (the template placeholder `[...]` is unfilled), do not infer it from the target document. Mark all checks that reference that parameter as `[Escalated]` with the note `§0 parameter not provided`.

*Output format:* produce two sections: (1) a findings table with columns `Check | Result | Notes` — the Result cell must contain exactly one of: `[Pass]`, `[Fail]`, `[N/A]`, `[Escalated]`; record pending T2 items and N/A guards in the Notes column; (2) the repaired document with all T1 repairs applied inline.

*T2-review flag format:* when a repair instruction says to "flag" an item for domain-expert confirmation, apply both: (a) in the findings table Notes column, record the item with the marker `[T2 review pending — <check name>: <description>]` and a one-phrase description of what requires confirmation (e.g. `[T2 review pending — CLAIM-FIRST: rewrite orientation]`); (b) in the repaired document inline, append the marker `*[T2 review pending]*` immediately after the repaired item, on the same line. This makes T2-pending items locatable from either the findings table or the repaired document without requiring a full cross-read.

---

## §0 — Parameters

*Structural prerequisite:* This audit is diagnostically useful only for documents with at least two levels of explicit argument hierarchy — a parent claim with named sub-items. Flat prose documents satisfy most T1 checks trivially via N/A and produce no actionable findings; do not apply this strip to documents without hierarchy.

| Parameter | Value for this audit |
| :--- | :--- |
| **Document under audit** | `[filename]` |
| **Compliance target** | `[e.g. a named standard]` |
| **Consequence unit** | `[what a consequence means for this document class — e.g. protocol instruction, design constraint, rule application]` |
| **Document-level convention for numbered items** | `[e.g. numbered bold items are Claims; numbered items are steps; or N/A]` |
| **Section-level document class overrides** | `[Optional. For hybrid documents only: list sections where a different N/A rule applies. If uniform, write N/A.]` |

---

## Scope-Out Table

*Classification is a human pre-step.* Document class is determined by the audit initiator using the full specification's scope-out table before this strip is executed. The result is recorded in §0 "Section-level document class overrides." If §0 has been pre-filled, apply those overrides directly — do not reclassify. If §0 is blank, use this table as the fallback reference.

Documents in these classes produce systematic false findings from the listed T1 checks. Suspend those checks for the whole document unless §0 defines a section-level override.

| Document class | T1 checks to suspend | Reason |
| :--- | :--- | :--- |
| Mathematical proofs | `CLAIM-FIRST`, `CONSEQUENCE` | Premises necessarily precede the conclusion — `CLAIM-FIRST` flags every premise; `CONSEQUENCE` requires a consequence unit at each step, which is only available at the theorem. |
| Dialectical arguments — documents that weigh competing hypotheses before concluding | `CLAIM-FIRST`, `CONSEQUENCE` | Lead sentences are legitimately conditional or comparative, not standalone claims; `CONSEQUENCE` would require committing to a conclusion before the weighing is complete. |
| Abductive reasoning — troubleshooting guides, incident reports | `CLAIM-FIRST`, `CONSEQUENCE` | The lead claim is tentative and qualified by incomplete evidence; definitive boundary statements are unavailable until diagnosis is complete. |

`CONTENT-TYPE`, `TYPE-LABEL`, `RC2`, `RC3` are not suspended for any of these classes.

---

## §1 — Content-Type Taxonomy

Required for `CONTENT-TYPE` and `TYPE-LABEL` execution. Four types; every sub-item carries exactly one.

| Type | Function | Label form |
| :--- | :--- | :--- |
| **Claim** | States what must hold — the boundary condition | Bold heading or numbered item lead |
| **Scope** | States what the claim does or does not reach — includes examples, analogies used as structural illustrations, and application instantiations that bound the claim's range | `*Scope (topic):*`, `*Scope (example — topic):*`, `*Scope (analogy — topic):*` |
| **Argument** | Justifies why the claim holds | `*Argument (topic):*` |
| **Closure** | Records why an attack or alternative was rejected | `*Closure (topic):*` + `§Cxx ` reference |

**Failure signal:** Claim and Argument at the same visual weight — receiver cannot triage without reading the full block.

**Structural terms used in checks:**

| Term | Definition |
| :--- | :--- |
| **Definition item** | A labeled or numbered item that opens a definitional block — any `###`-level section body, numbered bold item, or paragraph opened by a typed label in `*[Type] ([Topic]):*` format. `CLAIM-FIRST` applies to the first sentence of each. |
| **Sub-item** | A `-` list item nested under a Definition item or section body. `CONSEQUENCE`, `TYPE-LABEL`, and `RC2` apply at this level. First `-` list level under a heading body; nested `-` list items one level deeper are also in scope. |

---

## Checks

### `RC1` — Heading Hierarchy · Precondition Gate

Apply before `CONTENT-TYPE` and `CLAIM-FIRST`.

- *Pass:* `##`/`###` markers present, correctly hierarchical (no skipped levels), no section body reachable only by reading a prior section.
- *Fail:* Repair heading structure first. When repairing a skipped level, promote the child in preference to demoting the parent — parent demotion propagates structural changes to sections outside the section currently under repair. Do not apply `CONTENT-TYPE` or `CLAIM-FIRST` to affected sections until repaired. `RC1` failure is local — unaffected sections proceed.
- *Escalation:* If the dependency between sections is narrative (a section's meaning requires understanding a prior section's content) rather than structural (a heading level is missing or skipped), escalate to T2 — structural repair cannot resolve semantic dependencies. If you cannot determine whether a dependency is narrative or structural, treat it as potentially narrative and escalate to T2.

---

### `CONTENT-TYPE` · T1

- *Pass:* Arguments and Closures are visually distinct from Claims and Scope. Distinctness is established by label form (§1): Claim uses bold heading or numbered lead; Scope, Argument, and Closure each use a `*[Type] (topic):*` italic label. If §1 label forms are present and correct, the pass condition is satisfied.
- *N/A:* None — applies to all document classes in this strip.
- *Repair procedure:*
  1. Is visual separation of content types already present? → **Pass.**
  2. Separation absent; are content types identifiable from structural position alone (without domain knowledge)? → **T1 repair:** move Arguments to labeled sub-bullets; move Closures to the retraction log with pointer. *Retraction log: a dedicated `-` list section headed `*Retraction log:*`, placed at the end of the affected section (the innermost heading level — `###` if present, otherwise `##` — that contains the item being repaired). Each Closure entry is recorded with its original location (the containing heading title and a one-phrase item description, formatted as `[Heading title — item description]`) and a `§Cxx` reference code (e.g. `§C01`, `§C02`). At the original Closure location, leave a cross-reference pointer in the form `[→ §C01]` so the connection is traceable.* Then check the T1 recovery edge table.
  3. Separation absent; content types NOT identifiable from structure (domain context required)? → **Escalate to T2 reviewer.** Record the item as pending T2 review; do not make a pass/fail judgment. Then check the T1 recovery edge table.

*Escalation note:* Detecting missing separation is T1 (syntactic); identifying which items are Arguments vs. Claims in an unlabelled document may require semantic judgment — escalate the repair action, not the detection step.

---

### `CLAIM-FIRST` · T1

- *Pass:* First sentence of every Definition item is a standalone claim — a sentence the receiver can hold without reading further and be correctly oriented.
- *N/A if:* Document consists entirely of flat prose with no Definition items.
- *Suspend if:* Document class is in the scope-out table.
- *Escalation:* If determining whether the lead sentence is a standalone claim or a specification (a sentence that qualifies or conditions the claim rather than stating it) requires domain context not present in the document, escalate to T2 — do not default to pass; record as pending T2 review.
- *Repair:* Rewrite to claim-first; move specification to second sentence. AI-generated rewrites are T2-review candidates — flag all repaired items using the T2-review flag format defined in the Execution Protocol.
- *Failure patterns:* leads that fail this check —
  - "Under this framing..." → mid-argument entry, not a claim
  - "Whether this is the case..." → open question, not a claim
  - "For all [variable]..." → specification before claim
  - *Corrected pattern:* state the claim — the boundary condition it establishes — first; move the qualifier or specification to the second sentence.

---

### `CONSEQUENCE` · T1

- *Pass:* Last sentence of every sub-item states a consequence unit `[from §0]`.
- *Valid consequence unit forms:* (a) rules out $X$ — states what is no longer in scope or permissible; (b) permits $X$ that would otherwise be questioned — explicitly licenses a non-obvious action or inference; (c) binds the receiver to action $Y$ — names a required next step; (d) names an open question the receiver must hold — identifies a boundary at which the current document stops.
- *Invalid form:* Names a follow-on topic without stating a conclusion (pointer without consequence — e.g. "this will be addressed in the next section").
- *Precondition bypass:* If the `CLAIM-FIRST` lead claim already fully states the receiver consequence and contains one of the four valid consequence forms (a–d), `CONSEQUENCE` is satisfied by that sentence — do not add a duplicate sentence. A standalone claim that does not contain a consequence form does not satisfy the bypass.
- *N/A if:* Document has no sub-items (no `-` list items under heading bodies). Typed items formatted as flat paragraphs (not yet `-` list items) are also N/A here — they do not meet the sub-item definition and will be re-examined after `RC2` via the T1 recovery edge.
- *Suspend if:* Document class is in the scope-out table.
- *Escalation:* If determining whether the final sentence is in one of the valid consequence forms (a–d) — i.e. whether it rules out, permits, binds, or names an open question — requires domain context not present in the document, escalate to T2 — do not default to pass.
- *Repair:* Add one consequence sentence at the end of each sub-item. If `CLAIM-FIRST` already covers the consequence, confirm satisfied and proceed. If the consequence cannot be derived from the item's content alone without domain knowledge — i.e. you cannot determine what is ruled out, permitted, or required without external context — escalate to T2; do not generate a speculative sentence. AI-generated consequence sentences are T2-review candidates — flag all added sentences using the T2-review flag format defined in the Execution Protocol.

---

### `TYPE-LABEL` · T1

- *Pass:* Every sub-item label identifies content type using `*[Type] ([Topic]):*` format. Types: Claim, Scope, Argument, Closure. The pass condition for the topic field is the label function test: covering the body, a receiver can determine relevance and decide to skip from the label alone. Word count is not a pass condition — existing labels are assessed against skippability, not length. This is a syntactic check — it verifies label format only, not whether the label's type accurately describes the item's content. Semantic label accuracy (wrong type assigned to an item) requires T2 review.
- *Failure detection:* The lead word must be one of the four types — Claim, Scope, Argument, Closure — regardless of how accurately the label classifies the item's content. Two failure sub-types to detect explicitly: (a) topic labels that name a subject (e.g. `*Typed DAG:*`); (b) pseudo-functional labels that name a presentation modality or check concept (e.g. `*Example:*`, `*Biological model:*`, `*Analogy:*`, `*Consequence:*`) — these look like type labels because they classify content, but the lead word is not in the taxonomy. Both sub-types fail this check.
- *Format variants:* Syntactic variants that do not match `*[Type] ([Topic]):*` exactly (wrong delimiter, wrong italics pattern, wrong bracket type) — treat as Fail; repair by relabeling. Format ambiguity does not escalate to T2.
- *N/A if:* Document has no sub-items. Typed items formatted as flat paragraphs are also N/A here — they will be re-examined after `RC2` via the T1 recovery edge.
- *Repair:* Relabel using the exact `*[Type] ([Topic]):*` format. When generating a new topic phrase from scratch, use a 1–5 word phrase naming the subject of the item, extracted from the item's lead sentence (e.g., `*Argument (cost implications):*`, `*Scope (quantifier range):*`) — this is a generation heuristic for new labels only, not a validity constraint on existing labels. Flag all relabeled items as T2-review candidates using the T2-review flag format defined in the Execution Protocol. Confirm topic wording with domain expert before treating as settled. If numbered items are implicitly Claims, resolve the repair strategy from the §0 'Document-level convention for numbered items' parameter: if §0 specifies that numbered items are Claims, prefer a document-level convention note; if §0 says N/A or does not classify numbered items, apply explicit `*Claim:*` leads. If classifying numbered items requires domain judgment, escalate the repair strategy to T2. Place any convention note as the opening line of §0; use the top of the document only if §0 is absent.

*Apply after `CONTENT-TYPE` — labeling mixed-type content creates false precision.*

---

### `RC2` · T1 — List Structure for Sub-Items

- *Pass:* All typed sub-items (`*[Type] (...):*`) are `-` list items, not flat paragraphs separated by blank lines. Markdown list markers `*` and `+` are equivalent to `-` for this check — the pass condition is list structure, not specific marker.
- *N/A if:* Document has no sub-items.
- *Identification:* A flat paragraph is a candidate for conversion if and only if it opens with a `*[Type] ([Topic]):*` label — the type label is the syntactic marker that identifies it as a misformatted sub-item rather than normal prose. Flat paragraphs that do not open with a type label are normal body prose and are not in scope for `RC2`. Do not convert unlabelled paragraphs.
- *Repair:* Convert flat paragraph sub-items (identified above) to `-` list items under their parent heading or Definition item.

---

### `RC3` · T1 — Numbered Item Type Convention

- *Pass:* Numbered bold items (e.g., **1.** Text) are explicitly identified as Claims — either by a document-level convention note or by explicit `*Claim:*` lead on each. The check applies to any numbered sequence (Arabic, Roman, alphabetical) when items are bolded — the trigger is the combination of numbering and bold, not Arabic numeral format specifically. If numbered bold items are not Claims in this document class, the convention must state what they are, not only that they are not Claims. Plain numbered items (e.g., `1. Text`) are governed by the §0 "Document-level convention for numbered items" parameter — resolve from §0 before applying this check.
- *N/A if:* Document contains no numbered items.
- *Repair:* Add a convention note, or apply `*Claim:*` label to each numbered item. Resolve the repair strategy from the §0 'Document-level convention for numbered items' parameter: if §0 specifies that numbered bold items are Claims, prefer a convention note; if §0 says N/A or does not classify them, apply explicit `*Claim:*` leads. If determining which numbered items are Claims requires domain judgment, escalate the repair strategy to T2. Convention note text and `*Claim:*` leads generated by a blank AI are T2-review candidates — flag using the T2-review flag format defined in the Execution Protocol. Place any convention note as the opening line of §0; use the top of the document only if §0 is absent.

---

## T1 Recovery Edges

After any T1 repair, check whether it triggers re-examination of another T1 check.

| Recovery edge | Trigger | Action |
| :--- | :--- | :--- |
| `CONTENT-TYPE` → `CLAIM-FIRST` | `CONTENT-TYPE` repair (a) moves Arguments to new sub-bullets creating net-new items, or (b) relocates content within an existing item changing its lead sentence | Re-examine `CLAIM-FIRST` for all affected sub-items — each must open with a standalone claim |
| `CONTENT-TYPE` → `CONSEQUENCE` | `CONTENT-TYPE` repair (a) moves Arguments to new sub-bullets creating net-new items, or (b) relocates content within an existing item changing its final sentence | Re-examine `CONSEQUENCE` for all affected sub-items — each must close with a valid consequence unit (forms a–d above) |
| `TYPE-LABEL` → `CONTENT-TYPE` | Label function reveals an item contains mixed content types | Re-examine `CONTENT-TYPE` for that item |
| `RC2` → `CONSEQUENCE` | `RC2` repair converts a typed flat-paragraph sub-item to a `-` list item — the item previously N/A'd `CONSEQUENCE` because it was not a list item | Re-examine `CONSEQUENCE` for each converted item — each must close with a valid consequence unit (forms a–d above) |
| `RC2` → `TYPE-LABEL` | `RC2` repair converts a typed flat-paragraph sub-item to a `-` list item — the item previously N/A'd `TYPE-LABEL` because it was not a list item | Re-examine `TYPE-LABEL` for each converted item — verify `*[Type] ([Topic]):*` format is present |

*T2 recovery edges (e.g. `MECE` → `CLAIM-FIRST`, `CLAIM-FIRST` → `MECE`) are not in scope for this strip. They apply when a T2 auditor runs the full template.*
