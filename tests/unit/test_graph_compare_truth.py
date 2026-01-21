"""Unit tests for compare_to_truth functionality."""

from causaliq_core.graph import DAG, PDAG
from pandas import DataFrame

from causaliq_analysis.graph import _to_pdag, compare_to_truth


def test_compare_to_truth_all_correct():
    """Test comparison when all edges match the true graph."""
    true_dag = DAG(["A", "B", "C"], [("A", "->", "B"), ("B", "->", "C")])

    # averaged DataFrame with edges matching truth
    averaged = DataFrame(
        [
            {
                "node_a": "A",
                "node_b": "B",
                "p_a_to_b": 1.0,
                "p_b_to_a": 0.0,
                "p_undirected": 0.0,
                "p_no_edge": 0.0,
                "h_exist": 0.0,
                "h_orient": 0.0,
            },
            {
                "node_a": "B",
                "node_b": "C",
                "p_a_to_b": 1.0,
                "p_b_to_a": 0.0,
                "p_undirected": 0.0,
                "p_no_edge": 0.0,
                "h_exist": 0.0,
                "h_orient": 0.0,
            },
        ]
    )

    result = compare_to_truth(averaged, true_dag)

    assert len(result) == 2
    assert list(result["true_edge"]) == ["a_to_b", "a_to_b"]
    assert list(result["exist_ok"]) == [True, True]
    assert list(result["orient_ok"]) == [True, True]


def test_compare_to_truth_wrong_direction():
    """Test comparison when edge direction is wrong."""
    true_dag = DAG(["A", "B"], [("A", "->", "B")])

    # averaged DataFrame with wrong direction
    averaged = DataFrame(
        [
            {
                "node_a": "A",
                "node_b": "B",
                "p_a_to_b": 0.2,
                "p_b_to_a": 0.8,
                "p_undirected": 0.0,
                "p_no_edge": 0.0,
                "h_exist": 0.0,
                "h_orient": 0.722,
            },
        ]
    )

    result = compare_to_truth(averaged, true_dag)

    assert result.iloc[0]["true_edge"] == "a_to_b"
    assert result.iloc[0]["exist_ok"] == True  # noqa: E712
    assert result.iloc[0]["orient_ok"] == False  # noqa: E712


def test_compare_to_truth_missing_edge():
    """Test comparison when predicted edge doesn't exist in truth."""
    true_dag = DAG(["A", "B"], [])  # No edge in true graph

    # averaged DataFrame predicts an edge
    averaged = DataFrame(
        [
            {
                "node_a": "A",
                "node_b": "B",
                "p_a_to_b": 0.7,
                "p_b_to_a": 0.2,
                "p_undirected": 0.1,
                "p_no_edge": 0.0,
                "h_exist": 0.0,
                "h_orient": 0.8,
            },
        ]
    )

    result = compare_to_truth(averaged, true_dag)

    assert result.iloc[0]["true_edge"] == "no_edge"
    assert result.iloc[0]["exist_ok"] == False  # noqa: E712
    assert result.iloc[0]["orient_ok"] is None


def test_compare_to_truth_extra_edge_in_truth():
    """Test when truth has edge but prediction says no edge."""
    true_dag = DAG(["A", "B"], [("A", "->", "B")])

    # averaged DataFrame with high no_edge probability
    averaged = DataFrame(
        [
            {
                "node_a": "A",
                "node_b": "B",
                "p_a_to_b": 0.1,
                "p_b_to_a": 0.1,
                "p_undirected": 0.1,
                "p_no_edge": 0.7,
                "h_exist": 0.88,
                "h_orient": 0.95,
            },
        ]
    )

    result = compare_to_truth(averaged, true_dag)

    assert result.iloc[0]["true_edge"] == "a_to_b"
    assert result.iloc[0]["exist_ok"] == False  # noqa: E712
    assert result.iloc[0]["orient_ok"] is None


def test_compare_to_truth_undirected_matches_any():
    """Test that undirected in prediction matches any direction in truth."""
    true_dag = DAG(["A", "B"], [("A", "->", "B")])

    # averaged DataFrame predicts undirected
    averaged = DataFrame(
        [
            {
                "node_a": "A",
                "node_b": "B",
                "p_a_to_b": 0.2,
                "p_b_to_a": 0.2,
                "p_undirected": 0.5,
                "p_no_edge": 0.1,
                "h_exist": 0.469,
                "h_orient": 1.0,
            },
        ]
    )

    result = compare_to_truth(averaged, true_dag)

    assert result.iloc[0]["true_edge"] == "a_to_b"
    assert result.iloc[0]["exist_ok"] == True  # noqa: E712
    # Undirected prediction with directed truth - failed to discover direction
    assert result.iloc[0]["orient_ok"] == False  # noqa: E712


