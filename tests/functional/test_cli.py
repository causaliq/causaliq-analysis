"""
Functional tests for the CLI.

These tests use Click's CliRunner to invoke the CLI commands
and verify end-to-end behavior.

monkeypatch only works on current process, so CLI runner must be invoked
using standalone=False
"""

from click.testing import CliRunner
from pytest import fixture

from causaliq_analysis.cli import cli


# Provide a CLI runner for testing
@fixture
def cli_runner():
    return CliRunner()


# Main CLI with no arguments shows available commands
def test_cli_no_args_shows_commands():
    runner = CliRunner()
    result = runner.invoke(cli, [])
    # Click groups return exit code 0 or 2 depending on click version
    assert result.exit_code in (0, 2)
    assert "Commands:" in result.output
    assert "migrate-trace" in result.output


# Main function invokes CLI correctly
def test_main_function(monkeypatch):
    called = {}

    def fake_cli(*args, **kwargs):
        called["cli"] = True

    monkeypatch.setattr("causaliq_analysis.cli.cli", fake_cli)
    from causaliq_analysis.cli import main

    main()
    assert called.get("cli") is True


# Test migrate_trace command success.
def test_migrate_trace_success(cli_runner, tmp_path, monkeypatch):
    """Test migrate_trace command succeeds with valid parameters."""
    from causaliq_analysis.migrate import MigratedGraph, MigrateTraceResult

    # Mock run_migrate_trace to return test data
    def mock_run_migrate_trace(
        partial_id, root_dir, sample_size, seeds, log_fn
    ):
        if log_fn:
            log_fn("Loading traces...")
            log_fn("Found 2 matching traces")
            log_fn("Migration complete: 2 graphs generated")
        return MigrateTraceResult(
            graphs=[
                MigratedGraph(
                    trace_id="N1000",
                    graphml='<?xml version="1.0"?><graphml></graphml>',
                    metadata={"N": 1000, "algorithm": "TABU"},
                ),
            ],
            skipped=0,
        )

    def mock_write_migrate_result(result, output_dir, log_fn):
        if log_fn:
            log_fn("Writing graphs...")
        return [f"{output_dir}/N1000.graphml"]

    monkeypatch.setattr(
        "causaliq_analysis.migrate.run_migrate_trace", mock_run_migrate_trace
    )
    monkeypatch.setattr(
        "causaliq_analysis.migrate.write_migrate_result",
        mock_write_migrate_result,
    )

    root_dir = tmp_path / "experiments"
    root_dir.mkdir()
    output_dir = tmp_path / "output"

    result = cli_runner.invoke(
        cli,
        [
            "migrate-trace",
            "--network=asia",
            "--series=TABU/STD",
            f"--root-dir={root_dir}",
            f"--output={output_dir}",
        ],
    )

    assert result.exit_code == 0
    assert "Migration complete" in result.output


# Test migrate_trace command with sample_size filter.
def test_migrate_trace_with_sample_size(cli_runner, tmp_path, monkeypatch):
    """Test migrate_trace command with --N sample size filter."""
    from causaliq_analysis.migrate import MigratedGraph, MigrateTraceResult

    def mock_run_migrate_trace(
        partial_id, root_dir, sample_size, seeds, log_fn
    ):
        # Verify sample_size was parsed correctly
        assert sample_size == 1000
        return MigrateTraceResult(
            graphs=[
                MigratedGraph(
                    trace_id="N1000",
                    graphml='<?xml version="1.0"?><graphml></graphml>',
                    metadata={"N": 1000},
                ),
            ],
            skipped=0,
        )

    def mock_write_migrate_result(result, output_dir, log_fn):
        return [f"{output_dir}/N1000.graphml"]

    monkeypatch.setattr(
        "causaliq_analysis.migrate.run_migrate_trace", mock_run_migrate_trace
    )
    monkeypatch.setattr(
        "causaliq_analysis.migrate.write_migrate_result",
        mock_write_migrate_result,
    )

    root_dir = tmp_path / "experiments"
    root_dir.mkdir()

    result = cli_runner.invoke(
        cli,
        [
            "migrate-trace",
            "--network=asia",
            "--series=TABU/STD",
            f"--root-dir={root_dir}",
            "--N=1k",  # Use sample_size parameter
        ],
    )

    assert result.exit_code == 0


