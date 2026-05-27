#!/usr/bin/env python3
"""Markdown audit report for a typed argument document.

Composes T1 check results and graph queries into a single Markdown document
suitable for human review handoff. No new logic — composition only.

Default mode: summary (Escalated findings collapsed to a count per check).
--full mode:  full per-finding detail, equivalent to t1_check.py stdout.

Usage:
    python tools/report.py <document.md> > report.md
    python tools/report.py <document.md> --full > report_full.md
"""

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_graph import parse_document, build_graph, scan_declared_types

try:
    import networkx as nx
except ImportError:
    print("networkx not found — run: pip install networkx", file=sys.stderr)
    sys.exit(1)

# Import check machinery from t1_check — no duplication of check logic.
from t1_check import collect_results


# ---------------------------------------------------------------------------
# Section renderers — each emits Markdown lines to a list, returns it
# ---------------------------------------------------------------------------

def _render_header(doc_path, nodes, edges, declared_types):
    doc_name = Path(doc_path).name
    extra = ""
    canonical = {"Claim", "Scope", "Argument", "Closure"}
    extended = sorted(declared_types - canonical)
    if extended:
        extra = f"  \nDeclared extended types: {', '.join(extended)}"
    return [
        f"# Argument Structure Audit Report — {doc_name}",
        "",
        f"Date: {date.today()}  ",
        f"Nodes: {len(nodes)}  |  Edges: {len(edges)}{extra}",
        "",
    ]


def _render_t1_summary(check_results):
    lines = ["## T1 Check Summary", ""]
    lines += ["| Check | Result | Notes |", "| :--- | :--- | :--- |"]
    for name, (findings, counts) in check_results.items():
        fails     = [f for f in findings if f.result == "Fail"]
        escalated = [f for f in findings if f.result == "Escalated"]
        if not fails and not escalated:
            result_cell, notes = "[Pass]", ""
        elif escalated and not fails:
            result_cell = "[Escalated]"
            notes = f"{len(escalated)} items require T2 review"
        else:
            result_cell = "[Fail]"
            sigs = counts.get("CRITICAL", 0) + counts.get("SIGNIFICANT", 0)
            notes = f"{sigs} failure(s)"
        lines.append(f"| {name} | {result_cell} | {notes} |")
    lines.append("")
    return lines


def _render_findings(check_results, full):
    """Critical/Significant findings section.

    Summary mode: Escalated items shown as count only; Fail items listed.
    Full mode: all findings listed in severity order.
    """
    lines = ["## Critical and Significant Findings", ""]

    any_printed = False
    for name, (findings, _) in check_results.items():
        fails     = [f for f in findings if f.result == "Fail"]
        escalated = [f for f in findings if f.result == "Escalated"]

        if full:
            to_show = sorted(findings,
                             key=lambda f: {"CRITICAL": 0, "SIGNIFICANT": 1, "MINOR": 2}
                             .get(f.severity, 3))
        else:
            to_show = sorted(fails,
                             key=lambda f: {"CRITICAL": 0, "SIGNIFICANT": 1}.get(f.severity, 2))

        if not to_show and not (escalated and not full):
            continue

        lines.append(f"### {name}")
        for f in to_show:
            lines.append(f"- [{f.severity}] {f.file}:{f.line} — {f.note}")
        if escalated and not full:
            lines.append(f"- [Escalated] {len(escalated)} items require T2 review")
        lines.append("")
        any_printed = True

    if not any_printed:
        lines.append("No Critical or Significant findings.")
        lines.append("")
    return lines


