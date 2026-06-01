#!/usr/bin/env python3
"""Tool test suite — argument_structure_audit/tools/

Covers:
  1. extract_graph  — parse_document, build_graph, node/edge counts, node types
  2. t1_check       — collect_results on a compliant and a non-compliant document
  3. query          — all 10 commands against the synthetic fixture
  4. report         — report.py main() output structure (summary and full mode)
  5. Integration    — full pipeline on synthetic fixture: t1_check → query → report

Run from the repository root:
    python3 argument_structure_audit/tools/test_suite.py
Or from the tools directory:
    python3 test_suite.py

Exit 0 = all tests pass. Exit 1 = at least one failure (details printed).
No third-party test framework required.
"""

import sys
import io
import textwrap
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr

# ---------------------------------------------------------------------------
# sys.path — make tools importable regardless of working directory
# ---------------------------------------------------------------------------
_here = Path(__file__).parent.resolve()
sys.path.insert(0, str(_here))

from extract_graph import parse_document, build_graph, scan_declared_types
from t1_check import collect_results, run_all
import networkx as nx
from query import (
    cmd_orphans, cmd_subgraph, cmd_descendants, cmd_cycles,
    cmd_density, cmd_mece, cmd_refs, cmd_shared,
    cmd_ancestors, cmd_chain,
    _parse_refs, _split_citation, _resolve_node_id,
)


# ---------------------------------------------------------------------------
# Synthetic fixture document
# ---------------------------------------------------------------------------

COMPLIANT_DOC = textwrap.dedent("""\
    ## Section One

    1. **First claim** The core assertion holds under all conditions.
       - *Argument (supporting evidence):* Evidence A supports this. This rules out counter-position X.
       - *Scope (boundary condition):* Applies only within domain Y. This qualifies the claim scope.
       - *Closure (defence):* Objection Z is addressed by W. This closes the objection.

    ## Section Two

    1. **Second claim** The secondary assertion follows from the first.
       - *Argument (empirical basis):* Data confirms the pattern. This strengthens the position.
       - *Claim (sub-claim):* A narrower point within this claim. This narrows the scope further.
""")

NON_COMPLIANT_DOC = textwrap.dedent("""\
    ## Good Section

    1. **Good claim** This is a well-formed claim.
       - *Argument (valid):* Supports the claim. This rules out alternatives.

    ## Bad Section

    *Argument (flat prose):* This argument is not in a list item.

    #### Skipped Heading Level

    - unlabelled item without a type label
""")

# Fixture document with known prose cross-references for refs/shared tests.
# Sections A and B each cite §C-item; Section B also cites §D-item.
# A fenced block contains a citation that must NOT be counted.
CITATION_DOC = textwrap.dedent("""\
    ## Section A

    1. **Claim A** The first assertion.
       - *Argument (basis):* Evidence supports this. *[→ §C-item]* This rules out X.

    ## Section B

    1. **Claim B** The second assertion.
       - *Argument (basis):* Further evidence. *[→ §C-item, §D-item]* This rules out Y.

    ## Section C

    1. **Claim C** The referenced item.
       - *Scope (limit):* Applies here only. This qualifies the claim.

    ```python
    # This citation inside a fenced block must not be counted:
    # [→ §C-item]
    ```
""")


