#!/usr/bin/env python3
"""Parse a structured argument document into a typed DAG.

Compliant argument documents encode their full graph structure in standard
Markdown tokens (specification.md §8). This tool exploits that property: it
recovers nodes and edges by pattern-matching tokens only — no NLP required.

Node types:
  heading        — ## / ### sections; form the backbone hierarchy
  definition_item — numbered bold items or **Claim:** paragraphs; argument roots
  sub_item       — "- *Type (Topic):*" list items; typed argument leaf nodes

Edge relations (derived from child content_type per specification.md §8):
  contains     — structural parent→child (headings, Claim sub-items, Unknown)
  supported_by — parent claim ←  Argument sub-item (claim is supported by argument)
  qualified_by — parent claim ←  Scope sub-item (claim is qualified by scope)
  defended_by  — parent claim ←  Closure sub-item (claim is defended by closure)

Requires: pip install networkx
Optional for DOT output: pip install pydot

Usage:
    python extract_graph.py <document.md> [--output json|dot|both]
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import networkx as nx
except ImportError:
    print("networkx not found — run: pip install networkx", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Compiled patterns — compiled once at import time for performance.
# Each pattern targets exactly one Markdown token type.
# ---------------------------------------------------------------------------

# Opening line of a fenced code or mermaid block (``` or ~~~).
# Used to suppress node extraction inside code blocks.
FENCE_RE = re.compile(r"^(`{3,}|~{3,})")

# ATX heading: captures (#-count, heading text).
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)")

# Numbered bold item: "1. **Label** rest text"
# e.g. "3. **Thermodynamic constraint** because X" → groups: ("3", "Thermodynamic constraint", "because X")
# Maps to a definition_item node; the bold label becomes the topic.
NUMBERED_RE = re.compile(r"^([0-9]+)\.\s+\*\*(.+?)\*\*\s*(.*)")

# Standalone bold claim: "**Claim:** text"
# Alternative definition_item form used in some compliant documents.
BOLD_CLAIM_RE = re.compile(r"^\*\*Claim:\*\*\s+(.*)")

# List item: captures (leading whitespace, body).
# Indentation depth (spaces // 2) determines nesting level.
SUBITEM_RE = re.compile(r"^(\s*)- (.*)")

# TYPE-LABEL format: "*Type (Topic):* remainder"
# e.g. "*Argument (energy cost):* Because X..." → groups: ("Argument", "energy cost", "Because X...")
# (.+?) is non-greedy but allows nested parens — e.g. "*Scope (difference (b)):*"
LABEL_RE = re.compile(r"^\*([\w]+)\s*\((.+?)\):\*\s*(.*)", re.DOTALL)

# Epistemic status markers embedded in topic strings: *(D)*, *(C)*, *(O)*, *(O/C)*
# e.g. "*(D/C)*" or "*(O)*" — stripped from topic; preserved in raw text.
EPISTEMIC_RE = re.compile(r"\*\([DCO/]+\)\*\s*")

# Sentence boundary: period/!/? followed by whitespace and a capital letter,
# dollar sign (LaTeX), backslash, asterisk (bold/italic), or bracket.
# e.g. "X is true. Because Y" → splits before "Because"; "X costs $3. Y" → splits before "Y".
# Used to extract lead_sentence and consequence_sentence without NLP.
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z$\\\*\[])")

# The four canonical content types from specification.md §3.
# Extended types declared in a document's §0 parameter table are added at parse
# time via scan_declared_types() — they do not belong here.
VALID_TYPES = {"Claim", "Scope", "Argument", "Closure"}

# Matches a §0 parameter table row declaring extended content types.
# e.g. "| **Extended content types** | OQ, Hypothesis |" → group(1): "OQ, Hypothesis "
# Undeclared types are treated as Unknown (used but not declared — orphaned variable).
EXTENDED_TYPES_RE = re.compile(r"^\|\s*\*\*Extended content types\*\*\s*\|\s*([^|]+)\|")

# Maps a sub-item's content_type to the semantic edge relation it carries.
# Argument nodes justify their parent (supports); Scope nodes bound it (qualifies);
# Closure nodes defend against attacks (defends). Claim and Unknown use the
# structural default (contains) because no directional semantic applies.
CONTENT_TYPE_TO_RELATION = {
    "Argument": "supported_by",
    "Scope":    "qualified_by",
    "Closure":  "defended_by",
    "Claim":    "contains",
    "Unknown":  "contains",
}

# Fill colours for --color DOT output — one distinct colour per content type
# so the type distribution is visible at a glance in the rendered graph.
CONTENT_TYPE_COLORS = {
    "Claim":    "#4caf50",  # green   — boundary conditions
    "Argument": "#2196f3",  # blue    — justifications
    "Scope":    "#ff9800",  # orange  — qualifiers / bounds
    "Closure":  "#f44336",  # red     — defended attacks
    "Unknown":  "#eeeeee",  # grey    — unlabelled items
}


# ---------------------------------------------------------------------------
# Type declaration scan
# ---------------------------------------------------------------------------

def scan_declared_types(text):
    """Return the set of valid content types for this document.

    Scans the §0 parameter table for an 'Extended content types' row.
    Declared types are added to the canonical four — undeclared types that
    appear in TYPE-LABEL labels remain Unknown, analogous to an undeclared
    variable: used but never defined.

    Declaration format (in §0 parameter table):
        | **Extended content types** | OQ, Hypothesis |

    Accepts the document text string (not a path) — the caller reads the file
    once and passes text to both this function and the line parser.
    """
    declared = set(VALID_TYPES)
    for line in text.splitlines():
        m = EXTENDED_TYPES_RE.match(line.strip())
        if m:
            for raw in m.group(1).split(","):
                name = raw.strip().rstrip("|").strip()
                if name:
                    declared.add(name)
            break  # only the first match is used
    return declared


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _heading_slug(text):
    """Produce a URL-safe slug from a heading string for use in node IDs.

    Strips LaTeX ($...$) and code spans, lowercases, normalises dashes,
    removes non-word characters, collapses spaces to hyphens. Truncated to
    60 chars so IDs remain readable in DOT output.
    """
    t = re.sub(r"\$[^$]*\$", "", text)
    t = re.sub(r"`[^`]*`", "", t)
    t = t.lower()
    t = t.replace("—", "--").replace("–", "-")
    t = re.sub(r"[^\w\s-]", "", t)
    t = re.sub(r"\s+", "-", t.strip())
    return t[:60]


def _make_id(type_, qualifier, counter):
    """Build a deterministic node ID from type prefix, parent qualifier, and counter.

    Format: "type:safe-qualifier:N"
    The counter ensures uniqueness when multiple nodes share the same parent slug.
    """
    safe = re.sub(r"[^a-z0-9_-]", "-", qualifier.lower())[:40]
    return f"{type_}:{safe}:{counter}"


def _split_sentences(text):
    """Split a prose block into sentences using the punctuation-capital heuristic.

    This is structural, not semantic: it splits on sentence-ending punctuation
    followed by an uppercase letter (or LaTeX/markup delimiter). Good enough for
    extracting the first (lead) and last (consequence) sentences of an item block.
    """
    text = text.strip()
    if not text:
        return [""]
    parts = SENTENCE_SPLIT_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def _parse_type_label(body, valid_types=None):
    """Extract (content_type, topic, remainder) from a sub-item body string.

    Expects the body after stripping the leading "- " list marker.
    Returns ("Unknown", "", body) if the label is absent or the type was not
    declared — undeclared types are treated as Unknown (orphaned variable).
    Strips epistemic markers *(D)*, *(C)*, *(O)* from the topic string because
    they annotate confidence level, not content type, and clutter graph metadata.

    valid_types defaults to the canonical four when not supplied.
    """
    if valid_types is None:
        valid_types = VALID_TYPES
    m = LABEL_RE.match(body.strip())
    if not m:
        return "Unknown", "", body.strip()
    raw_type = m.group(1)
    raw_topic = m.group(2).strip()
    remainder = m.group(3).strip()
    content_type = raw_type if raw_type in valid_types else "Unknown"
    topic = EPISTEMIC_RE.sub("", raw_topic).strip().rstrip(",").strip()
    return content_type, topic, remainder


def _node(node_id, node_type, content_type, topic, text, lineno, level=0):
    """Construct a node dict with all required fields.

    lead_sentence and consequence_sentence are extracted here for the graph's
    node payload. They operationalise CLAIM-FIRST and CONSEQUENCE audit checks:
    the graph can be queried for structural compliance without re-parsing prose.
    """
    sentences = _split_sentences(text)
    lead = sentences[0] if sentences else ""
    consequence = sentences[-1] if len(sentences) > 1 else lead
    return {
        "id":                   node_id,
        "type":                 node_type,
        "content_type":         content_type,
        "topic":                topic,
        "lead_sentence":        lead,
        "consequence_sentence": consequence,
        "text":                 text,
        "line":                 lineno,
        "level":                level,
    }


# ---------------------------------------------------------------------------
# Parser state
# ---------------------------------------------------------------------------

@dataclass
class _ParseState:
    """All mutable state threaded through the line-by-line parser.

    Bundling these into one object lets each token handler receive and update
    state without needing nonlocal declarations or a large argument list.
    """
    nodes:        List[dict]         = field(default_factory=list)
    edges:        List[dict]         = field(default_factory=list)
    valid_types:  set                = field(default_factory=set)
    heading_stack: List[Tuple]       = field(default_factory=list)  # (level, node_id)
    depth_stack:  Dict[int, str]     = field(default_factory=dict)  # indent_depth → node_id
    current_def:  Optional[dict]     = None   # accumulates multi-line definition_item
    def_counter:  int                = 0
    sub_counter:  int                = 0


def _flush_def(state: _ParseState) -> None:
    """Emit the accumulated definition_item node and clear the accumulator.

    Called at every token boundary that cannot be a continuation line
    (heading, new def item, sub-item). Safe to call when nothing is open.
    """
    if state.current_def is None:
        return
    text = state.current_def["text"].strip()
    sentences = _split_sentences(text)
    state.current_def["lead_sentence"] = sentences[0] if sentences else ""
    state.current_def["consequence_sentence"] = (
        sentences[-1] if len(sentences) > 1 else state.current_def["lead_sentence"]
    )
    state.current_def["text"] = text
    state.nodes.append(state.current_def)
    state.current_def = None


def _current_heading_id(state: _ParseState) -> str:
    """Return the ID of the most recently opened heading, or '__root__'."""
    return state.heading_stack[-1][1] if state.heading_stack else "__root__"


# ---------------------------------------------------------------------------
# Per-token handlers — one function per Markdown token type.
# Each receives the matched line and state; mutates state in place.
# ---------------------------------------------------------------------------

def _handle_heading(stripped: str, lineno: int, state: _ParseState) -> None:
    """Process a heading line — create a heading node and wire parent edge."""
    _flush_def(state)
    state.depth_stack.clear()  # a new heading resets sub-item depth context

    hm = HEADING_RE.match(stripped)
    level = len(hm.group(1))
    text  = hm.group(2).strip()
    slug  = _heading_slug(text)
    node_id = f"h{level}:{slug}"

    # Deduplicate IDs when two headings produce the same slug (e.g. repeated §Rxx).
    existing = [n["id"] for n in state.nodes if n["type"] == "heading"]
    if node_id in existing:
        node_id = f"{node_id}:{lineno}"

    n = _node(node_id, "heading", "Unknown", "", text, lineno, level=level)
    n["lead_sentence"] = text
    n["consequence_sentence"] = text
    state.nodes.append(n)

    # Pop headings of equal or deeper level so the stack reflects true ancestry.
    while state.heading_stack and state.heading_stack[-1][0] >= level:
        state.heading_stack.pop()
    if state.heading_stack:
        state.edges.append({
            "source": state.heading_stack[-1][1],
            "target": node_id,
            "relation": "contains",
        })
    state.heading_stack.append((level, node_id))


def _handle_numbered_def(stripped: str, lineno: int, state: _ParseState) -> None:
    """Process a numbered bold definition item — open a new definition accumulator."""
    _flush_def(state)
    state.depth_stack.clear()
    state.def_counter += 1

    nm = NUMBERED_RE.match(stripped)
    parent_id  = _current_heading_id(state)
    node_id    = _make_id("def", parent_id, state.def_counter)
    label_text = nm.group(2).strip()
    rest       = nm.group(3).strip()
    full_text  = f"**{label_text}** {rest}".strip()

    state.current_def = _node(node_id, "definition_item", "Claim", label_text, full_text, lineno)
    state.current_def["_parent"] = parent_id
    state.edges.append({"source": parent_id, "target": node_id, "relation": "contains"})


def _handle_bold_claim(stripped: str, lineno: int, state: _ParseState) -> None:
    """Process a standalone **Claim:** paragraph — open a new definition accumulator."""
    _flush_def(state)
    state.depth_stack.clear()
    state.def_counter += 1

    bcm = BOLD_CLAIM_RE.match(stripped)
    parent_id = _current_heading_id(state)
    node_id   = _make_id("def", parent_id, state.def_counter)
    text      = bcm.group(1).strip()

    state.current_def = _node(node_id, "definition_item", "Claim", "", text, lineno)
    state.current_def["_parent"] = parent_id
    state.edges.append({"source": parent_id, "target": node_id, "relation": "contains"})


def _handle_sub_item(line: str, lineno: int, state: _ParseState) -> None:
    """Process a list sub-item — create a typed sub_item node and wire parent edge."""
    _flush_def(state)
    state.sub_counter += 1

    sm     = SUBITEM_RE.match(line)
    indent = len(sm.group(1))
    body   = sm.group(2).strip()
    depth  = indent // 2  # 2-space indent = depth 1, 4-space = depth 2

    content_type, topic, _ = _parse_type_label(body, state.valid_types)
    node_id = _make_id("sub", _current_heading_id(state), state.sub_counter)
    n = _node(node_id, "sub_item", content_type, topic, body, lineno)

    # Depth 0 attaches to the current heading; deeper depths walk up depth_stack.
    # Loop bound: parent_depth decrements from depth-1 to 0, at most depth steps.
    if depth == 0:
        parent_id = _current_heading_id(state)
    else:
        parent_depth = depth - 1
        while parent_depth >= 0 and parent_depth not in state.depth_stack:
            parent_depth -= 1
        parent_id = state.depth_stack.get(parent_depth, _current_heading_id(state))

    relation = CONTENT_TYPE_TO_RELATION.get(content_type, "contains")
    state.edges.append({"source": parent_id, "target": node_id, "relation": relation})

    # Register at this depth; evict deeper entries — depth N supersedes depths > N.
    state.depth_stack[depth] = node_id
    for k in list(state.depth_stack.keys()):
        if k > depth:
            del state.depth_stack[k]

    state.nodes.append(n)


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_document(path):
    """Walk the document line by line and emit nodes and edges.

    State machine — three modes:
      in_fence        : inside a fenced code/mermaid block; skip all lines
      current_def set : accumulating a multi-line definition_item body
      normal          : dispatch each line to its per-token handler

    ```mermaid
    stateDiagram-v2
        [*] --> normal
        normal --> in_fence : FENCE_RE
        in_fence --> normal : line starts with fence_marker
        normal --> accumulating_def : NUMBERED / BOLD_CLAIM
        accumulating_def --> accumulating_def : continuation line
        accumulating_def --> accumulating_def : NUMBERED / BOLD_CLAIM (flush + new def)
        accumulating_def --> normal : HEADING / SUB_ITEM (flush)
        normal --> [*] : EOF
        accumulating_def --> [*] : EOF (flush)
    ```

    Returns (nodes, edges) as plain lists of dicts.
    """
    if not path:
        raise ValueError("path must be a non-empty string")
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as e:
        print(f"Error: could not read file — {path} ({e.strerror})", file=sys.stderr)
        sys.exit(1)

    state = _ParseState(valid_types=scan_declared_types(text))
    lines = text.splitlines()

    in_fence     = False
    fence_marker = ""

    for lineno, line in enumerate(lines, 1):
        stripped = line.rstrip()

        # Fence entry/exit — skip everything inside code blocks.
        if not in_fence and FENCE_RE.match(stripped):
            in_fence = True
            fence_marker = FENCE_RE.match(stripped).group(1)
            continue
        if in_fence:
            if stripped.startswith(fence_marker):
                in_fence = False
            continue

        if HEADING_RE.match(stripped):
            _handle_heading(stripped, lineno, state)
        elif NUMBERED_RE.match(stripped):
            _handle_numbered_def(stripped, lineno, state)
        elif BOLD_CLAIM_RE.match(stripped):
            _handle_bold_claim(stripped, lineno, state)
        elif SUBITEM_RE.match(line):
            _handle_sub_item(line, lineno, state)
        elif state.current_def is not None and stripped:
            # Continuation line — append to open definition item body.
            state.current_def["text"] += " " + stripped

    _flush_def(state)
    return state.nodes, state.edges


# ---------------------------------------------------------------------------
# Graph construction and serialisation
# ---------------------------------------------------------------------------

def build_graph(nodes, edges):
    """Wrap the node/edge lists in a NetworkX DiGraph.

    All node dict fields are stored as node attributes, enabling downstream
    NetworkX queries (ancestors, descendants, subgraph, topological_sort, etc.)
    directly against content type and topic metadata.
    """
    if not isinstance(nodes, list):
        raise TypeError("nodes must be a list")
    if not isinstance(edges, list):
        raise TypeError("edges must be a list")
    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n["id"], **{k: v for k, v in n.items() if k != "id"})
    for e in edges:
        G.add_edge(e["source"], e["target"], relation=e["relation"])
    return G


def to_json(G):
    """Serialise the graph to NetworkX node-link JSON format.

    The node-link format is the standard NetworkX interchange format and is
    directly loadable by D3.js force-directed graph layouts.
    """
    data = nx.node_link_data(G, edges="links")
    return json.dumps(data, ensure_ascii=False, indent=2)


def to_dot(G, color=False):
    """Serialise the graph to DOT format for Graphviz rendering.

    When color=True, each node is filled with the colour for its content_type
    (from CONTENT_TYPE_COLORS). This makes the type distribution visible at a
    glance without needing to read individual node labels.

    Node IDs use colons as separators (e.g. "h2:section-title:1"). Graphviz
    interprets colons in node names as port separators even inside quotes, so
    IDs are sanitised to double-underscores for DOT output only — the graph
    structure is unaffected.

    Uses a hand-written DOT emitter (pydot's nx bridge doesn't sanitise IDs).
    """
    def _dot_id(node_id):
        # Replace colons with double-underscores to avoid Graphviz port-separator misparse.
        return node_id.replace(":", "__")

    lines = ["digraph G {"]
    if color:
        lines.append("  node [style=filled];")
    for n in G.nodes():
        attrs = G.nodes[n]
        label = (attrs.get("topic") or attrs.get("lead_sentence", ""))[:60]
        label = label.replace('"', '\\"').replace("\n", " ")
        ct = attrs.get("content_type", "Unknown")
        attr_str = f'label="{label}"'
        if color:
            fill = CONTENT_TYPE_COLORS.get(ct, CONTENT_TYPE_COLORS["Unknown"])
            attr_str += f' fillcolor="{fill}" style="filled"'
        lines.append(f'  "{_dot_id(n)}" [{attr_str}];')
    for u, v, data in G.edges(data=True):
        rel = data.get("relation", "")
        lines.append(f'  "{_dot_id(u)}" -> "{_dot_id(v)}" [label="{rel}"];')
    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extract a typed argument DAG from a Markdown document."
    )
    parser.add_argument("document", help="Path to the Markdown document")
    parser.add_argument(
        "--output", choices=["json", "dot", "both"], default="json",
        help="Output format: json (node-link), dot (Graphviz), or both"
    )
    parser.add_argument(
        "--color", action="store_true",
        help="Apply content-type fill colours to DOT output nodes"
    )
    args = parser.parse_args()

    nodes, edges = parse_document(args.document)
    G = build_graph(nodes, edges)

    if args.output in ("json", "both"):
        print(to_json(G))
    if args.output in ("dot", "both"):
        if args.output == "both":
            print("---DOT---", file=sys.stderr)
        print(to_dot(G, color=args.color))


if __name__ == "__main__":
    main()
