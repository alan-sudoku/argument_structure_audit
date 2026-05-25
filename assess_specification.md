# Argument Structure Audit — Specification Assessment Prompt

**Role:** 
Formal Logic Auditor. Adversarial, surgical. No flattery, no filler, no introductory or concluding remarks. Output only the technical audit.

*Claim (task):* Perform a System Logic Verification of `specification.md` by answering the six assessment questions below. You have no prior context. Treat this as a blank receiver—navigate from headings, assess logic from structure.

**Method:**
Treat the template as a formal specification for a state-machine. Prioritize the detection of logical collisions (contradictory constraints), circular dependencies in the recovery edges, and determinism failures in the T1 pass conditions.
---

## Context

`specification.md` is a reusable audit checklist for structured argument documents. It defines nine structural checks (`CONTENT-TYPE`–`HEADING-SYNTHESIS`) and two AI readability checks (`RC2`–`RC3`), organised into four application phases. `RC1` is a Phase 1 precondition gate — it verifies heading hierarchy encoding before Phase 1 checks begin and is not a compliance check. Its stated goals are:

1. Make documents more logically structured and cleanly formatted when applied
2. Be fully satisfiable — a well-formed document should be able to pass all checks simultaneously
3. Be necessary — every check should catch failures that no other check covers

The template claims to operationalize the **Minto Pyramid Principle** (claim-first, MECE, horizontal logic) and extend it with content-type taxonomy (Claim/Scope/Argument/Closure) and AI readability requirements.

*Scope (what is not in scope):* Assess only the specification itself as a reusable instrument — do not assess any document it has been applied to.

---

## Document to assess

File: `specification.md`

Read in this order to minimise linear parsing:
1. §0 Parameterisation — understand what the template requires as input
2. §5 Structural Audit Checklist — the summary table for orientation; per-check `###` sections for full pass conditions, scope notes, N/A guards, and repair actions
3. §6 Application Priority — the four-phase sequencing, `RC1` precondition gate, Mermaid flowchart, and recovery edge table
4. §4.4 Authoring Pipeline — the distinction between Minto baseline and compliance augmentations
5. §3 Content-Type Taxonomy — the four content types and their label forms
6. §8 AI Readability Checklist — `RC2`–`RC3` and their relationship to `CONTENT-TYPE`–`HEADING-SYNTHESIS`

---

## Output format

Respond in five sections, one per assessment question. Use the content-type label format from the template: lead each finding with `*Claim (...):*`, `*Scope (...):*`, or `*Argument (...):*`. End each section with one sentence stating the net consequence for the template — what action (if any) the assessment finding requires.

Do not summarise the template back to the reader. State verdicts and findings directly.

---

## Assessment Question 1 — Measurability

*Claim (question):* Can applying the template produce a measurably more logical and more cleanly formatted document?

Assess:

- **Operationalizability**: Are the pass conditions for each check (`CONTENT-TYPE`–`HEADING-SYNTHESIS`) precise enough to produce consistent results across different auditors applying them independently? Identify any check whose pass condition is ambiguous — where two auditors could reach opposite verdicts on the same block of text.
- **Before/after testability**: Does each check produce a documentable repair — a specific, bounded change to the document? Or do any checks require holistic judgment that cannot be attributed to a single repair action?
- **Conflict risk**: Could applying two checks to the same block produce conflicting edits? Identify any pair of checks whose repair actions could contradict each other when applied to the same content.
- **Tier assignment**: Is the T1/T2 tier assignment defensible for each check? For `CLAIM-FIRST` and `CONSEQUENCE`, the T1 basis separates detection (locating the structural position of the lead or final sentence) from pass-condition evaluation (determining whether that sentence qualifies as a standalone claim or valid consequence form). Assess whether the detection step is genuinely free of semantic judgment — does identifying *which* sentence is the standalone claim or consequence already require domain knowledge? Also assess whether the escalation notes on `CONTENT-TYPE`, `CLAIM-FIRST`, and `CONSEQUENCE` correctly identify the mandatory escalation boundary, or whether those checks should be fully reclassified to T2. Identify any remaining T1 check with hidden semantic requirements, or any T2 check mechanical enough to be T1.
- **Two-level `LOAD-TEST` tier consistency**: `LOAD-TEST` is a single T2 check with two mandatory sub-steps — block pass (paragraph granularity) and sentence pass (sentence granularity). The sentence pass operates at a finer granularity that is closer to mechanical T1 work. Assess whether the T2 label is consistently defensible for both sub-steps, or whether the sentence pass introduces a tier boundary ambiguity that a blank AI could exploit to apply it without domain judgment.

