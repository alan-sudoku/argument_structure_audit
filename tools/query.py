#!/usr/bin/env python3
"""Structural graph query CLI for typed argument DAGs.

Eight graph queries plus prose cross-reference commands against a parsed
argument document. All output goes to stdout in plain-text table format —
readable by both humans and AI callers without further parsing.

Imports parse_document and build_graph from extract_graph.py (same directory).

Usage:
    python tools/query.py <document.md> orphans
    python tools/query.py <document.md> subgraph <heading-slug>
    python tools/query.py <document.md> ancestors <node-id>
    python tools/query.py <document.md> descendants <node-id>
    python tools/query.py <document.md> cycles
    python tools/query.py <document.md> density
    python tools/query.py <document.md> chain
    python tools/query.py <document.md> mece
    python tools/query.py <document.md> refs
    python tools/query.py <document.md> refs --target <slug>
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import networkx as nx
except ImportError:
    print("networkx not found — run: pip install networkx", file=sys.stderr)
    sys.exit(1)

# Add this script's directory to sys.path so extract_graph can be imported
# without requiring the caller to set PYTHONPATH manually.
sys.path.insert(0, str(Path(__file__).parent))
from extract_graph import parse_document, build_graph


# ---------------------------------------------------------------------------
# Query implementations
# ---------------------------------------------------------------------------

def _resolve_node_id(G: nx.DiGraph, node_id: str) -> str:
    """Resolve a full or partial node ID against the graph.

    Returns the matched node ID. Exits with a clear message if not found or
    if the substring matches more than one node.
    """
    if node_id in G:
        return node_id
    matches = [n for n in G.nodes() if node_id in n]
    if not matches:
        print(f"Node '{node_id}' not found.", file=sys.stderr)
        sys.exit(1)
    if len(matches) > 1:
        print(f"Ambiguous node ID '{node_id}' — multiple matches:", file=sys.stderr)
        for m in matches:
            print(f"  {m}", file=sys.stderr)
        sys.exit(1)
    return matches[0]


def cmd_orphans(G: nx.DiGraph) -> None:
    """Sub-items and definition items with no typed parent edge (in-degree 0).

    Top-level headings legitimately have in-degree 0 — excluded by type filter.
    Anything else at in-degree 0 has no edge from its structural parent,
    indicating a parser miss or a document encoding violation.
    """
    orphans = [
        n for n in G.nodes()
        if G.in_degree(n) == 0 and G.nodes[n].get("type") != "heading"
    ]
    if not orphans:
        print("No orphans found.")
        return
    print(f"Orphans: {len(orphans)}")
    print()
    print(f"{'Node ID':<50} {'Type':<18} {'Line':>4}  Topic")
    print("-" * 100)
    for n in sorted(orphans, key=lambda x: G.nodes[x].get("line", 0)):
        attrs = G.nodes[n]
        label = (attrs.get("topic") or attrs.get("lead_sentence", ""))[:50]
        print(f"{n:<50} {attrs.get('type',''):<18} {attrs.get('line',0):>4}  {label}")


def cmd_subgraph(G: nx.DiGraph, slug: str) -> None:
    """All nodes in the subgraph rooted at the heading whose ID contains slug.

    Prints nodes in topological order — correct reading order for the sub-tree.
    Exits with error and lists available headings if the slug is ambiguous or absent.
    """
    if not slug:
        raise ValueError("slug must be a non-empty string")
    candidates = [
        n for n in G.nodes()
        if G.nodes[n].get("type") == "heading" and slug in n
    ]
    if not candidates:
        print(f"No heading node found matching '{slug}'.", file=sys.stderr)
        print("Available h2 headings (deeper headings can also be targeted):", file=sys.stderr)
        for n in G.nodes():
            if G.nodes[n].get("type") == "heading" and G.nodes[n].get("level") == 2:
                print(f"  {n}", file=sys.stderr)
        sys.exit(1)
    if len(candidates) > 1:
        print(f"Ambiguous slug '{slug}' — multiple matches:", file=sys.stderr)
        for c in candidates:
            print(f"  {c}", file=sys.stderr)
        print("Refine the slug and retry.", file=sys.stderr)
        sys.exit(1)

    root = candidates[0]
    scope = {root} | nx.descendants(G, root)
    sub = G.subgraph(scope)

    print(f"Subgraph rooted at: {root}  ({len(scope)} nodes)")
    print()
    print(f"{'Node ID':<50} {'Type':<18} {'Content-type':<14} {'Line':>4}  Topic")
    print("-" * 110)
    for n in nx.topological_sort(sub):
        attrs = sub.nodes[n]
        label = (attrs.get("topic") or attrs.get("lead_sentence", ""))[:40]
        print(
            f"{n:<50} {attrs.get('type',''):<18} {attrs.get('content_type',''):<14}"
            f" {attrs.get('line',0):>4}  {label}"
        )


def cmd_descendants(G: nx.DiGraph, node_id: str) -> None:
    """All nodes downstream of node_id — forward propagation from a change to that node.

    Accepts a full node ID or an unambiguous substring. Downstream means every
    node reachable from node_id following directed edges.
    Together with ancestors, gives the full delta-audit scope for a changed node.
    """
    if not node_id:
        raise ValueError("node_id must be a non-empty string")
    node_id = _resolve_node_id(G, node_id)

    desc = nx.descendants(G, node_id)
    if not desc:
        print(f"'{node_id}' has no descendants (leaf node).")
        return

    print(f"Descendants of: {node_id}  ({len(desc)} nodes)")
    print()
    print(f"{'Node ID':<50} {'Type':<18} {'Line':>4}  Topic")
    print("-" * 100)
    for n in sorted(desc, key=lambda x: G.nodes[x].get("line", 0)):
        attrs = G.nodes[n]
        label = (attrs.get("topic") or attrs.get("lead_sentence", ""))[:50]
        print(f"{n:<50} {attrs.get('type',''):<18} {attrs.get('line',0):>4}  {label}")


def cmd_ancestors(G: nx.DiGraph, node_id: str) -> None:
    """All nodes upstream of node_id — the blast radius for a change to that node.

    Accepts a full node ID or an unambiguous substring. Upstream means every
    node from which node_id is reachable following directed edges.
    """
    if not node_id:
        raise ValueError("node_id must be a non-empty string")
    node_id = _resolve_node_id(G, node_id)

    ancs = nx.ancestors(G, node_id)
    if not ancs:
        print(f"'{node_id}' has no ancestors (root node).")
        return

    print(f"Ancestors of: {node_id}  ({len(ancs)} nodes)")
    print()
    print(f"{'Node ID':<50} {'Type':<18} {'Line':>4}  Topic")
    print("-" * 100)
    for n in sorted(ancs, key=lambda x: G.nodes[x].get("line", 0)):
        attrs = G.nodes[n]
        label = (attrs.get("topic") or attrs.get("lead_sentence", ""))[:50]
        print(f"{n:<50} {attrs.get('type',''):<18} {attrs.get('line',0):>4}  {label}")


def cmd_cycles(G: nx.DiGraph) -> None:
    """Report whether the graph is a DAG; list any cycles if not.

    Circular reasoning in a compliant document is a structural violation.
    This check is trivially correct — NetworkX cycle detection is O(V+E).
    """
    if nx.is_directed_acyclic_graph(G):
        print("DAG: yes — no cycles detected.")
        return
    print("DAG: NO — cycles detected.")
    print()
    try:
        cycle = nx.find_cycle(G)
        print("First cycle found:")
        for u, v, *_ in cycle:
            print(f"  {u} → {v}")
    except nx.NetworkXNoCycle:
        print("  (cycle finder returned no cycle despite failed DAG check)")


def cmd_density(G: nx.DiGraph) -> None:
    """Content-type counts per top-level (##) section.

    Counts descendants of each h2 heading by content_type. Argument count is
    a proxy for justification load; high Unknown count flags encoding gaps.
    """
    top_headings = [
        n for n in nx.topological_sort(G)
        if G.nodes[n].get("type") == "heading" and G.nodes[n].get("level") == 2
    ]

    rows = []
    for h in top_headings:
        desc = nx.descendants(G, h)
        ct = {"Argument": 0, "Scope": 0, "Claim": 0, "Closure": 0, "Unknown": 0}
        for d in desc:
            key = G.nodes[d].get("content_type", "Unknown")
            ct[key] = ct.get(key, 0) + 1
        rows.append((G.nodes[h].get("lead_sentence", h), ct))

    w = min(max((len(r[0]) for r in rows), default=20), 48)
    print(f"{'Section':<{w}}  {'Arg':>5}  {'Scope':>5}  {'Claim':>5}  {'Closure':>7}  {'Unknown':>7}  {'Total':>5}")
    print("-" * (w + 46))
    for label, ct in rows:
        total = sum(ct.values())
        print(
            f"{label[:w]:<{w}}  {ct['Argument']:>5}  {ct['Scope']:>5}  {ct['Claim']:>5}"
            f"  {ct['Closure']:>7}  {ct['Unknown']:>7}  {total:>5}"
        )


def cmd_mece(G: nx.DiGraph) -> None:
    """List direct children of every heading for T2 MECE review.

    For each heading, shows its direct non-heading children grouped by
    content_type. Does NOT evaluate MECE — that requires a domain-expert
    human auditor. Surfaces the sibling sets and flags where MECE is
    applicable (≥2 siblings) vs. N/A (0 or 1 sibling).

    Output is scoped to headings that have at least one direct child.
    """
    topo = list(nx.topological_sort(G))
    headings = [n for n in topo if G.nodes[n].get("type") == "heading"]

    for h in headings:
        children = [
            v for v in G.successors(h)
            if G.nodes[v].get("type") != "heading"
        ]
        if not children:
            continue

        level   = G.nodes[h].get("level", 0)
        label   = G.nodes[h].get("lead_sentence", h)[:70]
        indent  = "  " * (level - 1)
        mece_flag = "N/A (single item)" if len(children) == 1 else "→ T2 MECE review"

        print(f"{indent}{label}")
        print(f"{indent}  Node: {h}  |  Children: {len(children)}  |  {mece_flag}")

        for child in sorted(children, key=lambda x: G.nodes[x].get("line", 0)):
            attrs  = G.nodes[child]
            ctype  = attrs.get("content_type", "Unknown")
            topic  = (attrs.get("topic") or attrs.get("lead_sentence", ""))[:55]
            print(f"{indent}    [{ctype:<10}] line {attrs.get('line',0):>4}  {topic}")
        print()


def cmd_chain(G: nx.DiGraph) -> None:
    """Print the longest path through the DAG — the deepest reasoning chain.

    Uses nx.dag_longest_path (hop count, unweighted). The path reflects the
    deepest nesting from a root node to a leaf, tracing the primary spine
    of the argument hierarchy.
    """
    try:
        path = nx.dag_longest_path(G)
    except nx.NetworkXUnfeasible:
        print("Graph contains cycles — longest path undefined.", file=sys.stderr)
        sys.exit(1)

    print(f"Longest path: {len(path)} nodes")
    print()
    print(f"{'#':>3}  {'Node ID':<50} {'Type':<18} {'Line':>4}  Topic")
    print("-" * 110)
    for i, n in enumerate(path, 1):
        attrs = G.nodes[n]
        label = (attrs.get("topic") or attrs.get("lead_sentence", ""))[:40]
        print(
            f"{i:>3}  {n:<50} {attrs.get('type',''):<18} {attrs.get('line',0):>4}  {label}"
        )



# ---------------------------------------------------------------------------
# Prose cross-reference helpers
# ---------------------------------------------------------------------------

# Matches fenced code blocks: captures the opening fence marker (``` or ~~~).
# Example: ```python  →  group(1) == "```"
_FENCE_RE = re.compile(r"^([`~]{3,})")

# Matches inline prose references of the form [→ §N ...] or [→ OQ-EC.N ...].
# Example: *[→ §5.2 Source orthogonality]*  →  group(1) == "§5.2 Source orthogonality"
# Example: *[→ OQ-EC.4]*                    →  group(1) == "OQ-EC.4"
_REF_RE = re.compile(r"\[→\s+([^\]]+)\]")

# Matches Markdown section headings at any level.
# Example: "## §2 Argument"  →  group(1) == "##", group(2) == "§2 Argument"
_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)")


def _parse_refs(path: str) -> dict[str, list[tuple[int, str]]]:
    """Return inverted index: target_text → [(lineno, section_heading), ...].

    Parses raw Markdown for [→ target] patterns outside fenced blocks.
    Each entry records which section the citation appears in and its line number.
    Sections are identified by the nearest preceding heading.

    Args:
        path: path to the Markdown document (string, not Path).

    Returns:
        Dict mapping each distinct citation target text to a list of
        (line_number, section_heading) tuples, one per occurrence.
    """
    if not path:
        raise ValueError("path must be a non-empty string")

    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as e:
        print(f"Cannot read '{path}': {e.strerror}", file=sys.stderr)
        sys.exit(1)

    inverted: dict[str, list[tuple[int, str]]] = {}
    current_section = "(preamble)"
    in_fence = False
    fence_marker = ""

    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()

        # Fence tracking — same pattern as extract_graph.py
        fence_match = _FENCE_RE.match(stripped)
        if not in_fence and fence_match:
            in_fence = True
            fence_marker = fence_match.group(1)
            continue
        if in_fence:
            if stripped.startswith(fence_marker):
                in_fence = False
            continue

        # Track current section heading
        heading_match = _MD_HEADING_RE.match(line)
        if heading_match:
            current_section = heading_match.group(2).strip()
            continue

        # Collect all [→ target] citations on this line
        for m in _REF_RE.finditer(line):
            target = m.group(1).strip()
            inverted.setdefault(target, []).append((lineno, current_section))

    return inverted


def cmd_refs(path: str, target: str | None = None) -> None:
    """Prose cross-reference index.

    Without --target: prints a full matrix — for each section, all citation
    targets it contains. Sections with no citations are omitted.

    With --target: inverted lookup — lists every section that cites the target
    matching the given slug (substring match), with line number and citation text.

    Args:
        path:   path to the Markdown document.
        target: optional slug to invert the lookup.
    """
    inverted = _parse_refs(path)

    if not inverted:
        print("No prose cross-references found.")
        return

    if target is not None:
        # Inverted lookup: find all targets whose text contains the slug
        matches = {t: locs for t, locs in inverted.items() if target.lower() in t.lower()}
        if not matches:
            print(f"No citations found matching '{target}'.", file=sys.stderr)
            sys.exit(1)

        total = sum(len(locs) for locs in matches.values())
        print(f"Citations matching '{target}': {total} occurrence(s) across {len(matches)} target(s)")
        print()
        for tgt, locs in sorted(matches.items()):
            print(f"  Target: [{tgt}]")
            for lineno, section in sorted(locs):
                print(f"    line {lineno:>4}  in: {section}")
        return

    # Full matrix: group by section (preserving first-occurrence order)
    by_section: dict[str, list[tuple[int, str]]] = {}
    for tgt, locs in inverted.items():
        for lineno, section in locs:
            by_section.setdefault(section, []).append((lineno, tgt))

    # Sort each section's citations by line number
    for section in by_section:
        by_section[section].sort()

    # Order sections by their first citation line
    section_order = sorted(by_section.keys(), key=lambda s: by_section[s][0][0])

    total_citations = sum(len(v) for v in by_section.values())
    total_targets = len(inverted)
    print(f"Prose cross-references: {total_citations} citation(s) to {total_targets} distinct target(s)")
    print()
    for section in section_order:
        cites = by_section[section]
        print(f"  {section}  ({len(cites)} citation(s))")
        for lineno, tgt in cites:
            print(f"    line {lineno:>4}  → {tgt}")
        print()



def _split_citation(text: str) -> list[str]:
    """Split a compound citation string into individual identifier tokens.

    Citation text inside [→ ...] may be comma-separated:
      "§3 derivation-convergent stability, OQ-EC.4, OQ-EC.12"
    Respects parentheses so commas inside "(topic, detail)" are not split points.

    Example: "§2 Argument (a, b), OQ-EC.4" → ["§2 Argument (a, b)", "OQ-EC.4"]
    """
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in text:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            token = "".join(current).strip()
            if token:
                parts.append(token)
            current = []
        else:
            current.append(ch)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def cmd_shared(path: str, min_count: int = 3) -> None:
    """Shared premise / trunk detection.

    Builds the inverted citation index (reusing _parse_refs), splits compound
    citation strings into individual identifier tokens, then reports every
    identifier cited from N or more distinct sections, sorted descending by count.

    Targets above the threshold are shared-premise candidates — falsifying one
    removes a premise from every citing section simultaneously.

    Args:
        path:      path to the Markdown document.
        min_count: minimum number of distinct sections citing a target (default 3).
    """
    if min_count < 1:
        raise ValueError("min_count must be >= 1")

    inverted = _parse_refs(path)

    # Expand compound citation strings into individual tokens, then build
    # token → set-of-sections mapping.
    token_sections: dict[str, set[str]] = {}
    for compound_tgt, locs in inverted.items():
        for token in _split_citation(compound_tgt):
            for _, section in locs:
                token_sections.setdefault(token, set()).add(section)

    candidates = {
        token: sections
        for token, sections in token_sections.items()
        if len(sections) >= min_count
    }

    if not candidates:
        print(f"No shared premises found (threshold: cited from {min_count}+ distinct sections).")
        return

    sorted_candidates = sorted(candidates.items(), key=lambda x: -len(x[1]))

    print(f"Shared premises: {len(candidates)} target(s) cited from {min_count}+ distinct sections")
    print()
    print(f"  {'N':>3}  Target")
    print(f"  {'─'*3}  {'─'*70}")
    for token, sections in sorted_candidates:
        n = len(sections)
        print(f"  {n:>3}  {token}")
        for sec in sorted(sections):
            print(f"       ↳ {sec}")
        print()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Structural graph queries against a typed argument document."
    )
    parser.add_argument("document", help="Path to the Markdown document")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("orphans",  help="Sub-items with no typed parent edge")
    sg = sub.add_parser("subgraph", help="Subgraph rooted at a heading (slug match)")
    sg.add_argument("slug", help="Substring of the target heading node ID")
    anc = sub.add_parser("ancestors",   help="All upstream nodes for a node (blast radius)")
    anc.add_argument("node_id", help="Full or partial node ID")
    desc = sub.add_parser("descendants", help="All downstream nodes from a node (forward propagation)")
    desc.add_argument("node_id", help="Full or partial node ID")
    sub.add_parser("cycles",   help="DAG check — report any cycles")
    sub.add_parser("density",  help="Content-type counts per top-level section")
    sub.add_parser("chain",    help="Longest path through the DAG")
    sub.add_parser("mece",     help="Direct children per heading — sibling sets for T2 MECE review")
    refs_p = sub.add_parser("refs", help="Prose cross-reference index ([→ §N] / [→ OQ-EC.N] citations)")
    refs_p.add_argument("--target", default=None, metavar="SLUG",
                        help="Inverted lookup: list sections that cite the target matching SLUG")
    shared_p = sub.add_parser("shared", help="Shared premise detection — targets cited from N+ distinct sections")
    shared_p.add_argument("--min", type=int, default=3, dest="min_count", metavar="N",
                          help="Minimum section count threshold (default: 3)")

    args = parser.parse_args()

    # refs and shared operate on raw Markdown — no graph build needed
    if args.command == "refs":
        cmd_refs(args.document, getattr(args, "target", None))
        return
    if args.command == "shared":
        cmd_shared(args.document, args.min_count)
        return

    nodes, edges = parse_document(args.document)
    G = build_graph(nodes, edges)

    dispatch = {
        "orphans":   lambda: cmd_orphans(G),
        "subgraph":  lambda: cmd_subgraph(G, args.slug),
        "ancestors":   lambda: cmd_ancestors(G, args.node_id),
        "descendants": lambda: cmd_descendants(G, args.node_id),
        "cycles":    lambda: cmd_cycles(G),
        "density":   lambda: cmd_density(G),
        "chain":     lambda: cmd_chain(G),
        "mece":      lambda: cmd_mece(G),
    }
    dispatch[args.command]()


if __name__ == "__main__":
    main()