# Test migrate_trace command with skipped traces.
def test_migrate_trace_with_skipped(cli_runner, tmp_path, monkeypatch):
    """Test migrate_trace shows skipped count when some traces skipped."""
    from causaliq_analysis.migrate import MigratedGraph, MigrateTraceResult

    def mock_run_migrate_trace(
        partial_id, root_dir, sample_size, seeds, log_fn
    ):
        return MigrateTraceResult(
            graphs=[
                MigratedGraph(
                    trace_id="N1000",
                    graphml='<?xml version="1.0"?><graphml></graphml>',
                    metadata={"N": 1000},
                ),
            ],
            skipped=2,
        )

    def mock_write_migrate_result(result, output_dir, log_fn):
        return [f"{output_dir}/N1000.graphml"]

    monkeypatch.setattr(
        "causaliq_analysis.migrate.run_migrate_trace", mock_run_migrate_trace
    )
    monkeypatch.setattr(
        "causaliq_analysis.migrate.write_migrate_result",
        mock_write_migrate_result,
    )

    root_dir = tmp_path / "experiments"
    root_dir.mkdir()

    result = cli_runner.invoke(
        cli,
        [
            "migrate-trace",
            "--network=asia",
            "--series=TABU/STD",
            f"--root-dir={root_dir}",
        ],
    )

    assert result.exit_code == 0
    assert "Skipped 2 traces" in result.output


# Test migrate_trace command ValueError handling.
def test_migrate_trace_value_error(cli_runner, tmp_path, monkeypatch):
    """Test migrate_trace handles ValueError from run_migrate_trace."""

    def mock_run_migrate_trace(
        partial_id, root_dir, sample_size, seeds, log_fn
    ):
        raise ValueError("No traces found for pattern")

    monkeypatch.setattr(
        "causaliq_analysis.migrate.run_migrate_trace", mock_run_migrate_trace
    )

    root_dir = tmp_path / "experiments"
    root_dir.mkdir()

    result = cli_runner.invoke(
        cli,
        [
            "migrate-trace",
            "--network=asia",
            "--series=TABU/STD",
            f"--root-dir={root_dir}",
        ],
    )

    assert result.exit_code != 0
    assert "No traces found" in result.output


# Test migrate_trace command general exception handling.
def test_migrate_trace_general_error(cli_runner, tmp_path, monkeypatch):
    """Test migrate_trace handles general exceptions."""

    def mock_run_migrate_trace(
        partial_id, root_dir, sample_size, seeds, log_fn
    ):
        raise RuntimeError("Unexpected failure")

    monkeypatch.setattr(
        "causaliq_analysis.migrate.run_migrate_trace", mock_run_migrate_trace
    )

    root_dir = tmp_path / "experiments"
    root_dir.mkdir()

    result = cli_runner.invoke(
        cli,
        [
            "migrate-trace",
            "--network=asia",
            "--series=TABU/STD",
            f"--root-dir={root_dir}",
        ],
    )

    assert result.exit_code != 0
    assert "Migration failed" in result.output


