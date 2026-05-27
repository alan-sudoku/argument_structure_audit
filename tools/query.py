#!/usr/bin/env python3
"""Structural graph query CLI for typed argument DAGs.

Six deterministic NetworkX queries against a parsed argument document.
All output goes to stdout in plain-text table format — readable by both humans
and AI callers without further parsing.

Imports parse_document and build_graph from extract_graph.py (same directory).

Usage:
    python tools/query.py <document.md> orphans
    python tools/query.py <document.md> subgraph <heading-slug>
    python tools/query.py <document.md> ancestors <node-id>
    python tools/query.py <document.md> cycles
    python tools/query.py <document.md> density
    python tools/query.py <document.md> chain
"""

import argparse
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

def cmd_orphans(G):
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


def cmd_subgraph(G, slug):
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


def cmd_descendants(G, node_id):
    """All nodes downstream of node_id — forward propagation from a change to that node.

    Accepts a full node ID or an unambiguous substring. Downstream means every
    node reachable from node_id following directed edges.
    Together with ancestors, gives the full delta-audit scope for a changed node.
    """
    if not node_id:
        raise ValueError("node_id must be a non-empty string")
    if node_id not in G:
        matches = [n for n in G.nodes() if node_id in n]
        if not matches:
            print(f"Node '{node_id}' not found.", file=sys.stderr)
            sys.exit(1)
        if len(matches) > 1:
            print(f"Ambiguous node ID '{node_id}' — multiple matches:", file=sys.stderr)
            for m in matches:
                print(f"  {m}", file=sys.stderr)
            sys.exit(1)
        node_id = matches[0]

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


def cmd_ancestors(G, node_id):
    """All nodes upstream of node_id — the blast radius for a change to that node.

    Accepts a full node ID or an unambiguous substring. Upstream means every
    node from which node_id is reachable following directed edges.
    """
    if not node_id:
        raise ValueError("node_id must be a non-empty string")
    if node_id not in G:
        matches = [n for n in G.nodes() if node_id in n]
        if not matches:
            print(f"Node '{node_id}' not found.", file=sys.stderr)
            sys.exit(1)
        if len(matches) > 1:
            print(f"Ambiguous node ID '{node_id}' — multiple matches:", file=sys.stderr)
            for m in matches:
                print(f"  {m}", file=sys.stderr)
            sys.exit(1)
        node_id = matches[0]

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


def cmd_cycles(G):
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


def cmd_density(G):
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


def cmd_mece(G):
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


def cmd_chain(G):
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

    args = parser.parse_args()
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
