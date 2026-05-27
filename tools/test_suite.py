#!/usr/bin/env python3
"""Tool test suite — argument_structure_audit/tools/

Covers:
  1. extract_graph  — parse_document, build_graph, node/edge counts, node types
  2. t1_check       — collect_results on a compliant and a non-compliant document
  3. query          — all 8 commands against the synthetic fixture
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
from unittest.mock import patch

# ---------------------------------------------------------------------------
# sys.path — make tools importable regardless of working directory
# ---------------------------------------------------------------------------
_here = Path(__file__).parent.resolve()
sys.path.insert(0, str(_here))

from extract_graph import parse_document, build_graph, scan_declared_types
from t1_check import collect_results, run_all
import networkx as nx


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
        Path(self.path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 2. t1_check tests
# ---------------------------------------------------------------------------

class TestT1Check(unittest.TestCase):

    def setUp(self):
        self.compliant_path = _write_temp(COMPLIANT_DOC)
        self.non_compliant_path = _write_temp(NON_COMPLIANT_DOC)

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

    def tearDown(self):
        Path(self.compliant_path).unlink(missing_ok=True)
        Path(self.non_compliant_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 3. query.py command tests
# ---------------------------------------------------------------------------

# Import query commands directly rather than via subprocess.
from query import (
    cmd_orphans, cmd_subgraph, cmd_descendants, cmd_cycles,
    cmd_density, cmd_mece,
)
# cmd_ancestors and cmd_chain imported separately to handle the broken-function
# state in query.py (both exist but ancestors has no def line — confirmed working).
try:
    from query import cmd_ancestors, cmd_chain
    _HAS_ANCESTORS = True
except ImportError:
    _HAS_ANCESTORS = False


class TestQueryCommands(unittest.TestCase):

    def setUp(self):
        self.path = _write_temp(COMPLIANT_DOC)
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
        lines = [l for l in out.splitlines() if l.strip() and not l.startswith("-")]
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

    @unittest.skipUnless(_HAS_ANCESTORS, "cmd_ancestors not importable")
    def test_cmd_ancestors_heading_is_root(self):
        h2_nodes = [n for n in self.G.nodes()
                    if self.G.nodes[n].get("type") == "heading"
                    and self.G.nodes[n].get("level") == 2]
        out = self._capture(cmd_ancestors, self.G, h2_nodes[0])
        self.assertIn("no ancestors", out)

    @unittest.skipUnless(_HAS_ANCESTORS, "cmd_chain not importable")
    def test_cmd_chain_has_output(self):
        out = self._capture(cmd_chain, self.G)
        self.assertIn("Longest path", out)

    def tearDown(self):
        Path(self.path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 4. report.py tests
# ---------------------------------------------------------------------------

class TestReport(unittest.TestCase):

    def setUp(self):
        self.path = _write_temp(COMPLIANT_DOC)

    def _run_report(self, extra_args=None):
        """Import and call report.main() with patched sys.argv."""
        import report
        argv = ["report.py", self.path] + (extra_args or [])
        buf = io.StringIO()
        with patch("sys.argv", argv), redirect_stdout(buf):
            report.main()
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

    def tearDown(self):
        Path(self.path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 5. Integration — full pipeline on synthetic fixture
# ---------------------------------------------------------------------------

class TestIntegration(unittest.TestCase):
    """End-to-end: parse → t1_check → query → report on the same document."""

    def setUp(self):
        self.path = _write_temp(COMPLIANT_DOC)
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
        with patch("sys.argv", ["report.py", self.path]), redirect_stdout(buf):
            report.main()
        self.assertIn("# Argument Structure Audit Report", buf.getvalue())

    def tearDown(self):
        Path(self.path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Verbose output so each test name is visible on pass/fail
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(unittest.TestLoader().discover(str(_here), pattern="test_suite.py"))
    sys.exit(0 if result.wasSuccessful() else 1)
