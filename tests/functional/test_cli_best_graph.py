"""Functional tests for best-graph CLI command."""

from causaliq_analysis.cli import cli


# Test best-graph command extracts DAG from simple PDG.
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
    output_dir = tmp_path / "output"

    with open(input_path, "w") as f:
        graphml.write_pdg(pdg, f)

    result = cli_runner.invoke(
        cli,
        [
            "best-graph",
            f"--input={input_path}",
            f"--output={output_dir}",
        ],
    )

    assert result.exit_code == 0

    # Verify output directory structure
    dag_path = output_dir / "dag.graphml"
    meta_path = output_dir / "_meta.json"
    assert dag_path.exists()
    assert meta_path.exists()

    # Verify output is a DAG with expected edges
    dag = graphml.read(str(dag_path))
    assert set(dag.nodes) == {"A", "B", "C"}
    assert len(dag.edges) == 2

    # Verify _meta.json content
    import json

    meta = json.loads(meta_path.read_text())
    assert "metadata" in meta
    assert "causaliq-analysis" in meta["metadata"]
    assert "best_graph" in meta["metadata"]["causaliq-analysis"]


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
    output_dir = tmp_path / "output"

    with open(input_path, "w") as f:
        graphml.write_pdg(pdg, f)

    result = cli_runner.invoke(
        cli,
        [
            "best-graph",
            f"--input={input_path}",
            f"--output={output_dir}",
            "--threshold=0.5",
        ],
    )

    assert result.exit_code == 0

    # Only A->B should be included (0.8 > 0.5)
    dag_path = output_dir / "dag.graphml"
    dag = graphml.read(str(dag_path))
    assert len(dag.edges) == 1


# Test best-graph command writes stats to _meta.json.
def test_best_graph_metadata_stats(cli_runner, tmp_path):
    """Test best-graph command writes extraction statistics to metadata."""
    import json

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
    output_dir = tmp_path / "output"

    with open(input_path, "w") as f:
        graphml.write_pdg(pdg, f)

    result = cli_runner.invoke(
        cli,
        [
            "best-graph",
            f"--input={input_path}",
            f"--output={output_dir}",
        ],
    )

    assert result.exit_code == 0

    # Check stats in metadata file
    meta_path = output_dir / "_meta.json"
    meta = json.loads(meta_path.read_text())
    stats = meta["metadata"]["causaliq-analysis"]["best_graph"]
    assert "edges_included" in stats
    assert "edges_skipped_cycle" in stats
    assert "edges_skipped_threshold" in stats
    assert "tie_breaks_applied" in stats


# Test best-graph command handles missing input file.
def test_best_graph_missing_input(cli_runner, tmp_path):
    """Test best-graph command rejects missing input file."""
    output_dir = tmp_path / "output"

    result = cli_runner.invoke(
        cli,
        [
            "best-graph",
            "--input=/nonexistent/file.graphml",
            f"--output={output_dir}",
        ],
    )

    assert result.exit_code != 0


# Test best-graph command handles invalid PDG file.
def test_best_graph_invalid_input(cli_runner, tmp_path):
    """Test best-graph command handles invalid PDG file."""
    input_path = tmp_path / "invalid.graphml"
    output_dir = tmp_path / "output"

    # Write invalid content
    with open(input_path, "w") as f:
        f.write("not valid graphml")

    result = cli_runner.invoke(
        cli,
        [
            "best-graph",
            f"--input={input_path}",
            f"--output={output_dir}",
        ],
    )

    assert result.exit_code != 0
    # Error comes from action now
    assert "Failed to read PDG" in result.output or "Error" in result.output


# Test best-graph command with undirected probability.
def test_best_graph_undirected_split(cli_runner, tmp_path):
    """Test best-graph command splits undirected probability."""
    import json

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
    output_dir = tmp_path / "output"

    with open(input_path, "w") as f:
        graphml.write_pdg(pdg, f)

    result = cli_runner.invoke(
        cli,
        [
            "best-graph",
            f"--input={input_path}",
            f"--output={output_dir}",
        ],
    )

    assert result.exit_code == 0

    dag_path = output_dir / "dag.graphml"
    dag = graphml.read(str(dag_path))
    assert len(dag.edges) == 1
    # A < B alphabetically, so A->B selected - check metadata
    meta_path = output_dir / "_meta.json"
    meta = json.loads(meta_path.read_text())
    stats = meta["metadata"]["causaliq-analysis"]["best_graph"]
    assert stats["tie_breaks_applied"] == 1


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
    output_dir = tmp_path / "output"

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
            f"--output={output_dir}",
        ],
    )

    assert result.exit_code != 0
    assert "DAG extraction failed" in result.output