def test_compare_to_truth_reverse_ordered_nodes():
    """Test when true edge is B->A but averaged has node_a=A, node_b=B."""
    true_dag = DAG(["A", "B"], [("B", "->", "A")])  # B -> A

    averaged = DataFrame(
        [
            {
                "node_a": "A",
                "node_b": "B",
                "p_a_to_b": 0.1,
                "p_b_to_a": 0.8,
                "p_undirected": 0.05,
                "p_no_edge": 0.05,
                "h_exist": 0.286,
                "h_orient": 0.6,
            },
        ]
    )

    result = compare_to_truth(averaged, true_dag)

    # True edge is B->A, which is "b_to_a" from the perspective of (A, B)
    assert result.iloc[0]["true_edge"] == "b_to_a"
    assert result.iloc[0]["exist_ok"] == True  # noqa: E712
    assert result.iloc[0]["orient_ok"] == True  # noqa: E712


def test_compare_to_truth_preserves_original_columns():
    """Test that original DataFrame columns are preserved."""
    true_dag = DAG(["A", "B"], [("A", "->", "B")])

    averaged = DataFrame(
        [
            {
                "node_a": "A",
                "node_b": "B",
                "p_a_to_b": 0.9,
                "p_b_to_a": 0.05,
                "p_undirected": 0.03,
                "p_no_edge": 0.02,
                "h_exist": 0.141,
                "h_orient": 0.4,
            },
        ]
    )

    result = compare_to_truth(averaged, true_dag)

    # All original columns should be preserved
    assert "node_a" in result.columns
    assert "node_b" in result.columns
    assert "p_a_to_b" in result.columns
    assert "p_b_to_a" in result.columns
    assert "p_undirected" in result.columns
    assert "p_no_edge" in result.columns
    assert "h_exist" in result.columns
    assert "h_orient" in result.columns

    # Values should be preserved
    assert result.iloc[0]["p_a_to_b"] == 0.9
    assert result.iloc[0]["h_exist"] == 0.141


def test_to_pdag_with_pdag_input():
    """Test _to_pdag returns PDAG unchanged when given a PDAG."""
    # Create a PDAG (not a DAG)
    pdag = PDAG(["A", "B"], [("A", "-", "B")])  # Undirected edge

    result = _to_pdag(pdag)

    # Should return the same object unchanged
    assert result is pdag


def test_compare_to_truth_with_undirected_edge_a_to_b():
    """Test compare_to_truth when true graph has undirected edge (A-B form)."""
    # Create a PDAG with an undirected edge
    true_pdag = PDAG(["A", "B"], [("A", "-", "B")])

    averaged = DataFrame(
        [
            {
                "node_a": "A",
                "node_b": "B",
                "p_a_to_b": 0.3,
                "p_b_to_a": 0.3,
                "p_undirected": 0.4,
                "p_no_edge": 0.0,
                "h_exist": 0.0,
                "h_orient": 1.0,
            },
        ]
    )

    result = compare_to_truth(averaged, true_pdag)

    # True edge should be undirected
    assert result.iloc[0]["true_edge"] == "undirected"
    assert result.iloc[0]["exist_ok"] == True  # noqa: E712
    # Undirected in truth matches undirected prediction
    assert result.iloc[0]["orient_ok"] == True  # noqa: E712


def test_compare_to_truth_with_undirected_edge_b_to_a():
    """Test compare_to_truth when true graph has undirected edge (B-A form)."""
    # Create a PDAG with an undirected edge stored as (B, A)
    # Use node names where B < A alphabetically won't apply (C, A)
    # so edge is stored as (C, A) and queried as (A, C) first (miss),
    # then (C, A) second (hit line 390)
    true_pdag = PDAG(["C", "A"], [("C", "-", "A")])

    averaged = DataFrame(
        [
            {
                "node_a": "A",
                "node_b": "C",
                "p_a_to_b": 0.2,
                "p_b_to_a": 0.2,
                "p_undirected": 0.6,
                "p_no_edge": 0.0,
                "h_exist": 0.0,
                "h_orient": 0.97,
            },
        ]
    )

    result = compare_to_truth(averaged, true_pdag)

    # True edge should be undirected (detected via C-A lookup, i.e., B-A path)
    assert result.iloc[0]["true_edge"] == "undirected"
    assert result.iloc[0]["exist_ok"] == True  # noqa: E712
    assert result.iloc[0]["orient_ok"] == True  # noqa: E712


