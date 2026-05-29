# Argument Structure Audit — Tools

Five standalone Python scripts and an interactive notebook for machine-assisted audit of structured argument documents.

---

## Prerequisites

**Required** — core graph queries, T1 checks, and report generation:
```bash
pip3 install networkx
```

**Optional** — interactive notebook:
```bash
pip3 install jupyter
```

**Optional** — interactive HTML graph visualisation:
```bash
pip3 install pyvis
```

**Optional** — static SVG/PNG rendering via Graphviz:
```bash
pip3 install pydot
brew install graphviz     # macOS
# apt install graphviz    # Linux
```

---

## Recommended usage order

**For a new document:**

```bash
# 1. Structural gate — catch encoding violations before graphing
python tools/t1_check.py <document.md>

# 2. Section overview — identify heavy sections before drilling
python tools/query.py <document.md> density

# 3. Confirm no detached nodes
python tools/query.py <document.md> orphans

# 4. Confirm no circular reasoning
python tools/query.py <document.md> cycles

# 5. Human-readable report for review handoff
python tools/report.py <document.md> > report.md

# 6. Drill into a specific section
python tools/query.py <document.md> subgraph <heading-slug>
```

**For a delta-audit after changing node X (spec §6 scope):**

```bash
python tools/query.py <document.md> ancestors <X>             # upstream — what reviews are invalidated
python tools/query.py <document.md> descendants <X>           # downstream — what is affected forward
python tools/query.py <document.md> subgraph <X-parent-slug>  # sibling set — re-check MECE
python tools/query.py <document.md> refs --target <X>         # prose blast radius — sections that cite X directly
```

Node IDs are not guessable — run `density` to see heading IDs, or `orphans` to surface problem node IDs. Format: `h2:slug` for top-level headings, `def:parent-slug:n` for definition items, `sub:parent-slug:n` for sub-items. All commands accept a partial ID if it matches exactly one node.

---

## For AI callers

All tool output is plain-text stdout — no parsing required. The decision boundary below tells an AI caller what it can act on autonomously and what must be handed back to a human.

**Exit codes:** `t1_check.py` exits 1 only on CRITICAL findings — SIGNIFICANT `[Fail]` findings exit 0. Always parse stdout for `[Fail]` lines; do not rely on exit code alone to determine whether the structural gate is clean. `query.py cycles` always exits 0 regardless of cycle detection; parse stdout for `DAG: NO` to detect a cycle in a shell pipeline.

**Valid content-type labels for repairs:** `Claim`, `Scope`, `Argument`, `Closure` — case-sensitive, exact match required. Using any other capitalisation or spelling will produce a new TYPE-LABEL `[Fail]`. Extended types declared in the document's §0 table are also valid for that document.

**Act on directly (structural, mechanical repair path):**

| Output | Action |
| :--- | :--- |
| `[Fail]` finding from `t1_check.py` | Apply the repair described in the note; re-run to confirm |
| `orphans` output | Investigate parser miss or document encoding violation at the reported line |
| `density` Unknown counts | Sub-item has no valid `*Type (Topic):*` label — formatting error, mechanically repairable; add the missing label and re-run |
| `cycles` output — cycle detected | Document is structurally non-compliant; report to human before any repair |

**Route to human reviewer (domain judgment required):**

| Output | Why it cannot be resolved by AI |
| :--- | :--- |
| `[Escalated]` finding | Pass condition requires semantic judgment not resolvable from structure alone |
| `mece` output | Mutual exclusivity and collective exhaustiveness require understanding the argument's domain logic |
| `cycles` output — cycle detected | Determining whether the cycle is an encoding error or an intentional back-reference requires document-level intent |
| `shared` output — N ≥ 5 | High-citation shared premises are independence-analysis candidates; whether they constitute a structural vulnerability requires domain judgment |

**Automation-ready sequence for a new document:**

```
t1_check → density → orphans → cycles → report
```

