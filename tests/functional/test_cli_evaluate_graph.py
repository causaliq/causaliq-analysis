"""Functional tests for evaluate-graph CLI command."""

from causaliq_analysis.cli import cli


# Test evaluate-graph command with matching graphs.
def test_evaluate_graph_perfect_match(cli_runner, tmp_path):
    """Test evaluate-graph command with identical graphs."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    # Create identical DAGs
    dag = DAG(["A", "B", "C"], [("A", "->", "B"), ("B", "->", "C")])

    graph_path = tmp_path / "learned.graphml"
    ref_path = tmp_path / "reference.graphml"

    with open(graph_path, "w") as f:
        graphml.write(dag, f)
    with open(ref_path, "w") as f:
        graphml.write(dag, f)

    result = cli_runner.invoke(
        cli,
        [
            "evaluate-graph",
            f"--input={graph_path}",
            f"--reference={ref_path}",
            "-m",
            "f1",
            "-m",
            "shd",
            "-m",
            "equiv.f1",
            "-m",
            "equiv.shd",
        ],
    )

    assert result.exit_code == 0
    # Perfect match should have f1=1, shd=0
    import json

    metrics = json.loads(result.output)
    assert metrics["f1"] == 1.0
    assert metrics["shd"] == 0
    assert metrics["equiv.f1"] == 1.0
    assert metrics["equiv.shd"] == 0


# Test evaluate-graph command with different graphs.
def test_evaluate_graph_different_graphs(cli_runner, tmp_path):
    """Test evaluate-graph command with different graphs."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    # Create different DAGs
    learned = DAG(["A", "B", "C"], [("A", "->", "B")])
    reference = DAG(["A", "B", "C"], [("A", "->", "B"), ("B", "->", "C")])

    graph_path = tmp_path / "learned.graphml"
    ref_path = tmp_path / "reference.graphml"

    with open(graph_path, "w") as f:
        graphml.write(learned, f)
    with open(ref_path, "w") as f:
        graphml.write(reference, f)

    result = cli_runner.invoke(
        cli,
        [
            "evaluate-graph",
            f"--input={graph_path}",
            f"--reference={ref_path}",
            "-m",
            "f1",
            "-m",
            "shd",
        ],
    )

    assert result.exit_code == 0
    import json

    metrics = json.loads(result.output)
    # One edge matched, one missing - SHD should be non-zero
    assert metrics["shd"] > 0
    assert metrics["f1"] < 1.0


# Test evaluate-graph command with specific metrics.
def test_evaluate_graph_with_specific_metrics(cli_runner, tmp_path):
    """Test evaluate-graph command with specific metric selection."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    dag = DAG(["A", "B"], [("A", "->", "B")])

    graph_path = tmp_path / "learned.graphml"
    ref_path = tmp_path / "reference.graphml"

    with open(graph_path, "w") as f:
        graphml.write(dag, f)
    with open(ref_path, "w") as f:
        graphml.write(dag, f)

    result = cli_runner.invoke(
        cli,
        [
            "evaluate-graph",
            f"--input={graph_path}",
            f"--reference={ref_path}",
            "-m",
            "f1",
            "-m",
            "shd",
        ],
    )

    assert result.exit_code == 0
    import json

    metrics = json.loads(result.output)
    # Should have only requested metrics
    assert "f1" in metrics
    assert "shd" in metrics
    # Should not have equiv metrics
    assert "equiv.f1" not in metrics
    assert "equiv.shd" not in metrics


# Test evaluate-graph command with table format.
def test_evaluate_graph_table_format(cli_runner, tmp_path):
    """Test evaluate-graph command with table output format."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    dag = DAG(["A", "B"], [("A", "->", "B")])

    graph_path = tmp_path / "learned.graphml"
    ref_path = tmp_path / "reference.graphml"

    with open(graph_path, "w") as f:
        graphml.write(dag, f)
    with open(ref_path, "w") as f:
        graphml.write(dag, f)

    result = cli_runner.invoke(
        cli,
        [
            "evaluate-graph",
            f"--input={graph_path}",
            f"--reference={ref_path}",
            "-m",
            "f1",
            "-m",
            "shd",
            "-m",
            "equiv.f1",
            "-m",
            "equiv.shd",
            "--format=table",
        ],
    )

    assert result.exit_code == 0
    assert "Structural Evaluation Metrics" in result.output
    assert "f1" in result.output
    assert "shd" in result.output
    assert "equiv.f1" in result.output
    assert "equiv.shd" in result.output


