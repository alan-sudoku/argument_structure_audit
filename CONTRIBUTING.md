# Contributing to the Argument Structure Audit

---

## What is in scope

| Contribution type | Description |
| :--- | :--- |
| Bug report | A check produces contradictory results, a gap exists in the recovery edge table, or a document class produces false findings that are not documented in the scope-out table |
| Specification improvement | Changes to pass conditions, N/A guards, escalation paths, scope-out classes, or recovery edges in `specification.md` |
| Strip improvement | Changes to the T1 execution instrument in `t1_strip.md` |
| New scope-out class | A document class not currently listed that produces systematic false findings (not N/A designations) from one or more checks |
| Tool bug | A script produces incorrect output, crashes on valid input, or its output diverges from the specification's defined check behavior |
| Tool improvement | Changes to parser logic, check implementations, query commands, or report formatting in `tools/` |

**Out of scope:** changes to T2 check definitions (`MECE`, `LOGIC-TYPE`, `LOAD-TEST`, `HEADING-SYNTHESIS`) without a named human domain-expert auditor — these checks require semantic judgment that cannot be validated without domain knowledge of the document under audit. Any T2 proposal must name the auditor and include a documented audit pass using the current specification.

---

## Quality gate by contribution type

### Specification changes (`specification.md`)

1. Run `assess_specification.md` against the modified specification. All six questions must produce a verdict of accurate or keep-as-is before the change is proposed. Document any gap or inconsistency findings and state how the change resolves them.
2. Verify `specification.md` §7 self-compliance check still passes after the change.
3. If the change affects the phase diagram or recovery edge table, verify both in both directions: every `N/A if:` clause in §5 has a corresponding bypass table row, and every bypass table row has a backing §5 guard.

### Strip changes (`t1_strip.md`)

1. Run `t1_checklist.md` against the modified strip. Every item must pass before the change is proposed. A single No is a gap — repair before submitting.
2. Verify that all `[value — from §0]` references in the strip resolve to parameters defined in the §0 table.
3. Verify the T1 recovery edge table is complete for any check whose repair logic was modified — trace all edges forward to confirm no cycle is introduced.

### New scope-out class

Document the case using this structure:

- **Class name and definition** — what distinguishes this class from the three existing classes
- **False findings, not N/A** — for each check proposed for suspension, state why the check produces a false positive rather than an inapplicable result; name a concrete example
- **Checks not suspended** — confirm that `CONTENT-TYPE`, `TYPE-LABEL`, `RC2`, `RC3` still apply and state why

### Bug reports

State:
1. The check and the specific pass condition or repair instruction that is contradictory or incomplete
2. The document structure that exposes the gap — a minimal example with two levels of hierarchy
3. Whether the issue produces a false finding (incorrect verdict) or an open-ended state (no defined resolution path)

---

### Tool changes (`tools/`)

1. Run the test suite — all tests must pass before and after the change:
   ```bash
   python3 tools/test_suite.py
   ```
2. Verify the baseline node/edge count is unchanged on a reference document after any parser modification:
   ```bash
   python3 tools/extract_graph.py <reference.md> --output json \
     | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Nodes: {len(d[\"nodes\"])}, Edges: {len(d[\"links\"])}')"
   ```
3. For any new check behavior or query command, add a corresponding test case to `test_suite.py` — new behavior with no test will be rejected.
4. Check implementations in `t1_check.py` must align with the pass conditions defined in `specification.md §5`. A check that diverges from the specification is a specification bug, not a tool bug — open a specification improvement first.

**Format adaptations are out of scope for this repository.** The tools are a general-purpose baseline. PRs that hard-code conventions specific to a particular document's format (custom type names, non-standard tokens, project-specific regex) will not be merged. Adapt locally by following the guidance in `tools/README.md` — Adapting to a different document format.

---

## Prose changes — staging discipline

Any change that rewrites or reorders prose in `specification.md` or `t1_strip.md` must follow the staging workflow in `repair_guide.md` before being committed:

- Write the candidate in a staging block
- Apply the relevant check's pass condition explicitly to the candidate
- Confirm no new problem is introduced (sequencing dependency, orphaned cross-reference, recovery edge invalidated)
- Commit only after the staging audit passes

Mechanical changes (relabeling, list structure conversion) may be applied directly without staging.