Run in that order. Stop and report to the human if any `[Fail]` finding cannot be resolved mechanically, if orphans are found, or if a cycle is detected. Do not proceed to `report` until the structural gate (`t1_check`) is clean or findings are explicitly deferred by the human.

---

## Prompt template — AI-assisted audit

Copy this prompt and fill in the `< >` placeholders before handing it to a blank AI. The questions at the bottom tell you what to decide before running.

````markdown
You are running a T1 structural audit on an argument document using the audit toolchain in `argument_structure_audit/tools/`. Run the following commands in order from the repository root and report back as specified.

**Document:** `<path/to/document.md>`

---

**Step 1 — Structural gate**
```bash
python tools/t1_check.py <path/to/document.md>
```
Report: paste the Markdown summary table. For each `[Fail]` finding, state the line number, the check name, and the note. Do not attempt to repair yet.

**Step 2 — Section overview**
```bash
python tools/query.py <path/to/document.md> density
```
Report: paste the full density table. For any section with Unknown > 0, note the section name and count — these are unlabelled sub-items, mechanically repairable by adding the missing `*Type (Topic):*` label.

**Step 3 — Orphan check**
```bash
python tools/query.py <path/to/document.md> orphans
```
Report: state count and list node IDs and line numbers if any found.

**Step 4 — Cycle check**
```bash
python tools/query.py <path/to/document.md> cycles
```
Report: state DAG confirmed or cycle detected. If cycle detected, stop and report — do not proceed.

**Step 5 — Report**
```bash
python tools/report.py <path/to/document.md> > report.md
```
Report: confirm the file was written. State total node and edge count from the header.

---

**Escalation rules — do not resolve these yourself:**
- Any `[Escalated]` finding: list them by check name and count only. Do not evaluate.
- Any `mece` output showing sibling sets: surface only, do not evaluate MECE.
- Any cycle: stop and hand back to the human.

**After completing all steps:** summarise in three lines — (1) T1 gate result, (2) structural health (orphans, DAG), (3) highest-Unknown section if any.
````

**Before handing this prompt to an AI, answer:**

1. **Document path** — what is the path to the document relative to the repository root?
2. **Scope** — full new-document audit (use the prompt above as-is), or delta-audit after changing a specific node (replace Steps 2–5 with `ancestors <node-id>`, `descendants <node-id>`, `subgraph <parent-slug>`)?
3. **Repairs** — do you want the AI to attempt mechanical repairs for `[Fail]` findings in a second pass, or report only?
4. **Report format** — summary mode (default) or `--full` for per-finding detail?

---

## `extract_graph.py` — Graph extractor

Parses a compliant argument document into a typed directed acyclic graph (DAG).
Works by pattern-matching Markdown tokens only — no NLP.
Requires `networkx`.

**Node types**

| Type | Source in document |
| :--- | :--- |
| `heading` | `##` / `###` sections |
| `definition_item` | Numbered bold items (`1. **Label**`) or `**Claim:**` paragraphs |
| `sub_item` | `- *Type (Topic):*` list items |

**Edge relations** (derived from child content type per `specification.md §3`)

| Relation | Trigger |
| :--- | :--- |
| `contains` | Structural parent → child (headings, Claim sub-items, Unknown) |
| `supports` | `Argument` sub-item → parent |
| `qualifies` | `Scope` sub-item → parent |
| `defends` | `Closure` sub-item → parent |

**Usage**

```bash
# JSON output (node-link format — loadable by D3.js, pyvis)
python tools/extract_graph.py <document.md> --output json > graph.json

# DOT output (Graphviz)
python tools/extract_graph.py <document.md> --output dot > graph.dot

# Both
python tools/extract_graph.py <document.md> --output both
```

Run from the repository root. `document.md` can be any path relative to the working directory.

---

## `t1_check.py` — T1 audit checker

Runs the seven T1 structural checks in the phase order defined in `specification.md §6`.
No third-party dependencies.

**Checks**

