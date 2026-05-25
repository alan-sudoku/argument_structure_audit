# Argument Structure Audit — Blank-AI Usage Assessment Prompt

*Claim (task):* You have just applied `specification.md` to a document. Answer the questions below about how you processed and used the template — not about the document you audited. The subject of this assessment is your own usage of the template, not its correctness as an artifact.

Answer each question with specific evidence from the template text — quote the token, sentence, or structural element that caused the behaviour you describe. Do not generalise.

---

## Context

The template defines nine structural checks, five decision maps, a four-phase application order, an `RC1` precondition gate, a recovery edge table, and an N/A bypass table. It is intended to be executable by a blank-AI receiver without full linear parsing.

This assessment probes four qualitative dimensions of your usage:
1. **Attention** — where did you look first, and what did you skip?
2. **Uncertainty** — where did you stop to resolve ambiguity?
3. **Confidence** — where did you proceed at speed without checking?
4. **Speed-bias** — where might speed have produced a misread?

Plus a fifth section that probes structural properties of your reconstruction — whether entailment relations, operator types, and constraint boundaries survived the encoding-to-reconstruction pass.

---

## Output format

Respond one section at a time. For each question: lead with the verdict or finding (claim-first), then provide the specific token or structural evidence. Use `*quoted text*` to cite template content directly. Flag any question you cannot answer with specific evidence — state which structural signal was absent.

End with one paragraph stating: what single change to the template would most reduce processing uncertainty for a blank-AI receiver applying it for the first time.

## Section 1 — Parsing and attention

*Claim (purpose):* identify where a blank-AI directs attention first and what navigation signals it uses before reading body content.

**Q1.1 — First engagement**
Before reading any section body, what was the first structural element you engaged with after the title? State which element (execution protocol, Table of Contents, §0, other) and what information you extracted from it. If you read multiple elements before entering a section body, list them in order.

**Q1.2 — Heading predictability**
List the section headings (§0–§8, plus §5.1 and the four Phase headings) in the order you encountered them. For each, mark: (a) *predicted* — the heading gave sufficient information to predict the section's content before entering it; or (b) *opaque* — you required body text to understand what the section contained. For every opaque heading, state what misled you.

**Q1.3 — Entry point under time pressure**
If you could read only two sections before applying the checklist, which two would you choose and why? Does the template's execution protocol (steps 1–6) agree with your choice? If not, state the divergence.

**Q1.4 — Table of Contents utility**
The ToC has ten rows including §5.1. Which rows were load-bearing for navigation — they told you something you could not have inferred from the heading alone? Which rows were decorative — they named the section without adding navigational information?

---

## Section 2 — Chain of thought and uncertainty stops

*Claim (purpose):* identify the information points where the AI must hold multiple interpretations simultaneously before resolving — the "but" and "could be" moments in processing.

**Q2.1 — Ambiguous terms at first encounter**
List every term in the template that required you to hold two or more interpretations before resolution. For each term, state: (a) the two interpretations you were weighing; (b) the token or structural signal that resolved the ambiguity; (c) whether the resolution came from the same sentence, the same section, or a later section.

Candidate terms to examine — assess each explicitly:
- `T2 escalation` in `CONTENT-TYPE`, `CLAIM-FIRST`, `CONSEQUENCE`
- `[consequence unit — from §0]` before §0 is read
- `N/A if:` — is this a conditional bypass or a mandatory pre-check?
- `domain-expert auditor` — is this a named person or a capability requirement?
- `Loop termination` in the §5 `HEADING-SYNTHESIS` check specification (the recovery edge table contains a pointer to §5, not the full argument — note whether you followed the pointer or treated the pointer as sufficient)
- `skeleton document` in `LOAD-TEST` (both passes)
- `precondition gate` for `RC1` — is this a check that produces a pass/fail verdict, or a structural stop condition that triggers repair before any check runs?

**Q2.2 — Provisional interpretations revised**
Identify any point where you held a provisional interpretation of a check, rule, or constraint, continued reading, and later revised it. State: (a) the original interpretation; (b) the token that triggered revision; (c) the revised interpretation. If no revision occurred, state which checks you are least confident about and why.

**Q2.3 — Recovery edge discovery**
At what point did you discover that repairing check X could invalidate a previously completed check Y? Was it: (a) before applying any check, from the §6 recovery edge table; (b) during repair, triggered by a note in §5; (c) after completing a phase, retrospectively? State the specific check pair that first made the dependency visible.

**Q2.4 — Phase ordering constraint vs. recommendation**
The template states: *"Phase ordering is a satisfiability constraint, not a stylistic preference."* Did you read this as a hard constraint (violating it produces an unsatisfiable state) or as a strong recommendation (violating it increases rework risk)? At what point did you settle on your reading, and what token confirmed it?

---

## Section 3 — High-confidence speed-through points