# Test best-graph command handles write output failure.
def test_best_graph_write_failure(cli_runner, tmp_path, monkeypatch):
    """Test best-graph command handles output write failure."""
    from pathlib import Path

    from causaliq_core.graph import PDG, EdgeProbabilities
    from causaliq_core.graph.io import graphml

    pdg = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(forward=0.8, none=0.2)},
    )

    input_path = tmp_path / "input.graphml"
    output_dir = tmp_path / "output"

    with open(input_path, "w") as f:
        graphml.write_pdg(pdg, f)

    # Mock Path.write_text to raise an exception
    original_write_text = Path.write_text

    def mock_write_text(self, content, *args, **kwargs):
        if self.suffix == ".graphml":
            raise IOError("Disk full")
        return original_write_text(self, content, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", mock_write_text)

    result = cli_runner.invoke(
        cli,
        [
            "best-graph",
            f"--input={input_path}",
            f"--output={output_dir}",
        ],
    )

    assert result.exit_code != 0
    assert "Failed to write output" in result.output


# Test best-graph command handles action returning non-success status.
def test_best_graph_action_non_success(cli_runner, tmp_path, monkeypatch):
    """Test best-graph command handles action returning non-success."""
    from causaliq_core.graph import PDG, EdgeProbabilities
    from causaliq_core.graph.io import graphml

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    pdg = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(forward=0.8, none=0.2)},
    )

    input_path = tmp_path / "input.graphml"
    output_dir = tmp_path / "output"

    with open(input_path, "w") as f:
        graphml.write_pdg(pdg, f)

    # Mock action to return error status
    def mock_run(self, action, params, mode=None, **kwargs):
        return ("error", {"reason": "test failure"}, [])

    monkeypatch.setattr(AnalysisActionProvider, "run", mock_run)

    result = cli_runner.invoke(
        cli,
        [
            "best-graph",
            f"--input={input_path}",
            f"--output={output_dir}",
        ],
    )

    assert result.exit_code != 0
    assert "Action failed" in result.output


# Test best-graph command handles action returning no DAG object.
def test_best_graph_no_dag_object(cli_runner, tmp_path, monkeypatch):
    """Test best-graph command handles action returning no DAG object."""
    from causaliq_core.graph import PDG, EdgeProbabilities
    from causaliq_core.graph.io import graphml

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    pdg = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(forward=0.8, none=0.2)},
    )

    input_path = tmp_path / "input.graphml"
    output_dir = tmp_path / "output"

    with open(input_path, "w") as f:
        graphml.write_pdg(pdg, f)

    # Mock action to return success but no objects
    def mock_run(self, action, params, mode=None, **kwargs):
        return ("success", {"info": "ok"}, [])

    monkeypatch.setattr(AnalysisActionProvider, "run", mock_run)

    result = cli_runner.invoke(
        cli,
        [
            "best-graph",
            f"--input={input_path}",
            f"--output={output_dir}",
        ],
    )

    assert result.exit_code != 0
    assert "No DAG object" in result.output


# Test best-graph command handles metadata write failure.
def test_best_graph_metadata_write_failure(cli_runner, tmp_path, monkeypatch):
    """Test best-graph command handles metadata file write failure."""
    from pathlib import Path

    from causaliq_core.graph import PDG, EdgeProbabilities
    from causaliq_core.graph.io import graphml

    pdg = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(forward=0.8, none=0.2)},
    )

    input_path = tmp_path / "input.graphml"
    output_dir = tmp_path / "output"

    with open(input_path, "w") as f:
        graphml.write_pdg(pdg, f)

    # Mock Path.write_text to fail only for _meta.json
    original_write_text = Path.write_text

    def mock_write_text(self, content, *args, **kwargs):
        if self.name == "_meta.json":
            raise IOError("Disk full")
        return original_write_text(self, content, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", mock_write_text)

    result = cli_runner.invoke(
        cli,
        [
            "best-graph",
            f"--input={input_path}",
            f"--output={output_dir}",
        ],
    )

    assert result.exit_code != 0
    assert "Failed to write metadata" in result.output


# Test best-graph command handles directory creation failure.
def test_best_graph_mkdir_failure(cli_runner, tmp_path, monkeypatch):
    """Test best-graph command handles output directory creation failure."""
    from pathlib import Path

    from causaliq_core.graph import PDG, EdgeProbabilities
    from causaliq_core.graph.io import graphml

    pdg = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(forward=0.8, none=0.2)},
    )

    input_path = tmp_path / "input.graphml"
    output_dir = tmp_path / "output"

    with open(input_path, "w") as f:
        graphml.write_pdg(pdg, f)

    # Mock Path.mkdir to raise an exception
    def mock_mkdir(self, *args, **kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr(Path, "mkdir", mock_mkdir)

    result = cli_runner.invoke(
        cli,
        [
            "best-graph",
            f"--input={input_path}",
            f"--output={output_dir}",
        ],
    )

    assert result.exit_code != 0
    assert "Failed to create output directory" in result.output