| Check | Phase | What it tests |
| :--- | :--- | :--- |
| `RC1` | Precondition | Heading hierarchy present, no skipped levels |
| `CONTENT-TYPE` | 1 | Arguments and Closures not embedded in flat prose |
| `CLAIM-FIRST` | 1 | First sentence of every definition item is a standalone claim |
| `CONSEQUENCE` | 3 | Last sentence of every sub-item states a consequence unit |
| `TYPE-LABEL` | 4 | Every sub-item label uses `*[Type] ([Topic]):*` format |
| `RC2` | Post-4 | Typed sub-items are list items, not flat paragraphs |
| `RC3` | Post-4 | Numbered bold items are identified as Claims by a convention note |

T2 checks (`MECE`, `LOGIC-TYPE`, `LOAD-TEST`, `HEADING-SYNTHESIS`) require a human domain-expert auditor and are not automated here.

**Usage**

```bash
python tools/t1_check.py <document.md>
```

**Output**

1. Per-check status with severity-sorted findings (`CRITICAL` / `SIGNIFICANT` / `MINOR`)
2. Markdown summary table in T1 strip Execution Protocol format

Result values: `[Pass]`, `[Fail]`, `[Escalated]`, `[N/A]`

`Escalated` means the check found no detectable structural violation but the pass condition requires domain judgment — route those items to a T2 reviewer.

---

## `query.py` — Graph query CLI

Eight graph queries plus prose cross-reference commands against a parsed document. All output is plain-text tables — readable by humans and AI callers without further parsing.

```bash
python tools/query.py <document.md> orphans
    # Sub-items with no typed parent edge (in-degree 0, type ≠ heading)

python tools/query.py <document.md> subgraph <heading-slug>
    # All nodes in the subgraph rooted at a heading (slug substring match), topological order

python tools/query.py <document.md> ancestors <node-id>
    # All upstream nodes — blast radius for a change to node-id (full or partial ID match)

python tools/query.py <document.md> descendants <node-id>
    # All downstream nodes from node-id — forward propagation scope for a change

python tools/query.py <document.md> cycles
    # DAG check — reports whether the graph contains circular reasoning

python tools/query.py <document.md> density
    # Content-type counts per top-level (##) section

python tools/query.py <document.md> chain
    # Longest path through the DAG in topological order (deepest reasoning chain)

python tools/query.py <document.md> mece
    # Direct children per heading — sibling sets for T2 MECE review

python tools/query.py <document.md> refs
    # Full prose cross-reference matrix: for each section, all [→ §N] and [→ OQ-EC.N] citations

python tools/query.py <document.md> refs --target <slug>
    # Inverted lookup: all sections that cite the target matching <slug>, with line numbers

python tools/query.py <document.md> shared
    # Targets cited from 3+ distinct sections (default) — shared premise / trunk detection

python tools/query.py <document.md> shared --min <N>
    # Set minimum citation count threshold to N
```

`mece` surfaces sibling sets with content_type labels and line references. It does **not** evaluate MECE — that requires a domain-expert human auditor.

`refs --target` gives the prose blast radius for a high-centrality node — complements `ancestors`/`descendants` for items that are logically load-bearing but structurally shallow. `shared` output with N ≥ 5 warrants flagging to a human reviewer — independence analysis requires domain judgment.

---

## `report.py` — Markdown audit report

Composes T1 check results and graph queries into a single Markdown document for human review handoff.

```bash
python tools/report.py <document.md>           # summary mode (default)
python tools/report.py <document.md> --full    # full per-finding detail
```

**Report sections:** T1 Check Summary · Critical and Significant Findings · Section Density · Structural Health · Top Load-Bearing Nodes

Summary mode collapses Escalated findings to a count per check. `--full` expands to all findings — equivalent to `t1_check.py` stdout plus the graph sections.

---

## `audit_notebook.ipynb` — Interactive exploration