def test_compare_to_truth_adds_missed_true_edges():
    """Test that edges in true graph but missed by averaging are added."""
    # True graph has edges A->B and B->C
    true_dag = DAG(["A", "B", "C"], [("A", "->", "B"), ("B", "->", "C")])

    # Averaged DataFrame only has A-B (B-C was filtered due to p_no_edge=1.0)
    averaged = DataFrame(
        [
            {
                "node_a": "A",
                "node_b": "B",
                "p_a_to_b": 0.8,
                "p_b_to_a": 0.1,
                "p_undirected": 0.1,
                "p_no_edge": 0.0,
                "h_exist": 0.0,
                "h_orient": 0.5,
            },
        ]
    )

    result = compare_to_truth(averaged, true_dag)

    # Should have 2 rows: A-B from averaged and B-C added from true graph
    assert len(result) == 2

    # Check the existing row (A-B)
    ab_row = result[result["node_a"] == "A"]
    assert len(ab_row) == 1
    assert ab_row.iloc[0]["true_edge"] == "a_to_b"
    assert ab_row.iloc[0]["exist_ok"] == True  # noqa: E712

    # Check the added row (B-C) - completely missed edge
    bc_row = result[result["node_a"] == "B"]
    assert len(bc_row) == 1
    assert bc_row.iloc[0]["node_b"] == "C"
    assert bc_row.iloc[0]["p_a_to_b"] == 0.0
    assert bc_row.iloc[0]["p_b_to_a"] == 0.0
    assert bc_row.iloc[0]["p_undirected"] == 0.0
    assert bc_row.iloc[0]["p_no_edge"] == 1.0
    assert bc_row.iloc[0]["true_edge"] == "a_to_b"
    assert bc_row.iloc[0]["exist_ok"] == False  # noqa: E712
    assert bc_row.iloc[0]["orient_ok"] is None


def test_compare_to_truth_adds_missed_reverse_direction_edge():
    """Test missed edge with B->A direction is correctly labeled."""
    # True graph has edge B->A (reverse direction)
    true_dag = DAG(["A", "B"], [("B", "->", "A")])

    # Empty averaged DataFrame (edge was completely missed)
    averaged = DataFrame(
        columns=[
            "node_a",
            "node_b",
            "p_a_to_b",
            "p_b_to_a",
            "p_undirected",
            "p_no_edge",
            "h_exist",
            "h_orient",
        ]
    )

    result = compare_to_truth(averaged, true_dag)

    # Should have 1 row for the missed B->A edge
    assert len(result) == 1
    assert result.iloc[0]["node_a"] == "A"
    assert result.iloc[0]["node_b"] == "B"
    assert (
        result.iloc[0]["true_edge"] == "b_to_a"
    )  # B->A from (A,B) perspective
    assert result.iloc[0]["exist_ok"] == False  # noqa: E712


def test_compare_to_truth_adds_missed_undirected_edge():
    """Test missed edge that is undirected in true graph."""
    # True graph has undirected edge A-B
    true_pdag = PDAG(["A", "B"], [("A", "-", "B")])

    # Empty averaged DataFrame (edge was completely missed)
    averaged = DataFrame(
        columns=[
            "node_a",
            "node_b",
            "p_a_to_b",
            "p_b_to_a",
            "p_undirected",
            "p_no_edge",
            "h_exist",
            "h_orient",
        ]
    )

    result = compare_to_truth(averaged, true_pdag)

    # Should have 1 row for the missed undirected edge
    assert len(result) == 1
    assert result.iloc[0]["node_a"] == "A"
    assert result.iloc[0]["node_b"] == "B"
    assert result.iloc[0]["true_edge"] == "undirected"
    assert result.iloc[0]["exist_ok"] == False  # noqa: E712
    assert result.iloc[0]["p_no_edge"] == 1.0


def test_compare_to_truth_empty_averaged_and_no_true_edges():
    """Test comparison with empty averaged DataFrame and empty true graph."""
    true_dag = DAG(["A", "B"], [])  # No edges in true graph

    # Empty averaged DataFrame with correct columns
    averaged = DataFrame(
        columns=[
            "node_a",
            "node_b",
            "p_a_to_b",
            "p_b_to_a",
            "p_undirected",
            "p_no_edge",
            "h_exist",
            "h_orient",
        ]
    )

    result = compare_to_truth(averaged, true_dag)

    # Should return empty DataFrame
    assert len(result) == 0
    assert isinstance(result, DataFrame)
