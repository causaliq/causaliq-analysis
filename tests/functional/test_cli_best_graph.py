"""Functional tests for best-graph CLI command."""

from causaliq_analysis.cli import cli


def test_best_graph_basic(cli_runner, tmp_path):
    """Test best-graph command extracts DAG from simple PDG."""
    from causaliq_core.graph import PDG, EdgeProbabilities
    from causaliq_core.graph.io import graphml

    # Create a simple PDG with clear forward edges
    pdg = PDG(
        ["A", "B", "C"],
        {
            ("A", "B"): EdgeProbabilities(forward=0.8, none=0.2),
            ("B", "C"): EdgeProbabilities(forward=0.7, none=0.3),
        },
    )

    input_path = tmp_path / "input.graphml"
    output_path = tmp_path / "output.graphml"

    with open(input_path, "w") as f:
        graphml.write_pdg(pdg, f)

    result = cli_runner.invoke(
        cli,
        [
            "best-graph",
            f"--input={input_path}",
            f"--output={output_path}",
        ],
    )

    assert result.exit_code == 0
    assert output_path.exists()

    # Verify output is a DAG with expected edges
    dag = graphml.read(str(output_path))
    assert set(dag.nodes) == {"A", "B", "C"}
    assert len(dag.edges) == 2


# Test best-graph command with threshold filtering.
def test_best_graph_with_threshold(cli_runner, tmp_path):
    """Test best-graph command respects threshold parameter."""
    from causaliq_core.graph import PDG, EdgeProbabilities
    from causaliq_core.graph.io import graphml

    # Create PDG with edges of varying probabilities
    pdg = PDG(
        ["A", "B", "C"],
        {
            ("A", "B"): EdgeProbabilities(forward=0.8, none=0.2),
            ("B", "C"): EdgeProbabilities(forward=0.3, none=0.7),
        },
    )

    input_path = tmp_path / "input.graphml"
    output_path = tmp_path / "output.graphml"

    with open(input_path, "w") as f:
        graphml.write_pdg(pdg, f)

    result = cli_runner.invoke(
        cli,
        [
            "best-graph",
            f"--input={input_path}",
            f"--output={output_path}",
            "--threshold=0.5",
        ],
    )

    assert result.exit_code == 0

    # Only A->B should be included (0.8 > 0.5)
    dag = graphml.read(str(output_path))
    assert len(dag.edges) == 1


# Test best-graph command prints stats when requested.
def test_best_graph_with_stats(cli_runner, tmp_path):
    """Test best-graph command prints extraction statistics."""
    from causaliq_core.graph import PDG, EdgeProbabilities
    from causaliq_core.graph.io import graphml

    pdg = PDG(
        ["A", "B", "C"],
        {
            ("A", "B"): EdgeProbabilities(forward=0.8, none=0.2),
            ("B", "C"): EdgeProbabilities(forward=0.7, none=0.3),
        },
    )

    input_path = tmp_path / "input.graphml"
    output_path = tmp_path / "output.graphml"

    with open(input_path, "w") as f:
        graphml.write_pdg(pdg, f)

    result = cli_runner.invoke(
        cli,
        [
            "best-graph",
            f"--input={input_path}",
            f"--output={output_path}",
            "--stats",
        ],
    )

    assert result.exit_code == 0
    assert "Edges included:" in result.output
    assert "Edges skipped (cycle):" in result.output
    assert "Edges skipped (threshold):" in result.output
    assert "Tie-breaks (alphabetical):" in result.output


# Test best-graph command handles missing input file.
def test_best_graph_missing_input(cli_runner, tmp_path):
    """Test best-graph command rejects missing input file."""
    output_path = tmp_path / "output.graphml"

    result = cli_runner.invoke(
        cli,
        [
            "best-graph",
            "--input=/nonexistent/file.graphml",
            f"--output={output_path}",
        ],
    )

    assert result.exit_code != 0


# Test best-graph command handles invalid PDG file.
def test_best_graph_invalid_input(cli_runner, tmp_path):
    """Test best-graph command handles invalid PDG file."""
    input_path = tmp_path / "invalid.graphml"
    output_path = tmp_path / "output.graphml"

    # Write invalid content
    with open(input_path, "w") as f:
        f.write("not valid graphml")

    result = cli_runner.invoke(
        cli,
        [
            "best-graph",
            f"--input={input_path}",
            f"--output={output_path}",
        ],
    )

    assert result.exit_code != 0
    assert "Failed to read PDG" in result.output


# Test best-graph command with undirected probability.
def test_best_graph_undirected_split(cli_runner, tmp_path):
    """Test best-graph command splits undirected probability."""
    from causaliq_core.graph import PDG, EdgeProbabilities
    from causaliq_core.graph.io import graphml

    # Undirected=0.8 splits to 0.4 each direction; forward wins by alphabet
    pdg = PDG(
        ["A", "B"],
        {
            ("A", "B"): EdgeProbabilities(undirected=0.8, none=0.2),
        },
    )

    input_path = tmp_path / "input.graphml"
    output_path = tmp_path / "output.graphml"

    with open(input_path, "w") as f:
        graphml.write_pdg(pdg, f)

    result = cli_runner.invoke(
        cli,
        [
            "best-graph",
            f"--input={input_path}",
            f"--output={output_path}",
            "--stats",
        ],
    )

    assert result.exit_code == 0

    dag = graphml.read(str(output_path))
    assert len(dag.edges) == 1
    # A < B alphabetically, so A->B selected
    assert "Tie-breaks (alphabetical): 1" in result.output


# Test best-graph command handles DAG extraction failure.
def test_best_graph_dag_extraction_failure(cli_runner, tmp_path, monkeypatch):
    """Test best-graph command handles to_dag_greedy failure."""
    from causaliq_core.graph import PDG, EdgeProbabilities
    from causaliq_core.graph.io import graphml

    pdg = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(forward=0.8, none=0.2)},
    )

    input_path = tmp_path / "input.graphml"
    output_path = tmp_path / "output.graphml"

    with open(input_path, "w") as f:
        graphml.write_pdg(pdg, f)

    # Mock to_dag_greedy to raise an exception
    def mock_to_dag_greedy(*args, **kwargs):
        raise RuntimeError("Algorithm failed")

    monkeypatch.setattr(PDG, "to_dag_greedy", mock_to_dag_greedy)

    result = cli_runner.invoke(
        cli,
        [
            "best-graph",
            f"--input={input_path}",
            f"--output={output_path}",
        ],
    )

    assert result.exit_code != 0
    assert "DAG extraction failed" in result.output


# Test best-graph command handles write output failure.
def test_best_graph_write_failure(cli_runner, tmp_path, monkeypatch):
    """Test best-graph command handles output write failure."""
    from causaliq_core.graph import PDG, EdgeProbabilities
    from causaliq_core.graph.io import graphml

    pdg = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(forward=0.8, none=0.2)},
    )

    input_path = tmp_path / "input.graphml"
    output_path = tmp_path / "output.graphml"

    with open(input_path, "w") as f:
        graphml.write_pdg(pdg, f)

    # Mock graphml.write to raise an exception
    original_write = graphml.write

    def mock_write(graph, file):
        # Allow reading but fail on the write for output
        if hasattr(file, "read"):
            return original_write(graph, file)
        raise IOError("Disk full")

    monkeypatch.setattr("causaliq_core.graph.io.graphml.write", mock_write)

    result = cli_runner.invoke(
        cli,
        [
            "best-graph",
            f"--input={input_path}",
            f"--output={output_path}",
        ],
    )

    assert result.exit_code != 0
    assert "Failed to write output" in result.output