Jupyter notebook for interactive analysis of a parsed document. Run `pip install jupyter` then open with `jupyter notebook tools/audit_notebook.ipynb`.

Set `DOCUMENT` in the setup cell. Sections:

| Section | What it exposes |
| :--- | :--- |
| T1 Checks | Summary table + per-check drill-down |
| Section Density | Argument/Scope/Claim/Closure/Unknown counts per h2 |
| Structural Health | Orphans, DAG check, longest reasoning chain |
| Section Subgraph | Full node tree for a heading (configurable slug) |
| Delta-Audit Scope | Ancestors + descendants for a changed node; `REF_SLUG` adds prose citation lookup alongside structural scope |
| Load-Bearing Nodes | Top-N non-heading nodes by degree centrality |
| T2 MECE Scaffolding | Direct children per heading for T2 review |
| Prose Cross-Reference Index | Full `[→ §N]` / `[→ OQ-EC.N]` citation matrix; set `REF_TARGET` for inverted lookup by item |
| Shared Premises | Targets cited from `SHARED_MIN`+ distinct sections — trunk detection; N≥5 auto-flagged for human review |
| pyvis | Interactive HTML render (requires `pip install pyvis`) |

---

## Visualisation

### Static render (Graphviz)

```bash
python tools/extract_graph.py <document.md> --output dot | dot -Tsvg -o graph.svg
open graph.svg
```

Use `dot` for hierarchical top-down layout (best for argument trees). Alternatives:
- `neato` — spring layout
- `fdp` — force-directed

### Interactive HTML (pyvis)

Save the JSON output, then run:

```python
import json
from pyvis.network import Network

with open("graph.json") as f:
    data = json.load(f)

color_map = {
    "Claim":    "#4caf50",
    "Argument": "#2196f3",
    "Scope":    "#ff9800",
    "Closure":  "#f44336",
    "Unknown":  "#9e9e9e",
}

net = Network(directed=True, height="900px")

for node in data["nodes"]:
    net.add_node(
        node["id"],
        label=node.get("topic") or node["id"][:30],
        title=node.get("lead_sentence", ""),
        color=color_map.get(node.get("content_type", "Unknown"), "#ccc"),
    )

for edge in data["links"]:
    net.add_edge(edge["source"], edge["target"], label=edge.get("relation", ""))

net.show("graph.html", notebook=False)
```

---

## Adapting to a different document format

The toolchain is a usable baseline for documents that follow the same structural paradigm — hierarchy plus typed labels — but use different tokens or type names.

**What can be changed with minimal effort:**

| Layer | Location | What to change |
| :--- | :--- | :--- |
| Type names (`Point` instead of `Claim`) | §0 declaration in document | Declare in `\| **Extended content types** \| Point \|` — parser accepts it automatically |
| Structural tokens (regex patterns) | `extract_graph.py` lines 48–86 | Six regex constants with worked examples on each; swap for new format's tokens |
| Per-token handlers | `extract_graph.py` `_handle_*` functions | Four functions, ~15 lines each, independently readable; a new token type is one `elif` + one new handler |
| Check definitions | `t1_check.py` `check_*` functions | Each check is standalone; replace, add, or remove without touching other checks |

**What is format-agnostic and needs no changes:**

`build_graph`, `query.py` (all 8 commands), `report.py`, and the notebook operate on the graph after parsing. Any well-formed DAG from any parser variant works with all of these unchanged.

**Where adaptation breaks down:**

The parser assumes relationships are encoded structurally (parent → children via containment) and that content types are label-encoded in the text. A format where relationships are stated as explicit cross-references rather than structural nesting would require rethinking `build_graph`, not just the parser — that is a deeper change, not a configuration.

**After any modification, run the test suite:**

```bash
python3 tools/test_suite.py
```

44 tests cover the full pipeline against a synthetic compliant and non-compliant fixture — graph extraction, edge relations, all 7 T1 checks, all 8 query commands, all 5 report sections, and end-to-end integration. Exit 0 = pipeline intact.