*Claim (purpose):* identify information points with high certainty and low entropy — where the AI can proceed without ambiguity resolution.

**Q3.1 — Immediately applicable checks**
Which checks in §5 could you apply from the pass condition alone, without reading the repair action, escalation notes, or N/A guards? List them. For each, state what property of the pass condition made it unambiguous — syntax, explicit binary condition, absence of domain dependency.

**Q3.2 — Encoding key recognition**
The template uses four encoding conventions: backtick check names, `[value — from §0]` parameters, `*Type (Topic):*` labels, and `· T1` / `· T2` tier markers. Which of these did you recognise as a typed convention on first encounter without reading the encoding key? Which required the key to interpret correctly?

**Q3.3 — Structural redundancy**
Identify information stated in more than one location in the template (e.g., a check's N/A condition appears both in the §5 check specification and in the §6 N/A bypass table). For each redundancy: (a) which location did you consult first? (b) did the second location add any information the first did not carry? (c) did the redundancy help or create noise?

**Q3.4 — Decision map vs. prose preference**
For the five checks with decision maps (`MECE`, `LOGIC-TYPE`, `CONTENT-TYPE`, `LOAD-TEST`, `HEADING-SYNTHESIS`): did you use the flowchart or the §5 prose to apply each check? State per check. If you used both, state what the flowchart gave you that the prose did not. For `LOAD-TEST` specifically: did the two-subgraph structure (`BP` block pass, `SP` sentence pass) help or hinder navigation of the merged check?

---

## Section 4 — Speed-bias and misread risk

*Claim (purpose):* identify information points where the LLM's pattern-completion speed may produce automatic responses that diverge from the template's intent — the equivalent of a user clicking a button before reading the label.

**Q4.1 — §0 binding before execution**
The execution protocol states: *"Bind §0 — fill in the parameter table before any check."* At what point did you first read the §0 parameter table? Was it: (a) before opening any §5 check section; (b) when a `[value — from §0]` reference appeared in a check; (c) not at all — you substituted a plausible value from context? If (b) or (c), state which check first contained the unresolved parameter reference.

**Q4.2 — N/A bypass table timing**
The N/A bypass table appears in §6, after the Phase diagram. At what point did you first consult it: (a) before executing Phase 1; (b) when a check produced no applicable targets; (c) after completing the audit? If a check stalled because you had no applicable targets, identify it — that check was the N/A guard's failure point for your processing sequence.

**Q4.3 — `LOAD-TEST` sub-step conflation**
`LOAD-TEST` sub-step 1 (block pass) tests whether a paragraph defines, constrains, or opens — a block-level judgment. Sub-step 2 (sentence pass) tests whether each sentence within a passing block is individually load-bearing — a sentence-level judgment with a different repair action. On first reading: did you treat these as two genuinely distinct operations requiring separate passes, or as a single continuous sweep from block to sentence? State: (a) which interpretation you held initially; (b) which token or structural signal separated them for you; (c) whether you applied the sentence pass selectively (only to blocks that marginally passed the block pass) or globally. If globally: identify which instruction in the template you used to justify that scope.

**Q4.4 — Phase diagram shading**
The Phase diagram shades three nodes green (`CONTENT-TYPE`, `MECE`, `LOAD-TEST`) as the default compliance-target mapping, and one node yellow (`RC1`) as the precondition gate. On first encounter, what did you read the green shading as indicating: (a) which checks are T1 vs. T2; (b) which checks are mandatory vs. optional; (c) which checks directly serve the compliance target vs. navigability? State the token or caption that established your reading. Separately: what did you read the yellow shading as indicating before reading the caption?

**Q4.5 — `LOAD-TEST` sentence-pass stopping rule**
The sentence-pass stopping rule states: *"Stop removal when every remaining sentence either (a) anchors the claim, (b) names a constraint boundary, or (c) is the `CONSEQUENCE` sentence."* A second stopping condition follows: *"If removing any remaining sentence would require `MECE` exhaustiveness re-evaluation for the affected sibling set, stop and record the dependency rather than removing."*

On first reading, did you interpret the first stopping rule as: (a) a termination condition — once reached, exit the sentence pass for this block; (b) a per-sentence filter — skip sentences that meet any of (a)–(c); (c) a minimum retention floor — remove everything until only (a)–(c) remain?

For the MECE dependency guard: did you read "stop" as: (a) stop evaluating this sentence and move to the next; (b) stop all removals in this block and record the dependency; (c) stop the entire sentence pass phase? State which interpretation you held before reading the `LOAD-TEST → MECE` recovery edge table row, and whether reading that row changed your interpretation.

**Q4.6 — T1 escalation as reclassification**
`CONTENT-TYPE`, `CLAIM-FIRST`, and `CONSEQUENCE` are classified T1 but carry escalation notes. Did you read the escalation note as: (a) evidence that these checks are misclassified and are actually T2; (b) a conditional branch within a T1 check — T1 detection, T2 repair; (c) a warning that T1 results are unreliable for certain document types? State the point at which your reading stabilised.

---

## Section 5 — Structural reconstruction quality (four probes)

*Claim (purpose):* assess structural properties of the AI's reconstruction of the template's constraint system — whether invariant content survived, what was lost, what was treated as binding vs. background, and where sender under-specification transferred cost to the receiver.

### §P1 — Invariance: did the entailment structure survive reconstruction?

**Q5.1 — Phase dependency preservation**
P1 requires that the consequence relation between transmitted elements is preserved in reconstruction. The template states that Phase 4 checks depend on Phase 2 being stable — not merely that Phase 4 comes after Phase 2, but that Phase 4 results are invalidated if Phase 2 is re-run.

Did your reconstruction preserve this entailment: *Phase 4 is only valid if Phase 2 is complete and stable*? Or did you reconstruct it as a weaker claim: *Phase 4 must be run after Phase 2*? State which version you held, and which token established the stronger reading if you held it.

**Q5.2 — Check identity across encodings**
`MECE` appears in: the §5 `MECE` check specification (`###` section), the §5.1 decision map, the §6 Phase diagram node, the §6 recovery edge table (multiple rows), and the N/A bypass table. Did you treat these as the same logical node — one check with multiple encodings — or did any encoding introduce a reading of `MECE` that conflicted with another? State any divergence.

**Q5.3 — Operator type preservation**
The template's phase ordering is a directed dependency structure (Phase N+1 depends on Phase N). The recovery edges are backward dependencies (repair at X re-opens Y). The `RC1` gate is a structural stop condition (not a dependency edge — it halts execution for affected sections until repair is complete). Did your reconstruction preserve the distinction between all three operator types — phase dependency, recovery edge, and gate stop — or did you flatten any two of them into a single "check this before that" rule?

### §P2 — Entropy: what was lost in reconstruction?

**Q5.4 — Surface mutation inventory**
P2 predicts that transmission is never lossless — surface form will mutate, but invariant structure must be preserved. List any information from the template that you paraphrased, compressed, or substituted in your internal representation. For each: (a) is it surface form (safe to lose) or invariant structural content (P1-protected)? (b) if it is invariant content, what was your substitution, and does it preserve the original entailment?

**Q5.5 — Encoding signal loss**
The template's §3 argument on AI receiver readability states that bold and italic are rendering-dependent signals; explicit type labels (`*Type (Topic):*`) and heading markers are rendering-independent. Did any semantic distinction in the template depend on bold or italic that you might have lost if processing raw token sequences without rendering? Identify the specific passages.

### §P3 — Constraint Packet: what did you treat as boundary conditions vs. background?

**Q5.6 — Layer 1 / Layer 2 classification**
P3 distinguishes Layer 1 content (P1-invariant, must be preserved: typed structure, operator types, entailment map) from Layer 2 content (optional domain guidance). Applied to the template:

- **Layer 1 candidates** (binding structural constraints): check pass conditions, phase ordering, `RC1` precondition gate stop condition, N/A guards, recovery edges, §0 parameter bindings, Phase 3 ordering constraint.
- **Layer 2 candidates** (contextual guidance): rationale in §1–§4, background arguments, authoring pipeline, self-compliance check.

State which sections you treated as Layer 1 and which as Layer 2. Identify any section you reclassified mid-read — Layer 2 on first encounter, Layer 1 after reading it. State specifically whether you initially treated the Phase 3 ordering constraint (§6) as Layer 1 or Layer 2, and at what point you settled on your classification.

**Q5.7 — Minimum sufficient read**
P3 asks: what is the minimum sufficient constraint packet for reliable reconstruction? Applied here: what is the minimum set of sections you needed to read before applying the template correctly? Compare this to the execution protocol's stated order (steps 1–6). If your minimum set differs from the protocol, identify the divergence and its cause.

**Q5.8 — Under-constrained regions**
Identify any instruction in the template where you had to expand the search space with your own prior knowledge because the template did not supply sufficient constraints. State: (a) the instruction; (b) what you filled in from prior knowledge; (c) whether a different receiver with different priors would fill it in differently.

### §P4 — Work: where did sender under-specification transfer cost to you?

**Q5.9 — Highest reconstruction cost**
P4 states that work omitted by the sender transfers to the receiver as an expanded search space. Identify the three points in the template that required the most reconstruction work from you — where you had to hold the most state, resolve the most ambiguity, or generate the most inferences. State per point: what work the template transferred to you and what constraint would have eliminated it.

**Q5.10 — Prior-fill detection**
Where did you complete a template instruction using your own training priors rather than explicit template content? A prior-fill is detectable when: you had a confident response before finishing the relevant sentence; or your response would differ from another AI with different training on the same instruction. Identify any such point and state what the template should have specified to prevent prior-fill.