Output for Q1: verdict (yes / partially / no), then one row per check with a consistency rating (high / medium / low) and a one-line rationale for any medium or low rating.

---

## Assessment Question 2 — Satisfiability

*Claim (question):* Can a real structured argument document simultaneously satisfy all `CONTENT-TYPE`–`HEADING-SYNTHESIS` and `RC2`–`RC3` checks?

Assess:

- **Logical tension**: Are any two checks in logical tension — where satisfying one makes satisfying another harder or impossible? Pay particular attention to: `CLAIM-FIRST` (lead claim) vs. `HEADING-SYNTHESIS` (heading synthesises children); `CONSEQUENCE` (consequence sentence) vs. `LOAD-TEST` sentence pass (every sentence load-bearing); `MECE` (MECE) vs. `LOGIC-TYPE` (horizontal logic).
- **`CLAIM-FIRST`↔`HEADING-SYNTHESIS` — merge resolution**: Does the `HEADING-SYNTHESIS` merge instruction resolve the `CLAIM-FIRST`/`HEADING-SYNTHESIS` tension, or does it introduce a new satisfiability constraint — specifically, does merging an absorbed child risk violating `MECE` exhaustiveness by reducing the sibling set below what the parent claim requires?
- **`CLAIM-FIRST`↔`HEADING-SYNTHESIS` — loop termination**: Does the loop termination argument hold for both exit paths? Assess whether Path A (differentiation — child adds a scope qualifier or sub-condition) is truly terminal: can adding a sub-condition alter that child's logical contribution to the sibling set in a way that requires `MECE` exhaustiveness re-evaluation, re-entering the loop via a different path despite formally exiting via Path A?
- **`LOAD-TEST` two-level application and Phase 3 ordering constraint**: The template places an explicit ordering constraint at Phase 3 entry: `CONSEQUENCE` runs before `LOAD-TEST`, and `CONSEQUENCE` sentences and `CLAIM-FIRST` lead sentences are exempt from the sentence pass by definition. Assess whether this constraint fully resolves the `CONSEQUENCE`/`LOAD-TEST` tension, or whether edge cases remain — for example, a block where the `CONSEQUENCE` sentence is the only sentence that causes the block to pass the block pass. Does the exemption create a gap in `LOAD-TEST` coverage for such blocks?
- **Structural inapplicability — N/A guard coverage**: Are there document classes or structural configurations where a check has no valid target and the check cannot be applied because the required structure is absent? The template provides explicit `N/A if:` guards on `CLAIM-FIRST`, `MECE`, `LOGIC-TYPE`, `CONSEQUENCE`, `LOAD-TEST`, `HEADING-SYNTHESIS`, `TYPE-LABEL`, `RC2`, and `RC3` — assess whether these guards correctly cover all flat-topology and skeleton-document cases, or whether there are document configurations where inapplicability is not handled and a check would incorrectly register as a failure.
- **Structural inapplicability — MECE hybrid document scope**: `MECE` carries an explicit N/A guard for procedural reference instruments (documents where parent nodes are navigation topics rather than propositional claims). Assess whether this guard is correctly scoped for hybrid documents — documents that contain both a procedural section (topic headings, no bounding claim) and an argumentative section (Minto-structured claims with a verifiable parent claim). Would such a document receive a full `MECE` N/A or a scoped one, and does the template provide sufficient instruction to distinguish these cases?
- **Proportionality**: Is the total check burden proportionate for documents of typical size and complexity? Estimate the minimum number of distinct repair passes required on a document that fails most checks.

Output for Q2: verdict (fully satisfiable / satisfiable with constraints / unsatisfiable), identification of any tension pairs with a one-line diagnosis, and any structural inapplicability cases.

---

## Assessment Question 3 — Criteria trimming

*Claim (question):* Does the template carry any checks that are redundant, underdefined, or overconstrained — checks that should be merged, removed, or scoped down?

Assess each of the following candidates:

- **`CLAIM-FIRST` vs. `MECE`/`LOGIC-TYPE`**: `CLAIM-FIRST` requires Minto compliance (inverted pyramid). `MECE` (MECE) and `LOGIC-TYPE` (horizontal logic) are also Minto principles. §4.4 states that `CLAIM-FIRST`, `MECE`, `LOGIC-TYPE` are the Minto baseline. If a document is already Minto-compliant, `MECE` and `LOGIC-TYPE` are pre-satisfied. Does `MECE`/`LOGIC-TYPE` add independent audit value beyond confirming Minto compliance, or are they redundant for any document written from Minto?
- **`HEADING-SYNTHESIS` per-heading vs. document-level pass condition**: v2 consolidates the former `HEADING-SCAN` check into `HEADING-SYNTHESIS` as a document-level pass condition — a second pass applied after all per-heading passes are complete. Assess whether the two pass conditions are genuinely independent failure modes. Can a document where every heading individually synthesises its children still fail the document-level three-target reconstructability test (central claim, L2 claims, open questions)? Or does per-heading synthesis guarantee document-level reconstructability, making the document-level condition redundant?
- **`RC1` as gate vs. gap — audit record visibility**: Does the Phase 1 gate placement make `RC1` failures visible in the audit record, or does it create a class of failure that is repaired silently without a logged result? Heading encoding failures caught by `RC1` are no longer recorded in the §7 self-compliance check — assess whether the gate placement preserves auditability.
- **`RC1` as gate vs. gap — pending state resolution**: The gate explicitly excludes locally-failed sections from the `HEADING-SYNTHESIS` document-level pass condition until repaired, with an instruction to record these sections as pending in the audit log. If a local `RC1` failure is never repaired, does the document-level pass remain permanently incomplete? Does the template provide a closing condition — a point at which the pending state resolves to either a logged pass or a logged failure — or does the pending status leave the audit open-ended with no defined resolution path?
- **`RC1` vs. `HEADING-SYNTHESIS` dependency**: `RC1` verifies that heading markers are present and correctly hierarchical. `HEADING-SYNTHESIS` (document-level pass condition) depends on the heading structure being well-formed. With `RC1` as a Phase 1 gate, the dependency is now structural rather than annotated. Does the gate placement guarantee that `HEADING-SYNTHESIS` never runs on malformed heading structure, or are there edge cases — for example, locally correct headings in one section and missing hierarchy in another — where `HEADING-SYNTHESIS` could run on a section that RC1 would flag?
- **`MECE` ME scope note**: The template's `MECE` includes a clarification that mutual exclusivity applies to proposition coverage, not inferential dependency — deductive chains (`LOGIC-TYPE`) do not violate ME by structure, only by writing failure. Does this clarification correctly exempt deductive chains from ME scrutiny, or does it create a loophole where genuine content overlap in a poorly written deductive chain (where B substantially restates A rather than advancing the argument) goes unchallenged?
- **`MECE` CE scope note — relabelling loophole**: Does the CE scope note correctly constrain collective exhaustiveness for deductive chains, or does it create a relabelling loophole — where any final sibling can be designated as the conclusion item to satisfy CE without genuinely resolving the parent claim? Assess whether the note requires an additional constraint on what qualifies as a conclusion item.
- **`MECE` CE scope note — entailment constraint vs. fallback**: The CE scope note requires that the conclusion item logically entail the parent claim — a conclusion that does not follow from the preceding premises fails CE. Assess whether this constraint is consistent with the CE domain-knowledge fallback: when exhaustiveness cannot be evaluated from document-internal content, the repair action is to narrow the parent claim rather than expand the sibling set. Does requiring logical entailment mean a sufficiently narrowed parent claim trivially satisfies the constraint — making it enforceable only in cases where the fallback is not used?

Output for Q3: for each candidate, a verdict (keep as-is / merge / split / remove / scope down) with a one-sentence justification.

---

## Assessment Question 4 — Diagram and dependency fidelity

*Claim (question):* Does the §6 Mermaid flowchart and recovery edge table accurately and completely encode the dependency structure stated in §6 prose, such that an AI receiver relying solely on those two structures — without reading the prose — would parse the same ordering and feedback constraints?

Assess:

- **Node-phase mapping**: Does every check (`CONTENT-TYPE`–`HEADING-SYNTHESIS`) appear as a node, assigned to the correct phase subgraph? Does the `RC1` precondition gate node (`G`) appear correctly in Phase 1, visually distinct from compliance nodes, before `CONTENT-TYPE`? Compare node labels and subgraph assignments against the four-phase sequencing and precondition gate prose in §6.
- **Intra-phase edge completeness**: Within each phase subgraph, do the directed edges correctly encode the stated ordering? Identify any check that §6 prose states must precede another within the same phase but which has no corresponding edge in the diagram.
- **Cross-phase dependency edges**: The diagram shows two dashed cross-phase edges (`CONTENT-TYPE` → `TYPE-LABEL` "types before labels"; `MECE` → `HEADING-SYNTHESIS` "item set before synthesis"). Do these capture all cross-phase hard ordering constraints stated in §6, or are there constraints in the prose that have no corresponding dashed edge?
- **Recovery edge completeness**: For each repair action in §5 and each phase precondition in §6, derive the set of backward dependencies that can be triggered — cases where a repair at check X invalidates a previously completed check Y. Compare this derived set against the recovery edge table. Identify any triggerable backward dependency not listed as a row. Assess whether the trigger conditions for the `CONTENT-TYPE` → `CLAIM-FIRST`, `CONTENT-TYPE` → `CONSEQUENCE`, and `CLAIM-FIRST` → `MECE` edges are precise enough to be actionable: the `CONTENT-TYPE` → `CLAIM-FIRST` and `CONTENT-TYPE` → `CONSEQUENCE` triggers each cover two cases — (a) `CONTENT-TYPE` repair moves Arguments to new sub-bullets, creating net-new items, and (b) `CONTENT-TYPE` repair relocates content within an existing item in a way that changes that item's lead or final sentence. Verify that these two cases are jointly exhaustive of the `CONTENT-TYPE` repairs that can invalidate `CLAIM-FIRST` or `CONSEQUENCE`. Identify any class of `CONTENT-TYPE` repair — for example, splitting one sub-bullet into two, or merging two sub-bullets into one — where it is ambiguous whether case (a) or case (b) applies, or where neither applies but the trigger should still fire.
- **Tier and N/A encoding**: Tier (T1/T2) is encoded in diagram node labels (e.g., `MECE · T2`). N/A conditions are encoded in a companion bypass table inserted between the Phase diagram caption and the recovery edge table — the table lists document conditions and maps each to the checks that are N/A under that condition. Verify: (a) T1/T2 labels on each node match the tier assignments in §5; (b) every check that carries an `N/A if:` guard in §5 appears in the companion bypass table under the correct document condition; (c) no check is listed in the table under a condition that its §5 guard does not cover. (d) N/A bypass logic for the `RC1` precondition gate: the gate is not a compliance check — assess whether the diagram and bypass table correctly communicate that an `RC1` failure stops affected section checks but does not generate an N/A designation for those checks. (e) *Bypass table completeness — bidirectional*: verify in both directions: (i) every `N/A if:` clause in §5 has a corresponding row and document-condition entry in the bypass table; (ii) every row in the bypass table maps to a condition explicitly stated in a §5 `N/A if:` clause. Identify any mismatch in either direction — a §5 guard with no bypass table row, or a bypass table row with no backing §5 guard.
- **Shading-caption consistency**: The caption describes shaded nodes as the default compliance-target mapping and qualifies this as instantiation-specific per §0. Verify that the caption's claim (shading is an example, not fixed) is consistent with the node style encoding in the Mermaid source. Note that v2 shades three nodes (`CONTENT-TYPE`, `MECE`, `LOAD-TEST`) and uses a separate yellow style for the `RC1` gate — verify the caption distinguishes these two shading roles.
- **§5.1 Decision map fidelity**: The template contains five decision maps (`CONTENT-TYPE`, `MECE`, `LOGIC-TYPE`, `LOAD-TEST`, `HEADING-SYNTHESIS`) in §5.1. The `LOAD-TEST` map encodes two labelled sub-paths: `BP` (block pass) and `SP` (sentence pass). Assess on three sub-axes: (a) *Selection correctness* — are these five checks correctly identified as requiring decision maps? Does `CLAIM-FIRST` have a single escalation branch, or does it require additional paths? For `CONSEQUENCE`, are its two branches — the escalation branch (illocutionary force judgment) and the precondition bypass (when `CLAIM-FIRST` already fully states the consequence) — mutually exclusive, or can a block require both simultaneously (e.g., `CLAIM-FIRST` partially but not fully states the consequence, and the remaining judgment requires domain context)? Identify any omitted check with branching logic that the prose cannot make parseable, or any mapped check whose branching is simple enough to retire the map. (b) *Branch completeness* — for each decision map, do all branches encode the complete repair logic from §5, including N/A exits, exemptions (including the Phase 3 ordering constraint exempt path in the `LOAD-TEST` SP sub-path), escalation conditions, stopping rules, and recovery path labels? Identify any branch present in §5 prose that has no corresponding path in the graph. (c) *Recovery table consistency* — do the recovery edge labels shown in all five decision maps (`CONTENT-TYPE`, `MECE`, `LOGIC-TYPE`, `LOAD-TEST`, `HEADING-SYNTHESIS`) match the trigger conditions and repair actions in the §6 recovery edge table? In particular: does the `LOAD-TEST` SP sub-path stopping rule (stop and record the dependency — do not remove) align with the `LOAD-TEST → MECE` recovery table entry — the table contains two rows for this edge (a `Repair Guard — pre-removal` row and a `Recovery edge — post-removal` row); verify the stopping rule aligns with the former and that no conflict exists with either. For the `CONTENT-TYPE` and `MECE` maps, verify that the recovery pointer nodes (D2 in `CONTENT-TYPE`; K2 and the Pass terminal in `MECE`) reference the correct §6 recovery edge entries. Identify any conflict between any decision map and the recovery table for the same edge.