# Test merge-graphs command with GraphML files.
def test_merge_graphs_from_graphml_files(cli_runner, tmp_path):
    """Test merge-graphs command with GraphML file inputs."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    # Create two simple DAGs
    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("B", "->", "A")])

    graph1_path = tmp_path / "graph1.graphml"
    graph2_path = tmp_path / "graph2.graphml"
    output_path = tmp_path / "merged.graphml"

    with open(graph1_path, "w") as f:
        graphml.write(dag1, f)
    with open(graph2_path, "w") as f:
        graphml.write(dag2, f)

    result = cli_runner.invoke(
        cli,
        [
            "merge-graphs",
            f"--input={graph1_path}",
            f"--input={graph2_path}",
            f"--output={output_path}",
        ],
    )

    assert result.exit_code == 0
    assert "Merged 2 graphs" in result.output
    assert output_path.exists()


# Test merge-graphs command from workflow cache.
def test_merge_graphs_from_cache(cli_runner, tmp_path):
    """Test merge-graphs command reading from .db cache."""
    from io import StringIO

    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    # Create a cache with two graphs
    cache_path = tmp_path / "test.db"
    output_path = tmp_path / "merged.graphml"

    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("B", "->", "A")])

    with WorkflowCache(str(cache_path)) as cache:
        # Entry 1
        entry1 = CacheEntry()
        buf1 = StringIO()
        graphml.write(dag1, buf1)
        entry1.add_object("graph", "graphml", buf1.getvalue())
        entry1.metadata["network"] = "asia"
        entry1.metadata["sample_size"] = 1000
        cache.put({"seed": 1}, entry1)

        # Entry 2
        entry2 = CacheEntry()
        buf2 = StringIO()
        graphml.write(dag2, buf2)
        entry2.add_object("graph", "graphml", buf2.getvalue())
        entry2.metadata["network"] = "asia"
        entry2.metadata["sample_size"] = 1000
        cache.put({"seed": 2}, entry2)

    result = cli_runner.invoke(
        cli,
        [
            "merge-graphs",
            f"--input={cache_path}",
            f"--output={output_path}",
        ],
    )

    assert result.exit_code == 0
    assert "Reading 2 entries" in result.output
    assert "Merged 2 graphs" in result.output


# Test merge-graphs with filter expression.
def test_merge_graphs_with_filter(cli_runner, tmp_path):
    """Test merge-graphs command with filter expression."""
    from io import StringIO

    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    cache_path = tmp_path / "test.db"
    output_path = tmp_path / "merged.graphml"

    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("B", "->", "A")])

    with WorkflowCache(str(cache_path)) as cache:
        # Entry 1 (should be included)
        entry1 = CacheEntry()
        buf1 = StringIO()
        graphml.write(dag1, buf1)
        entry1.add_object("graph", "graphml", buf1.getvalue())
        entry1.metadata["sample_size"] = 1000
        cache.put({"seed": 1}, entry1)

        # Entry 2 (should be filtered out)
        entry2 = CacheEntry()
        buf2 = StringIO()
        graphml.write(dag2, buf2)
        entry2.add_object("graph", "graphml", buf2.getvalue())
        entry2.metadata["sample_size"] = 100
        cache.put({"seed": 2}, entry2)

    result = cli_runner.invoke(
        cli,
        [
            "merge-graphs",
            f"--input={cache_path}",
            f"--output={output_path}",
            "--filter=sample_size >= 500",
        ],
    )

    assert result.exit_code == 0
    assert "Filtered out 1 entries" in result.output
    assert "Merged 1 graphs" in result.output


# Test merge-graphs with weights file.
def test_merge_graphs_with_weights(cli_runner, tmp_path):
    """Test merge-graphs command with metadata-driven weights."""
    import json
    from io import StringIO

    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    cache_path = tmp_path / "test.db"
    output_path = tmp_path / "merged.graphml"
    weights_path = tmp_path / "weights.json"

    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("B", "->", "A")])

    with WorkflowCache(str(cache_path)) as cache:
        entry1 = CacheEntry()
        buf1 = StringIO()
        graphml.write(dag1, buf1)
        entry1.add_object("graph", "graphml", buf1.getvalue())
        entry1.metadata["sample_size"] = 1000
        cache.put({"seed": 1}, entry1)

        entry2 = CacheEntry()
        buf2 = StringIO()
        graphml.write(dag2, buf2)
        entry2.add_object("graph", "graphml", buf2.getvalue())
        entry2.metadata["sample_size"] = 100
        cache.put({"seed": 2}, entry2)

    # Create weights file
    with open(weights_path, "w") as f:
        json.dump({"sample_size": {"100": 0.5, "1000": 1.0}}, f)

    result = cli_runner.invoke(
        cli,
        [
            "merge-graphs",
            f"--input={cache_path}",
            f"--output={output_path}",
            f"--weights={weights_path}",
        ],
    )

    assert result.exit_code == 0
    assert "Applied metadata-driven weights" in result.output


# Test merge-graphs with cpdag flag.
def test_merge_graphs_with_cpdag(cli_runner, tmp_path):
    """Test merge-graphs command with --cpdag flag."""
    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("A", "->", "B")])

    graph1_path = tmp_path / "graph1.graphml"
    graph2_path = tmp_path / "graph2.graphml"
    output_path = tmp_path / "merged.graphml"

    with open(graph1_path, "w") as f:
        graphml.write(dag1, f)
    with open(graph2_path, "w") as f:
        graphml.write(dag2, f)

    result = cli_runner.invoke(
        cli,
        [
            "merge-graphs",
            f"--input={graph1_path}",
            f"--input={graph2_path}",
            f"--output={output_path}",
            "--cpdag",
        ],
    )

    assert result.exit_code == 0
    assert "Merged 2 graphs" in result.output


# Test merge-graphs with invalid filter expression.
def test_merge_graphs_invalid_filter(cli_runner, tmp_path):
    """Test merge-graphs command with invalid filter expression."""
    from io import StringIO

    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    cache_path = tmp_path / "test.db"
    output_path = tmp_path / "merged.graphml"

    dag1 = DAG(["A", "B"], [("A", "->", "B")])

    with WorkflowCache(str(cache_path)) as cache:
        entry1 = CacheEntry()
        buf1 = StringIO()
        graphml.write(dag1, buf1)
        entry1.add_object("graph", "graphml", buf1.getvalue())
        entry1.metadata["sample_size"] = 1000
        cache.put({"seed": 1}, entry1)

    result = cli_runner.invoke(
        cli,
        [
            "merge-graphs",
            f"--input={cache_path}",
            f"--output={output_path}",
            "--filter=invalid syntax !!!",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid filter expression" in result.output


# Test merge-graphs weights require cache input.
def test_merge_graphs_weights_require_cache(cli_runner, tmp_path):
    """Test merge-graphs weights option requires .db cache input."""
    import json

    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    graph1_path = tmp_path / "graph1.graphml"
    output_path = tmp_path / "merged.graphml"
    weights_path = tmp_path / "weights.json"

    with open(graph1_path, "w") as f:
        graphml.write(dag1, f)

    with open(weights_path, "w") as f:
        json.dump({"sample_size": {"1000": 1.0}}, f)

    result = cli_runner.invoke(
        cli,
        [
            "merge-graphs",
            f"--input={graph1_path}",
            f"--output={output_path}",
            f"--weights={weights_path}",
        ],
    )

    assert result.exit_code != 0
    assert "require .db cache input" in result.output


# Test merge-graphs with cache entry missing graphml objects.
def test_merge_graphs_cache_no_graphml(cli_runner, tmp_path):
    """Test merge-graphs handles cache entries without graphml objects."""
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    cache_path = tmp_path / "test.db"
    output_path = tmp_path / "merged.graphml"

    with WorkflowCache(str(cache_path)) as cache:
        # Entry with no graphml objects
        entry1 = CacheEntry()
        entry1.add_object("data", "json", '{"key": "value"}')
        cache.put({"seed": 1}, entry1)

    result = cli_runner.invoke(
        cli,
        [
            "merge-graphs",
            f"--input={cache_path}",
            f"--output={output_path}",
        ],
    )

    assert result.exit_code != 0
    assert "No graphs found" in result.output


# Test merge-graphs with invalid weights JSON.
def test_merge_graphs_invalid_weights_json(cli_runner, tmp_path):
    """Test merge-graphs with invalid weights JSON file."""
    from io import StringIO

    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    cache_path = tmp_path / "test.db"
    output_path = tmp_path / "merged.graphml"
    weights_path = tmp_path / "weights.json"

    dag1 = DAG(["A", "B"], [("A", "->", "B")])

    with WorkflowCache(str(cache_path)) as cache:
        entry1 = CacheEntry()
        buf1 = StringIO()
        graphml.write(dag1, buf1)
        entry1.add_object("graph", "graphml", buf1.getvalue())
        cache.put({"seed": 1}, entry1)

    # Create invalid JSON
    with open(weights_path, "w") as f:
        f.write("not valid json {{{")

    result = cli_runner.invoke(
        cli,
        [
            "merge-graphs",
            f"--input={cache_path}",
            f"--output={output_path}",
            f"--weights={weights_path}",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid weights JSON" in result.output


# Test merge-graphs with invalid read from graphml.
def test_merge_graphs_invalid_graphml(cli_runner, tmp_path):
    """Test merge-graphs with invalid GraphML file."""
    graph1_path = tmp_path / "invalid.graphml"
    output_path = tmp_path / "merged.graphml"

    with open(graph1_path, "w") as f:
        f.write("not valid xml")

    result = cli_runner.invoke(
        cli,
        [
            "merge-graphs",
            f"--input={graph1_path}",
            f"--output={output_path}",
        ],
    )

    assert result.exit_code != 0
    assert "Failed to read" in result.output


# Test merge-graphs skipping entries without graphml objects.
def test_merge_graphs_skips_non_graphml_entries(cli_runner, tmp_path):
    """Test merge-graphs skips entries without graphml but merges others."""
    from io import StringIO

    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    cache_path = tmp_path / "test.db"
    output_path = tmp_path / "merged.graphml"

    dag1 = DAG(["A", "B"], [("A", "->", "B")])

    with WorkflowCache(str(cache_path)) as cache:
        # Entry 1 WITH graphml
        entry1 = CacheEntry()
        buf1 = StringIO()
        graphml.write(dag1, buf1)
        entry1.add_object("graph", "graphml", buf1.getvalue())
        cache.put({"seed": 1}, entry1)

        # Entry 2 WITHOUT graphml (will be skipped)
        entry2 = CacheEntry()
        entry2.add_object("data", "json", '{"key": "value"}')
        cache.put({"seed": 2}, entry2)

    result = cli_runner.invoke(
        cli,
        [
            "merge-graphs",
            f"--input={cache_path}",
            f"--output={output_path}",
        ],
    )

    assert result.exit_code == 0
    assert "Skipping" in result.output
    assert "no graphml objects" in result.output
    assert "Merged 1 graphs" in result.output


# Test merge-graphs with invalid weight specification.
def test_merge_graphs_invalid_weight_spec(cli_runner, tmp_path):
    """Test merge-graphs with invalid weight specification JSON."""
    import json
    from io import StringIO

    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    cache_path = tmp_path / "test.db"
    output_path = tmp_path / "merged.graphml"
    weights_path = tmp_path / "weights.json"

    dag1 = DAG(["A", "B"], [("A", "->", "B")])

    with WorkflowCache(str(cache_path)) as cache:
        entry1 = CacheEntry()
        buf1 = StringIO()
        graphml.write(dag1, buf1)
        entry1.add_object("graph", "graphml", buf1.getvalue())
        entry1.metadata["sample_size"] = 1000
        cache.put({"seed": 1}, entry1)

    # Create invalid weight spec (not a dict of dicts)
    with open(weights_path, "w") as f:
        json.dump({"sample_size": "not_a_dict"}, f)

    result = cli_runner.invoke(
        cli,
        [
            "merge-graphs",
            f"--input={cache_path}",
            f"--output={output_path}",
            f"--weights={weights_path}",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid weight specification" in result.output


# Test merge-graphs with cache entry containing invalid graphml.
def test_merge_graphs_invalid_graphml_in_cache(cli_runner, tmp_path):
    """Test merge-graphs with cache entry containing unparseable graphml."""
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    cache_path = tmp_path / "test.db"
    output_path = tmp_path / "merged.graphml"

    with WorkflowCache(str(cache_path)) as cache:
        # Entry with invalid graphml content
        entry1 = CacheEntry()
        entry1.add_object("graph", "graphml", "not valid xml content")
        cache.put({"seed": 1}, entry1)

    result = cli_runner.invoke(
        cli,
        [
            "merge-graphs",
            f"--input={cache_path}",
            f"--output={output_path}",
        ],
    )

    assert result.exit_code != 0
    assert "Failed to parse graph" in result.output


# Test merge-graphs with zero total weights.
def test_merge_graphs_zero_total_weights(cli_runner, tmp_path):
    """Test merge-graphs handles zero total weights gracefully."""
    import json
    from io import StringIO

    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    cache_path = tmp_path / "test.db"
    output_path = tmp_path / "merged.graphml"
    weights_path = tmp_path / "weights.json"

    dag1 = DAG(["A", "B"], [("A", "->", "B")])
    dag2 = DAG(["A", "B"], [("B", "->", "A")])

    with WorkflowCache(str(cache_path)) as cache:
        entry1 = CacheEntry()
        buf1 = StringIO()
        graphml.write(dag1, buf1)
        entry1.add_object("graph", "graphml", buf1.getvalue())
        entry1.metadata["sample_size"] = 100
        cache.put({"seed": 1}, entry1)

        entry2 = CacheEntry()
        buf2 = StringIO()
        graphml.write(dag2, buf2)
        entry2.add_object("graph", "graphml", buf2.getvalue())
        entry2.metadata["sample_size"] = 200
        cache.put({"seed": 2}, entry2)

    # Weight spec where all matching values have weight 0.0
    with open(weights_path, "w") as f:
        json.dump({"sample_size": {"100": 0.0, "200": 0.0}}, f)

    result = cli_runner.invoke(
        cli,
        [
            "merge-graphs",
            f"--input={cache_path}",
            f"--output={output_path}",
            f"--weights={weights_path}",
        ],
    )

    # Should succeed with equal weights when total is 0
    assert result.exit_code == 0
    assert "Merged 2 graphs" in result.output


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
            f"--graph={graph_path}",
            f"--reference={ref_path}",
        ],
    )

    assert result.exit_code == 0
    # Perfect match should have precision=1, recall=1, f1=1, shd=0
    import json

    metrics = json.loads(result.output)
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["shd"] == 0


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
            f"--graph={graph_path}",
            f"--reference={ref_path}",
        ],
    )

    assert result.exit_code == 0
    import json

    metrics = json.loads(result.output)
    # One edge matched, one missing
    assert metrics["precision"] == 1.0  # 1/1 predicted edges correct
    assert metrics["recall"] == 0.5  # 1/2 reference edges found
    assert metrics["shd"] > 0


# Test evaluate-graph command with Bayesys metrics.
def test_evaluate_graph_with_bayesys(cli_runner, tmp_path):
    """Test evaluate-graph command with Bayesys metrics."""
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
            f"--graph={graph_path}",
            f"--reference={ref_path}",
            "--bayesys=v1.5+",
        ],
    )

    assert result.exit_code == 0
    import json

    metrics = json.loads(result.output)
    # Should have standard metrics
    assert "precision" in metrics
    assert "recall" in metrics
    # Should also have Bayesys metrics
    assert "precision_b" in metrics
    assert "recall_b" in metrics
    assert "f1_b" in metrics
    assert "shd_b" in metrics
    assert "ddm" in metrics
    assert "bsf" in metrics


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
            f"--graph={graph_path}",
            f"--reference={ref_path}",
            "--format=table",
        ],
    )

    assert result.exit_code == 0
    assert "Structural Evaluation Metrics" in result.output
    assert "precision" in result.output
    assert "recall" in result.output
    assert "f1" in result.output
    assert "shd" in result.output


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
            f"--graph={graph_path}",
            f"--reference={ref_path}",
            f"--output={output_path}",
        ],
    )

    assert result.exit_code == 0
    assert "Metrics written to" in result.output
    assert output_path.exists()

    import json

    with open(output_path) as f:
        metrics = json.load(f)
    assert "precision" in metrics
    assert "f1" in metrics


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
            f"--graph={graph_path}",
            f"--reference={ref_path}",
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
            f"--graph={graph_path}",
            f"--reference={ref_path}",
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
            f"--graph={graph_path}",
            f"--reference={ref_path}",
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
            f"--graph={graph_path}",
            f"--reference={ref_path}",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid graph type" in result.output