def _render_density(G):
    """Content-type counts per top-level (##) section."""
    lines = ["## Section Density", ""]

    try:
        sorted_nodes = list(nx.topological_sort(G))
    except nx.NetworkXUnfeasible:
        sorted_nodes = sorted(G.nodes(), key=lambda n: G.nodes[n].get("line", 0))
        lines.append("> *Note: graph contains cycles — section order falls back to document order.*\n")
    top_headings = [
        n for n in sorted_nodes
        if G.nodes[n].get("type") == "heading" and G.nodes[n].get("level") == 2
    ]
    rows = []
    for h in top_headings:
        desc = nx.descendants(G, h)
        ct = {"Argument": 0, "Scope": 0, "Claim": 0, "Closure": 0, "Unknown": 0}
        for d in desc:
            key = G.nodes[d].get("content_type", "Unknown")
            ct[key] = ct.get(key, 0) + 1
        label = G.nodes[h].get("lead_sentence", h)
        rows.append((label, ct))

    w = min(max((len(r[0]) for r in rows), default=20), 48)
    lines.append(f"| {'Section':<{w}} | {'Arg':>5} | {'Scope':>5} | {'Claim':>5} | {'Closure':>7} | {'Unknown':>7} | {'Total':>5} |")
    lines.append(f"| {':---':<{w}} | {'---:':>5} | {'---:':>5} | {'---:':>5} | {'---:':>7} | {'---:':>7} | {'---:':>5} |")
    for label, ct in rows:
        total = sum(ct.values())
        lines.append(
            f"| {label[:w]:<{w}} | {ct['Argument']:>5} | {ct['Scope']:>5} | {ct['Claim']:>5}"
            f" | {ct['Closure']:>7} | {ct['Unknown']:>7} | {total:>5} |"
        )
    lines.append("")
    return lines


def _render_structural_health(G):
    lines = ["## Structural Health", ""]

    orphans = [
        n for n in G.nodes()
        if G.in_degree(n) == 0 and G.nodes[n].get("type") != "heading"
    ]
    lines.append(f"- Orphans: {len(orphans) if orphans else 'none found'}")

    if nx.is_directed_acyclic_graph(G):
        lines.append("- Cycles: DAG confirmed")
    else:
        lines.append("- Cycles: WARNING — cycle detected")

    try:
        chain = nx.dag_longest_path(G)
        lines.append(f"- Longest reasoning chain: {len(chain)} nodes")
    except nx.NetworkXUnfeasible:
        lines.append("- Longest reasoning chain: undefined (graph contains cycles)")

    lines.append("")
    return lines


def _render_top_nodes(G, n=5):
    """Top N nodes by degree centrality, excluding headings."""
    lines = [f"## Top Load-Bearing Nodes (degree centrality, top {n})", ""]

    centrality = nx.degree_centrality(G)
    ranked = sorted(
        [(node, score) for node, score in centrality.items()
         if G.nodes[node].get("type") != "heading"],
        key=lambda x: x[1],
        reverse=True,
    )[:n]

    if not ranked:
        lines.append("No non-heading nodes found.")
    else:
        lines.append(f"| {'Node ID':<50} | {'Centrality':>10} | {'Line':>4} | Topic |")
        lines.append(f"| {':---':<50} | {'---:':>10} | {'---:':>4} | :--- |")
        for node, score in ranked:
            attrs = G.nodes[node]
            label = (attrs.get("topic") or attrs.get("lead_sentence", ""))[:40]
            lines.append(
                f"| {node:<50} | {score:>10.4f} | {attrs.get('line', 0):>4} | {label} |"
            )
    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Emit a Markdown audit report for a typed argument document."
    )
    parser.add_argument("document", help="Path to the Markdown document")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Include full per-finding detail (default: summary mode)",
    )
    args = parser.parse_args()

    try:
        text = Path(args.document).read_text(encoding="utf-8")
    except OSError as e:
        print(f"Error: could not read file — {args.document} ({e.strerror})", file=sys.stderr)
        sys.exit(1)

    nodes, edges = parse_document(args.document)
    G = build_graph(nodes, edges)

    declared = scan_declared_types(text)

    # T1 checks — reuse _collect_results; suppress t1_check stdout entirely.
    lines_text = text.splitlines()
    rel = Path(args.document).name
    check_results = collect_results(lines_text, rel)

    sections = (
        _render_header(args.document, nodes, edges, declared)
        + _render_t1_summary(check_results)
        + _render_findings(check_results, args.full)
        + _render_density(G)
        + _render_structural_health(G)
        + _render_top_nodes(G)
    )
    print("\n".join(sections))


if __name__ == "__main__":
    main()