# Test evaluate-graph command with output file.
def test_evaluate_graph_output_file(cli_runner, tmp_path):
    """Test evaluate-graph command writing to output file."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    dag = DAG(["A", "B"], [("A", "->", "B")])

    graph_path = tmp_path / "learned.graphml"
    ref_path = tmp_path / "reference.graphml"
    output_path = tmp_path / "metrics.json"

    with open(graph_path, "w") as f:
        graphml.write(dag, f)
    with open(ref_path, "w") as f:
        graphml.write(dag, f)

    result = cli_runner.invoke(
        cli,
        [
            "evaluate-graph",
            f"--input={graph_path}",
            f"--reference={ref_path}",
            "-m",
            "f1",
            "-m",
            "shd",
            f"--output={output_path}",
        ],
    )

    assert result.exit_code == 0
    assert "Metrics written to" in result.output
    assert output_path.exists()

    import json

    with open(output_path) as f:
        metrics = json.load(f)
    assert "f1" in metrics
    assert "shd" in metrics


# Test evaluate-graph command with output file write failure.
def test_evaluate_graph_output_write_failure(
    cli_runner, tmp_path, monkeypatch
):
    """Test evaluate-graph command handles output file write failure."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    dag = DAG(["A", "B"], [("A", "->", "B")])

    graph_path = tmp_path / "learned.graphml"
    ref_path = tmp_path / "reference.graphml"
    output_path = tmp_path / "metrics.json"

    with open(graph_path, "w") as f:
        graphml.write(dag, f)
    with open(ref_path, "w") as f:
        graphml.write(dag, f)

    # Mock Path.write_text to raise an exception
    def mock_write_text(*args, **kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr("pathlib.Path.write_text", mock_write_text)

    result = cli_runner.invoke(
        cli,
        [
            "evaluate-graph",
            f"--input={graph_path}",
            f"--reference={ref_path}",
            "-m",
            "f1",
            f"--output={output_path}",
        ],
    )

    assert result.exit_code != 0
    assert "Failed to write output" in result.output


# Test evaluate-graph command with invalid graph file.
def test_evaluate_graph_invalid_graph(cli_runner, tmp_path):
    """Test evaluate-graph command with invalid graph file."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    dag = DAG(["A", "B"], [("A", "->", "B")])

    graph_path = tmp_path / "invalid.graphml"
    ref_path = tmp_path / "reference.graphml"

    with open(graph_path, "w") as f:
        f.write("not valid graphml")
    with open(ref_path, "w") as f:
        graphml.write(dag, f)

    result = cli_runner.invoke(
        cli,
        [
            "evaluate-graph",
            f"--input={graph_path}",
            f"--reference={ref_path}",
            "-m",
            "f1",
        ],
    )

    assert result.exit_code != 0
    assert "Failed to read learned graph" in result.output


# Test evaluate-graph command with invalid reference file.
def test_evaluate_graph_invalid_reference(cli_runner, tmp_path):
    """Test evaluate-graph command with invalid reference file."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    dag = DAG(["A", "B"], [("A", "->", "B")])

    graph_path = tmp_path / "learned.graphml"
    ref_path = tmp_path / "invalid.graphml"

    with open(graph_path, "w") as f:
        graphml.write(dag, f)
    with open(ref_path, "w") as f:
        f.write("not valid graphml")

    result = cli_runner.invoke(
        cli,
        [
            "evaluate-graph",
            f"--input={graph_path}",
            f"--reference={ref_path}",
            "-m",
            "f1",
        ],
    )

    assert result.exit_code != 0
    assert "Failed to read reference graph" in result.output


# Test evaluate-graph command with mismatched nodes.
def test_evaluate_graph_mismatched_nodes(cli_runner, tmp_path):
    """Test evaluate-graph command with graphs having different nodes."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    learned = DAG(["A", "B"], [("A", "->", "B")])
    reference = DAG(["X", "Y"], [("X", "->", "Y")])

    graph_path = tmp_path / "learned.graphml"
    ref_path = tmp_path / "reference.graphml"

    with open(graph_path, "w") as f:
        graphml.write(learned, f)
    with open(ref_path, "w") as f:
        graphml.write(reference, f)

    result = cli_runner.invoke(
        cli,
        [
            "evaluate-graph",
            f"--input={graph_path}",
            f"--reference={ref_path}",
            "-m",
            "f1",
        ],
    )

    # Should fail since nodes don't match
    assert result.exit_code != 0
    assert "Comparison failed" in result.output


# Test evaluate-graph command with TypeError from pdag_compare.
def test_evaluate_graph_type_error(cli_runner, tmp_path, monkeypatch):
    """Test evaluate-graph command handles TypeError from comparison."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    dag = DAG(["A", "B"], [("A", "->", "B")])

    graph_path = tmp_path / "learned.graphml"
    ref_path = tmp_path / "reference.graphml"

    with open(graph_path, "w") as f:
        graphml.write(dag, f)
    with open(ref_path, "w") as f:
        graphml.write(dag, f)

    # Mock pdag_compare to raise TypeError
    def mock_pdag_compare(*args, **kwargs):
        raise TypeError("bad arg type for compared_to")

    monkeypatch.setattr(
        "causaliq_analysis.metrics.pdag_compare", mock_pdag_compare
    )

    result = cli_runner.invoke(
        cli,
        [
            "evaluate-graph",
            f"--input={graph_path}",
            f"--reference={ref_path}",
            "-m",
            "f1",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid graph type" in result.output


# Test evaluate-graph command with invalid metric name.
def test_evaluate_graph_invalid_metric(cli_runner, tmp_path):
    """Test evaluate-graph command rejects invalid metric names."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    dag = DAG(["A", "B"], [("A", "->", "B")])

    graph_path = tmp_path / "learned.graphml"
    ref_path = tmp_path / "reference.graphml"

    with open(graph_path, "w") as f:
        graphml.write(dag, f)
    with open(ref_path, "w") as f:
        graphml.write(dag, f)

    result = cli_runner.invoke(
        cli,
        [
            "evaluate-graph",
            f"--input={graph_path}",
            f"--reference={ref_path}",
            "-m",
            "invalid_metric",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid metric" in result.output


# Test evaluate-graph command with equiv metrics only.
def test_evaluate_graph_equiv_metrics_only(cli_runner, tmp_path):
    """Test evaluate-graph command with only equivalence class metrics."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    dag = DAG(["A", "B"], [("A", "->", "B")])

    graph_path = tmp_path / "learned.graphml"
    ref_path = tmp_path / "reference.graphml"

    with open(graph_path, "w") as f:
        graphml.write(dag, f)
    with open(ref_path, "w") as f:
        graphml.write(dag, f)

    result = cli_runner.invoke(
        cli,
        [
            "evaluate-graph",
            f"--input={graph_path}",
            f"--reference={ref_path}",
            "-m",
            "equiv.f1",
            "-m",
            "equiv.shd",
        ],
    )

    assert result.exit_code == 0
    import json

    metrics = json.loads(result.output)
    assert "equiv.f1" in metrics
    assert "equiv.shd" in metrics
    # Should not have direct metrics
    assert "f1" not in metrics
    assert "shd" not in metrics


# Test evaluate-graph with xdsl format reference file.
def test_evaluate_graph_xdsl_reference(cli_runner, tmp_path):
    """Test evaluate-graph with .xdsl reference file."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    # Create learned graph
    learned = DAG(["A", "B"], [("A", "->", "B")])
    graph_path = tmp_path / "learned.graphml"
    with open(graph_path, "w") as f:
        graphml.write(learned, f)

    # Create minimal xdsl reference file (GeNIe format)
    xdsl_content = """<?xml version="1.0" encoding="UTF-8"?>
<smile version="1.0" id="Network1">
    <nodes>
        <cpt id="A">
            <state id="s0" />
            <state id="s1" />
            <probabilities>0.5 0.5</probabilities>
        </cpt>
        <cpt id="B">
            <state id="s0" />
            <state id="s1" />
            <parents>A</parents>
            <probabilities>0.9 0.1 0.2 0.8</probabilities>
        </cpt>
    </nodes>
</smile>"""
    ref_path = tmp_path / "reference.xdsl"
    ref_path.write_text(xdsl_content)

    result = cli_runner.invoke(
        cli,
        [
            "evaluate-graph",
            f"--input={graph_path}",
            f"--reference={ref_path}",
            "-m",
            "f1",
        ],
    )

    assert result.exit_code == 0


# Test evaluate-graph CPDAG conversion failure.
def test_evaluate_graph_cpdag_conversion_error(
    cli_runner, tmp_path, monkeypatch
):
    """Test evaluate-graph handles CPDAG conversion errors."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    dag = DAG(["A", "B"], [("A", "->", "B")])
    graph_path = tmp_path / "learned.graphml"
    ref_path = tmp_path / "reference.graphml"
    with open(graph_path, "w") as f:
        graphml.write(dag, f)
    with open(ref_path, "w") as f:
        graphml.write(dag, f)

    # Mock dag_to_pdag to raise ValueError
    def mock_dag_to_pdag(g):
        raise ValueError("PDAG is not extendable to a CPDAG")

    monkeypatch.setattr(
        "causaliq_core.graph.convert.dag_to_pdag", mock_dag_to_pdag
    )

    result = cli_runner.invoke(
        cli,
        [
            "evaluate-graph",
            f"--input={graph_path}",
            f"--reference={ref_path}",
            "-m",
            "equiv.f1",
        ],
    )

    assert result.exit_code != 0
    assert "CPDAG conversion failed" in result.output


# Test evaluate-graph with PDAG input that is not extendable.
def test_evaluate_graph_pdag_not_extendable(cli_runner, tmp_path, monkeypatch):
    """Test evaluate-graph fails when PDAG cannot be converted to CPDAG."""
    from causaliq_core.graph import DAG, PDAG
    from causaliq_core.graph.io import graphml

    # Write valid DAG files
    dag = DAG(["A", "B"], [("A", "->", "B")])
    graph_path = tmp_path / "learned.graphml"
    ref_path = tmp_path / "reference.graphml"
    with open(graph_path, "w") as f:
        graphml.write(dag, f)
    with open(ref_path, "w") as f:
        graphml.write(dag, f)

    # Create a PDAG that will be returned by read_graph
    pdag = PDAG(["A", "B"], [("A", "-", "B")])

    # Mock read_graph to return PDAG
    def mock_read_graph(path):
        return pdag

    monkeypatch.setattr("causaliq_core.graph.io.read_graph", mock_read_graph)

    # Mock pdag_to_cpdag to return None (not extendable)
    def mock_pdag_to_cpdag(g):
        return None

    monkeypatch.setattr(
        "causaliq_core.graph.convert.pdag_to_cpdag", mock_pdag_to_cpdag
    )

    result = cli_runner.invoke(
        cli,
        [
            "evaluate-graph",
            f"--input={graph_path}",
            f"--reference={ref_path}",
            "-m",
            "equiv.f1",
        ],
    )

    assert result.exit_code != 0
    assert "CPDAG conversion failed" in result.output
    assert "not extendable" in result.output


# Test evaluate-graph with valid PDAG input.
def test_evaluate_graph_pdag_input(cli_runner, tmp_path, monkeypatch):
    """Test evaluate-graph with PDAG input that converts to CPDAG."""
    from causaliq_core.graph import DAG, PDAG
    from causaliq_core.graph.io import graphml

    # Write valid DAG files
    dag = DAG(["A", "B"], [("A", "->", "B")])
    graph_path = tmp_path / "learned.graphml"
    ref_path = tmp_path / "reference.graphml"
    with open(graph_path, "w") as f:
        graphml.write(dag, f)
    with open(ref_path, "w") as f:
        graphml.write(dag, f)

    # Create PDAGs for input and return
    input_pdag = PDAG(["A", "B"], [("A", "-", "B")])
    result_cpdag = PDAG(["A", "B"], [("A", "->", "B")])

    # Mock read_graph to return PDAG
    def mock_read_graph(path):
        return input_pdag

    monkeypatch.setattr("causaliq_core.graph.io.read_graph", mock_read_graph)

    # Mock pdag_to_cpdag to return valid CPDAG
    def mock_pdag_to_cpdag(g):
        return result_cpdag

    monkeypatch.setattr(
        "causaliq_core.graph.convert.pdag_to_cpdag", mock_pdag_to_cpdag
    )

    result = cli_runner.invoke(
        cli,
        [
            "evaluate-graph",
            f"--input={graph_path}",
            f"--reference={ref_path}",
            "-m",
            "equiv.f1",
        ],
    )

    assert result.exit_code == 0


# Test evaluate-graph with unsupported graph type.
def test_evaluate_graph_unsupported_type(cli_runner, tmp_path, monkeypatch):
    """Test evaluate-graph fails with unsupported graph type."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    # Write valid DAG files
    dag = DAG(["A", "B"], [("A", "->", "B")])
    graph_path = tmp_path / "learned.graphml"
    ref_path = tmp_path / "reference.graphml"
    with open(graph_path, "w") as f:
        graphml.write(dag, f)
    with open(ref_path, "w") as f:
        graphml.write(dag, f)

    # Mock read_graph to return an unsupported type (plain dict)
    def mock_read_graph(path):
        return {"nodes": ["A", "B"]}  # Not a DAG or PDAG

    monkeypatch.setattr("causaliq_core.graph.io.read_graph", mock_read_graph)

    result = cli_runner.invoke(
        cli,
        [
            "evaluate-graph",
            f"--input={graph_path}",
            f"--reference={ref_path}",
            "-m",
            "equiv.f1",
        ],
    )

    assert result.exit_code != 0
    assert "CPDAG conversion failed" in result.output
    assert "Cannot convert" in result.output


# Test evaluate-graph equivalence comparison failure.
def test_evaluate_graph_equiv_comparison_error(
    cli_runner, tmp_path, monkeypatch
):
    """Test evaluate-graph handles equivalence comparison errors."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    dag = DAG(["A", "B"], [("A", "->", "B")])
    graph_path = tmp_path / "learned.graphml"
    ref_path = tmp_path / "reference.graphml"
    with open(graph_path, "w") as f:
        graphml.write(dag, f)
    with open(ref_path, "w") as f:
        graphml.write(dag, f)

    # Mock pdag_compare to raise ValueError
    def mock_pdag_compare(a, b):
        raise ValueError("Node sets differ")

    monkeypatch.setattr(
        "causaliq_analysis.metrics.pdag_compare", mock_pdag_compare
    )

    result = cli_runner.invoke(
        cli,
        [
            "evaluate-graph",
            f"--input={graph_path}",
            f"--reference={ref_path}",
            "-m",
            "equiv.f1",
        ],
    )

    assert result.exit_code != 0
    assert "Equivalence class comparison failed" in result.output


# Test evaluate-graph equivalence comparison type error.
def test_evaluate_graph_equiv_type_error(cli_runner, tmp_path, monkeypatch):
    """Test evaluate-graph handles type errors in equivalence comparison."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    dag = DAG(["A", "B"], [("A", "->", "B")])
    graph_path = tmp_path / "learned.graphml"
    ref_path = tmp_path / "reference.graphml"
    with open(graph_path, "w") as f:
        graphml.write(dag, f)
    with open(ref_path, "w") as f:
        graphml.write(dag, f)

    # Mock pdag_compare to raise TypeError
    def mock_pdag_compare(a, b):
        raise TypeError("Expected PDAG, got DAG")

    monkeypatch.setattr(
        "causaliq_analysis.metrics.pdag_compare", mock_pdag_compare
    )

    result = cli_runner.invoke(
        cli,
        [
            "evaluate-graph",
            f"--input={graph_path}",
            f"--reference={ref_path}",
            "-m",
            "equiv.f1",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid graph type" in result.output