Output for Q4: for each axis, a verdict (accurate / gap / inconsistency) with one-line rationale for any non-passing result. End with one sentence stating the net consequence for the diagram or table — what change (if any) the assessment requires.

---

## Assessment Question 5 — Scope boundary accuracy

*Claim (question):* Are the template's scope-in and scope-out boundaries correctly drawn, and do the operational scope claims hold against the template's own dependency structure?

Assess:

- **Scope-out document class accuracy**: §0 lists three document classes that produce systematic false findings: mathematical proofs (`` `CLAIM-FIRST`, `CONSEQUENCE`, `HEADING-SYNTHESIS`, `LOGIC-TYPE` ``), dialectical arguments (`` `CLAIM-FIRST`, `CONSEQUENCE`, `HEADING-SYNTHESIS`, `MECE` ``), and abductive reasoning (`` `CLAIM-FIRST`, `CONSEQUENCE`, `MECE`, `HEADING-SYNTHESIS` ``). For each class: (a) do the identified checks actually produce false findings for that class, or would some produce N/A designations instead? (b) are there checks not listed that would also produce false findings for that class?
- **Scope-out class overlap**: Are the three listed document classes mutually distinct, or do any overlap in ways that would cause a real document to be classified under more than one class? If overlap exists, assess whether it creates ambiguity — different false-finding sets — or whether the union of findings is still coherent.
- **Delta-audit — bound tightness**: Is the §6 delta-audit initial scope correctly defined? §6 defines the minimum re-audit scope for a single-node change as the changed node, its parent, and its sibling set — with an explicit upward cascade rule that may extend this scope further; the scope statement is an initial floor, not a ceiling. Given the recovery edges in the §6 table, assess whether the initial scope is correctly drawn — identify any recovery edge whose cascade could propagate a change beyond the stated initial scope: for example, a sibling-set change triggering `HEADING-SYNTHESIS` on the parent, which triggers `MECE` re-evaluation at a higher level, propagating to a grandparent sibling set outside the stated boundary.
- **Delta-audit — cascade termination**: Does the upward cascade termination argument hold? The delta-audit rule propagates upward until no parent claim is modified, with the stated bound that "the document has a finite root — upward propagation can continue at most as many levels as the document has depth, which is bounded." Assess whether this is sufficient: can a `MECE` repair that narrows a parent claim at level N create a new exhaustiveness gap at level N+1 — one previously satisfied by the original broader claim — triggering a narrowing at N+1 that opens a new gap at N+2? If such a sequence is possible, assess whether the finite-root bound still guarantees termination or whether the termination argument requires a supplementary bound.

Output for Q5: for each sub-question, a verdict (accurate / gap / inconsistency) with one-line rationale. End with one sentence stating whether the scope boundary claims require revision and at which location.


## Assessment Question 6: Structural DRY (Don't Repeat Yourself) Audit.
Claim (task): Identify structural logic that violates the single source of truth principle.
Search the document for operational rules (pass conditions, scope notes, execution triggers, or N/A bypasses) that are defined in one section but re-defined, appended to, or duplicated in another (e.g., split between §4, §5, and §6). Cite the specific *tokens* and § sections where this fragmentation occurs, and state which section should serve as the sole authoritative source.

## Verdict
Create a Verdict table of Assessment Question 1-6 with the following format:
| Issue | Source | Severity | Fix Effort | Recommended Action |
| :--- | :--- | :--- | :--- | :--- |