def _write_temp(content):
    """Write content to a temp file and return its path as a string."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
    f.write(content)
    f.flush()
    f.close()
    return f.name


# ---------------------------------------------------------------------------
# 1. extract_graph tests
# ---------------------------------------------------------------------------

class TestExtractGraph(unittest.TestCase):

    def setUp(self):
        self.path = _write_temp(COMPLIANT_DOC)
        self.addCleanup(Path(self.path).unlink, missing_ok=True)
        self.nodes, self.edges = parse_document(self.path)
        self.G = build_graph(self.nodes, self.edges)

    def test_node_count_positive(self):
        self.assertGreater(len(self.nodes), 0)

    def test_edge_count_positive(self):
        self.assertGreater(len(self.edges), 0)

    def test_graph_is_dag(self):
        self.assertTrue(nx.is_directed_acyclic_graph(self.G))

    def test_heading_nodes_present(self):
        headings = [n for n in self.G.nodes() if self.G.nodes[n].get("type") == "heading"]
        self.assertGreaterEqual(len(headings), 2)

    def test_sub_item_nodes_present(self):
        sub_items = [n for n in self.G.nodes() if self.G.nodes[n].get("type") == "sub_item"]
        self.assertGreater(len(sub_items), 0)

    def test_argument_nodes_have_supports_edge(self):
        for u, v, data in self.G.edges(data=True):
            if self.G.nodes[v].get("content_type") == "Argument":
                self.assertEqual(data.get("relation"), "supports")

    def test_scope_nodes_have_qualifies_edge(self):
        for u, v, data in self.G.edges(data=True):
            if self.G.nodes[v].get("content_type") == "Scope":
                self.assertEqual(data.get("relation"), "qualifies")

    def test_closure_nodes_have_defends_edge(self):
        for u, v, data in self.G.edges(data=True):
            if self.G.nodes[v].get("content_type") == "Closure":
                self.assertEqual(data.get("relation"), "defends")

    def test_no_orphan_sub_items(self):
        orphans = [
            n for n in self.G.nodes()
            if self.G.in_degree(n) == 0 and self.G.nodes[n].get("type") != "heading"
        ]
        self.assertEqual(orphans, [])

    def test_node_line_numbers_positive(self):
        for n in self.G.nodes():
            self.assertGreater(self.G.nodes[n].get("line", 0), 0, f"Node {n} missing line number")

    def test_missing_file_exits(self):
        with self.assertRaises(SystemExit):
            parse_document("/nonexistent/path/document.md")

    def test_build_graph_rejects_non_list(self):
        with self.assertRaises(TypeError):
            build_graph("not a list", [])

    def test_scan_declared_types_canonical(self):
        declared = scan_declared_types(COMPLIANT_DOC)
        # Canonical types always present in a compliant doc (no extended types declared)
        self.assertIn("Claim", declared)

    def tearDown(self):
        pass  # cleanup registered via addCleanup in setUp


# ---------------------------------------------------------------------------
# 2. t1_check tests
# ---------------------------------------------------------------------------

class TestT1Check(unittest.TestCase):

    def setUp(self):
        self.compliant_path = _write_temp(COMPLIANT_DOC)
        self.addCleanup(Path(self.compliant_path).unlink, missing_ok=True)
        self.non_compliant_path = _write_temp(NON_COMPLIANT_DOC)
        self.addCleanup(Path(self.non_compliant_path).unlink, missing_ok=True)

    def _results(self, path):
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        return collect_results(lines, Path(path).name)

    def test_compliant_rc1_passes(self):
        results = self._results(self.compliant_path)
        fails = [f for f in results["RC1"][0] if f.result == "Fail"]
        self.assertEqual(fails, [])

    def test_non_compliant_rc1_fails(self):
        results = self._results(self.non_compliant_path)
        fails = [f for f in results["RC1"][0] if f.result == "Fail"]
        self.assertGreater(len(fails), 0)

    def test_non_compliant_content_type_fails(self):
        results = self._results(self.non_compliant_path)
        fails = [f for f in results["CONTENT-TYPE"][0] if f.result == "Fail"]
        self.assertGreater(len(fails), 0)

    def test_non_compliant_type_label_fails(self):
        results = self._results(self.non_compliant_path)
        fails = [f for f in results["TYPE-LABEL"][0] if f.result == "Fail"]
        self.assertGreater(len(fails), 0)

    def test_compliant_no_critical_findings(self):
        results = self._results(self.compliant_path)
        criticals = [
            f for name in results
            for f in results[name][0]
            if f.severity == "CRITICAL"
        ]
        self.assertEqual(criticals, [])

    def test_all_checks_present(self):
        results = self._results(self.compliant_path)
        expected = {"RC1", "CONTENT-TYPE", "CLAIM-FIRST", "CONSEQUENCE", "TYPE-LABEL", "RC2", "RC3"}
        self.assertEqual(set(results.keys()), expected)

    def test_run_all_exit_0_on_compliant(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = run_all(self.compliant_path)
        self.assertEqual(code, 0)

    def test_run_all_verbose_emits_escalated_items(self):
        # NON_COMPLIANT_DOC has no sub-items with multi-sentence consequence,
        # so use COMPLIANT_DOC which has Escalated CONSEQUENCE items.
        buf = io.StringIO()
        with redirect_stdout(buf):
            run_all(self.compliant_path, verbose=True)
        out = buf.getvalue()
        # With --verbose, escalated CONSEQUENCE or CLAIM-FIRST lines include
        # a line number (digit) followed by a bracketed note excerpt.
        import re
        self.assertTrue(
            re.search(r"\d+\s+\[", out),
            "Expected verbose item lines (lineno + note) in output"
        )


# ---------------------------------------------------------------------------
# 3. query.py command tests
# ---------------------------------------------------------------------------


class TestQueryCommands(unittest.TestCase):

    def setUp(self):
        self.path = _write_temp(COMPLIANT_DOC)
        self.addCleanup(Path(self.path).unlink, missing_ok=True)
        nodes, edges = parse_document(self.path)
        self.G = build_graph(nodes, edges)

    def _capture(self, fn, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            fn(*args)
        return buf.getvalue()

    def test_cmd_orphans_no_output_on_compliant(self):
        out = self._capture(cmd_orphans, self.G)
        self.assertIn("No orphans", out)

    def test_cmd_cycles_dag_confirmed(self):
        out = self._capture(cmd_cycles, self.G)
        self.assertIn("DAG: yes", out)

    def test_cmd_density_has_section_row(self):
        out = self._capture(cmd_density, self.G)
        # At least one section row should appear after the header line
        lines = [ln for ln in out.splitlines() if ln.strip() and not ln.startswith("-")]
        self.assertGreater(len(lines), 1)

    def test_cmd_subgraph_valid_slug(self):
        h2_nodes = [n for n in self.G.nodes()
                    if self.G.nodes[n].get("type") == "heading"
                    and self.G.nodes[n].get("level") == 2]
        self.assertGreater(len(h2_nodes), 0)
        # Use the full first heading ID as the slug to avoid ambiguity
        slug = h2_nodes[0]
        out = self._capture(cmd_subgraph, self.G, slug)
        self.assertIn("Subgraph rooted at", out)

    def test_cmd_subgraph_bad_slug_exits(self):
        with self.assertRaises(SystemExit):
            buf = io.StringIO()
            with redirect_stderr(buf):
                cmd_subgraph(self.G, "zzz_no_such_heading_zzz")

    def test_cmd_subgraph_empty_slug_raises(self):
        with self.assertRaises(ValueError):
            cmd_subgraph(self.G, "")

    def test_cmd_descendants_leaf_message(self):
        # A heading with no children of its own type (leaf in subgraph sense)
        # — find a sub_item node and check descendants message
        sub_items = [n for n in self.G.nodes() if self.G.nodes[n].get("type") == "sub_item"]
        self.assertGreater(len(sub_items), 0)
        node_id = sub_items[0]
        out = self._capture(cmd_descendants, self.G, node_id)
        # Either "has no descendants" or a table — both are valid
        self.assertTrue("descendants" in out.lower())

    def test_cmd_descendants_empty_id_raises(self):
        with self.assertRaises(ValueError):
            cmd_descendants(self.G, "")

    def test_cmd_mece_has_output(self):
        out = self._capture(cmd_mece, self.G)
        self.assertGreater(len(out.strip()), 0)

    def test_cmd_ancestors_heading_is_root(self):
        h2_nodes = [n for n in self.G.nodes()
                    if self.G.nodes[n].get("type") == "heading"
                    and self.G.nodes[n].get("level") == 2]
        out = self._capture(cmd_ancestors, self.G, h2_nodes[0])
        self.assertIn("no ancestors", out)

    def test_cmd_chain_has_output(self):
        out = self._capture(cmd_chain, self.G)
        self.assertIn("Longest path", out)


# ---------------------------------------------------------------------------
# 3b. query.py — prose cross-reference and helper tests
# ---------------------------------------------------------------------------

class TestQueryProseCommands(unittest.TestCase):

    def setUp(self):
        self.path = _write_temp(CITATION_DOC)
        self.addCleanup(Path(self.path).unlink, missing_ok=True)

    def _capture(self, fn, *args, **kwargs):
        buf = io.StringIO()
        with redirect_stdout(buf):
            fn(*args, **kwargs)
        return buf.getvalue()

    # _split_citation ---------------------------------------------------------

    def test_split_citation_single(self):
        self.assertEqual(_split_citation("§C-item"), ["§C-item"])

    def test_split_citation_compound(self):
        result = _split_citation("§C-item, §D-item")
        self.assertEqual(result, ["§C-item", "§D-item"])

    def test_split_citation_preserves_parens(self):
        # Commas inside parentheses must not split
        result = _split_citation("§2 Argument (a, b), OQ-EC.4")
        self.assertEqual(result, ["§2 Argument (a, b)", "OQ-EC.4"])

    def test_split_citation_empty(self):
        self.assertEqual(_split_citation(""), [])

    def test_split_citation_whitespace_stripped(self):
        result = _split_citation("  §C-item ,  §D-item  ")
        self.assertEqual(result, ["§C-item", "§D-item"])

    # _parse_refs -------------------------------------------------------------

    def test_parse_refs_finds_citations(self):
        inverted = _parse_refs(self.path)
        self.assertGreater(len(inverted), 0)

    def test_parse_refs_excludes_fenced_block(self):
        # The citation inside the ```python block must not appear
        inverted = _parse_refs(self.path)
        # Fenced block contains [→ §C-item] on its own line; if excluded
        # correctly, §C-item appears only via the prose lines, not three times.
        # Count total occurrences across all (target, section) pairs.
        total = sum(len(locs) for key, locs in inverted.items() if "§C-item" in key)
        # Section A line and Section B compound line = 2 occurrences max
        self.assertLessEqual(total, 2)

    def test_parse_refs_section_tracking(self):
        inverted = _parse_refs(self.path)
        # §C-item is cited from both Section A and Section B
        sections = set()
        for key, locs in inverted.items():
            if "§C-item" in key:
                for _, section in locs:
                    sections.add(section)
        self.assertGreaterEqual(len(sections), 2)

    def test_parse_refs_missing_file_exits(self):
        with self.assertRaises(SystemExit):
            _parse_refs("/nonexistent/path/document.md")

    # _resolve_node_id --------------------------------------------------------

    def test_resolve_node_id_exact_match(self):
        path = _write_temp(COMPLIANT_DOC)
        self.addCleanup(Path(path).unlink, missing_ok=True)
        nodes, edges = parse_document(path)
        G = build_graph(nodes, edges)
        h2 = [n for n in G.nodes() if G.nodes[n].get("type") == "heading"
              and G.nodes[n].get("level") == 2][0]
        self.assertEqual(_resolve_node_id(G, h2), h2)

    def test_resolve_node_id_not_found_exits(self):
        path = _write_temp(COMPLIANT_DOC)
        self.addCleanup(Path(path).unlink, missing_ok=True)
        nodes, edges = parse_document(path)
        G = build_graph(nodes, edges)
        with self.assertRaises(SystemExit):
            buf = io.StringIO()
            with redirect_stderr(buf):
                _resolve_node_id(G, "zzz_no_such_node_zzz")

    def test_resolve_node_id_ambiguous_exits(self):
        path = _write_temp(COMPLIANT_DOC)
        self.addCleanup(Path(path).unlink, missing_ok=True)
        nodes, edges = parse_document(path)
        G = build_graph(nodes, edges)
        # "h2:" matches every h2 heading node — guaranteed ambiguous
        with self.assertRaises(SystemExit):
            buf = io.StringIO()
            with redirect_stderr(buf):
                _resolve_node_id(G, "h2:")

    # cmd_refs ----------------------------------------------------------------

    def test_cmd_refs_full_matrix_has_output(self):
        out = self._capture(cmd_refs, self.path)
        self.assertIn("citation", out)

    def test_cmd_refs_target_finds_match(self):
        out = self._capture(cmd_refs, self.path, "§C-item")
        self.assertIn("§C-item", out)

    def test_cmd_refs_target_no_match_exits(self):
        with self.assertRaises(SystemExit):
            buf = io.StringIO()
            with redirect_stderr(buf):
                cmd_refs(self.path, "zzz_no_such_target_zzz")

    def test_cmd_refs_no_citations_doc(self):
        path = _write_temp(COMPLIANT_DOC)
        self.addCleanup(Path(path).unlink, missing_ok=True)
        out = self._capture(cmd_refs, path)
        self.assertIn("No prose cross-references", out)

    # cmd_shared --------------------------------------------------------------

    def test_cmd_shared_finds_shared_premise(self):
        # §C-item is cited from Section A and Section B — shared at min=2
        out = self._capture(cmd_shared, self.path, 2)
        self.assertIn("§C-item", out)

    def test_cmd_shared_default_threshold_no_result(self):
        # Only 2 sections in CITATION_DOC — nothing meets min=3
        out = self._capture(cmd_shared, self.path, 3)
        self.assertIn("No shared premises", out)

    def test_cmd_shared_invalid_min_raises(self):
        with self.assertRaises(ValueError):
            cmd_shared(self.path, 0)


# ---------------------------------------------------------------------------
# 4. report.py tests
# ---------------------------------------------------------------------------

class TestReport(unittest.TestCase):

    def setUp(self):
        self.path = _write_temp(COMPLIANT_DOC)
        self.addCleanup(Path(self.path).unlink, missing_ok=True)

    def _run_report(self, extra_args=None):
        import report
        buf = io.StringIO()
        with redirect_stdout(buf):
            report.main([self.path] + (extra_args or []))
        return buf.getvalue()

    def test_report_has_header(self):
        out = self._run_report()
        self.assertIn("# Argument Structure Audit Report", out)

    def test_report_has_t1_summary(self):
        out = self._run_report()
        self.assertIn("## T1 Check Summary", out)

    def test_report_has_density(self):
        out = self._run_report()
        self.assertIn("## Section Density", out)

    def test_report_has_structural_health(self):
        out = self._run_report()
        self.assertIn("## Structural Health", out)

    def test_report_has_top_nodes(self):
        out = self._run_report()
        self.assertIn("## Top Load-Bearing Nodes", out)

    def test_report_full_mode_has_findings(self):
        out = self._run_report(["--full"])
        self.assertIn("## Critical and Significant Findings", out)

    def test_report_node_count_in_header(self):
        out = self._run_report()
        self.assertIn("Nodes:", out)


# ---------------------------------------------------------------------------
# 5. Integration — full pipeline on synthetic fixture
# ---------------------------------------------------------------------------

class TestIntegration(unittest.TestCase):
    """End-to-end: parse → t1_check → query → report on the same document."""

    def setUp(self):
        self.path = _write_temp(COMPLIANT_DOC)
        self.addCleanup(Path(self.path).unlink, missing_ok=True)
        self.nodes, self.edges = parse_document(self.path)
        self.G = build_graph(self.nodes, self.edges)
        lines = Path(self.path).read_text(encoding="utf-8").splitlines()
        self.check_results = collect_results(lines, Path(self.path).name)

    def test_dag_is_valid(self):
        self.assertTrue(nx.is_directed_acyclic_graph(self.G))

    def test_no_critical_t1_findings(self):
        criticals = [
            f for name in self.check_results
            for f in self.check_results[name][0]
            if f.severity == "CRITICAL"
        ]
        self.assertEqual(criticals, [])

    def test_no_orphans(self):
        orphans = [
            n for n in self.G.nodes()
            if self.G.in_degree(n) == 0 and self.G.nodes[n].get("type") != "heading"
        ]
        self.assertEqual(orphans, [])

    def test_topological_sort_succeeds(self):
        # Should not raise NetworkXUnfeasible
        order = list(nx.topological_sort(self.G))
        self.assertGreater(len(order), 0)

    def test_ancestors_descendants_disjoint(self):
        # For any node: its ancestors and descendants should not overlap
        for n in list(self.G.nodes())[:10]:  # sample first 10 to keep it fast
            ancs = nx.ancestors(self.G, n)
            desc = nx.descendants(self.G, n)
            self.assertEqual(ancs & desc, set(), f"Overlap for node {n}")

    def test_report_runs_without_error(self):
        import report
        buf = io.StringIO()
        with redirect_stdout(buf):
            report.main([self.path])
        self.assertIn("# Argument Structure Audit Report", buf.getvalue())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Verbose output so each test name is visible on pass/fail
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(unittest.TestLoader().discover(str(_here), pattern="test_suite.py"))
    sys.exit(0 if result.wasSuccessful() else 1)
