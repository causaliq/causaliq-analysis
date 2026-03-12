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
            f"--graph={graph_path}",
            f"--reference={ref_path}",
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
            f"--graph={graph_path}",
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
            f"--graph={graph_path}",
            f"--reference={ref_path}",
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
    assert "f1" in metrics
    assert "shd" in metrics


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
            f"--graph={graph_path}",
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
            f"--graph={graph_path}",
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
        ["evaluate-graph", f"--graph={graph_path}", f"--reference={ref_path}"],
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
            f"--graph={graph_path}",
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
            f"--graph={graph_path}",
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
            f"--graph={graph_path}",
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
            f"--graph={graph_path}",
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
            f"--graph={graph_path}",
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
            f"--graph={graph_path}",
            f"--reference={ref_path}",
            "-m",
            "equiv.f1",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid graph type" in result.output


# --------------------------------------------------------------------------
# Tests for best-graph command
# --------------------------------------------------------------------------


# Test best-graph command extracts optimal DAG from PDG.
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


# --------------------------------------------------------------------------
# Tests for summarise command
# --------------------------------------------------------------------------


# Test summarise command with JSON input.
def test_summarise_json_input(cli_runner, tmp_path):
    """Test summarise command with JSON file input."""
    import json

    # Create JSON input with metric values
    input_data = [
        {"f1": 0.8, "shd": 2},
        {"f1": 0.9, "shd": 1},
        {"f1": 0.85, "shd": 3},
    ]
    input_path = tmp_path / "metrics.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-m",
            "f1.sd",
            "-m",
            "shd.count",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert output_path.exists()

    # Read CSV and verify
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert abs(float(row["f1.mean"]) - 0.85) < 0.01
        assert row["shd.count"] == "3"


# Test summarise command with single JSON object.
def test_summarise_single_json_object(cli_runner, tmp_path):
    """Test summarise command with single JSON object input."""
    import json

    input_data = {"precision": 0.9, "recall": 0.85}
    input_path = tmp_path / "single.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "precision.mean",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert float(row["precision.mean"]) == 0.9


# Test summarise command with invalid metric spec.
def test_summarise_invalid_metric_spec(cli_runner, tmp_path):
    """Test summarise command rejects invalid metric specification."""
    import json

    input_path = tmp_path / "data.json"
    with open(input_path, "w") as f:
        json.dump([{"f1": 0.8}], f)

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1",  # Missing '.stat' part
            "-i",
            str(input_path),
            "-o",
            str(tmp_path / "out.csv"),
        ],
    )

    assert result.exit_code != 0
    assert "must be <field>.<stat>" in result.output


# Test summarise command with unsupported statistic.
def test_summarise_unsupported_stat(cli_runner, tmp_path):
    """Test summarise command rejects unsupported statistic."""
    import json

    input_path = tmp_path / "data.json"
    with open(input_path, "w") as f:
        json.dump([{"f1": 0.8}], f)

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.median",  # Not supported
            "-i",
            str(input_path),
            "-o",
            str(tmp_path / "out.csv"),
        ],
    )

    assert result.exit_code != 0
    assert "Unknown statistic" in result.output


# Test summarise command with unsupported file type.
def test_summarise_unsupported_file_type(cli_runner, tmp_path):
    """Test summarise command rejects unsupported file types."""
    input_path = tmp_path / "data.txt"
    input_path.write_text("some text")

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-i",
            str(input_path),
            "-o",
            str(tmp_path / "out.csv"),
        ],
    )

    assert result.exit_code != 0
    assert "Unsupported file type" in result.output


# Test summarise command SD with insufficient values.
def test_summarise_sd_insufficient_values(cli_runner, tmp_path):
    """Test summarise command returns None for SD with <2 values."""
    import json

    input_data = [{"f1": 0.8}]  # Only one value
    input_path = tmp_path / "single.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.sd",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert row["f1.sd"] == "" or row["f1.sd"] == "None"


# Test summarise command with empty values.
def test_summarise_empty_values(cli_runner, tmp_path):
    """Test summarise command handles no matching values."""
    import json

    input_data = [{"other_field": 0.8}]
    input_path = tmp_path / "data.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert row["f1.mean"] == "" or row["f1.mean"] == "None"


# Test summarise command with invalid JSON.
def test_summarise_invalid_json(cli_runner, tmp_path):
    """Test summarise command handles invalid JSON file."""
    input_path = tmp_path / "bad.json"
    input_path.write_text("{invalid json")

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-i",
            str(input_path),
            "-o",
            str(tmp_path / "out.csv"),
        ],
    )

    assert result.exit_code != 0
    assert "Invalid JSON file" in result.output


# Test summarise command with multiple input files.
def test_summarise_multiple_inputs(cli_runner, tmp_path):
    """Test summarise command with multiple input files."""
    import json

    input1 = tmp_path / "data1.json"
    input2 = tmp_path / "data2.json"
    with open(input1, "w") as f:
        json.dump([{"f1": 0.8}, {"f1": 0.9}], f)
    with open(input2, "w") as f:
        json.dump([{"f1": 0.7}], f)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-m",
            "f1.count",
            "-i",
            str(input1),
            "-i",
            str(input2),
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert row["f1.count"] == "3"
        assert abs(float(row["f1.mean"]) - 0.8) < 0.01


# Test summarise command with filter expression.
def test_summarise_with_filter(cli_runner, tmp_path):
    """Test summarise command with filter expression on JSON."""
    import json

    input_data = [
        {"f1": 0.8, "status": "completed"},
        {"f1": 0.5, "status": "failed"},
        {"f1": 0.9, "status": "completed"},
    ]
    input_path = tmp_path / "data.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-m",
            "f1.count",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
            "-f",
            "status == 'completed'",
        ],
    )

    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        # Only 2 values pass filter (0.8 and 0.9)
        assert row["f1.count"] == "2"
        assert abs(float(row["f1.mean"]) - 0.85) < 0.01


# Test summarise command with nested field access.
def test_summarise_nested_field(cli_runner, tmp_path):
    """Test summarise command can access nested fields."""
    import json

    input_data = [
        {"metrics": {"f1": 0.8}},
        {"metrics": {"f1": 0.9}},
    ]
    input_path = tmp_path / "nested.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "metrics.f1.mean",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert abs(float(row["metrics.f1.mean"]) - 0.85) < 0.01


# Test summarise command skips non-numeric values.
def test_summarise_skips_non_numeric(cli_runner, tmp_path):
    """Test summarise command skips non-numeric values."""
    import json

    input_data = [
        {"f1": 0.8},
        {"f1": "invalid"},
        {"f1": 0.9},
    ]
    input_path = tmp_path / "mixed.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.count",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        # Only 2 numeric values
        assert row["f1.count"] == "2"


# Test summarise command skips non-dict records.
def test_summarise_skips_non_dict_records(cli_runner, tmp_path):
    """Test summarise command skips non-dict items in array."""
    import json

    input_data = [
        {"f1": 0.8},
        "not a dict",
        {"f1": 0.9},
    ]
    input_path = tmp_path / "mixed_types.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.count",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert row["f1.count"] == "2"


# Test summarise command handles non-array/object JSON.
def test_summarise_invalid_json_structure(cli_runner, tmp_path):
    """Test summarise command rejects non-object/array JSON root."""
    import json

    input_path = tmp_path / "bad_structure.json"
    with open(input_path, "w") as f:
        json.dump("just a string", f)

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-i",
            str(input_path),
            "-o",
            str(tmp_path / "out.csv"),
        ],
    )

    assert result.exit_code != 0
    assert "must contain object or array" in result.output


# Test summarise command with workflow cache input.
def test_summarise_workflow_cache_input(cli_runner, tmp_path):
    """Test summarise command reads from workflow cache .db file."""
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    # Create a workflow cache with entries containing metrics
    cache_path = tmp_path / "results.db"
    with WorkflowCache(str(cache_path)) as cache:
        entry1 = CacheEntry(
            metadata={
                "causaliq-analysis": {"evaluate_graph": {"f1": 0.8, "shd": 2}}
            }
        )
        entry2 = CacheEntry(
            metadata={
                "causaliq-analysis": {"evaluate_graph": {"f1": 0.9, "shd": 1}}
            }
        )
        cache.put({"seed": 1}, entry1)
        cache.put({"seed": 2}, entry2)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-m",
            "shd.count",
            "-i",
            str(cache_path),
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert abs(float(row["f1.mean"]) - 0.85) < 0.01
        assert row["shd.count"] == "2"


# Test summarise command with workflow cache filter.
def test_summarise_workflow_cache_with_filter(cli_runner, tmp_path):
    """Test summarise command can filter workflow cache entries."""
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    cache_path = tmp_path / "results.db"
    with WorkflowCache(str(cache_path)) as cache:
        entry1 = CacheEntry(
            metadata={
                "causaliq-analysis": {
                    "evaluate_graph": {"f1": 0.8, "status": "completed"}
                }
            }
        )
        entry2 = CacheEntry(
            metadata={
                "causaliq-analysis": {
                    "evaluate_graph": {"f1": 0.5, "status": "failed"}
                }
            }
        )
        entry3 = CacheEntry(
            metadata={
                "causaliq-analysis": {
                    "evaluate_graph": {"f1": 0.9, "status": "completed"}
                }
            }
        )
        cache.put({"seed": 1}, entry1)
        cache.put({"seed": 2}, entry2)
        cache.put({"seed": 3}, entry3)

    output_path = tmp_path / "summary.csv"

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-m",
            "f1.count",
            "-i",
            str(cache_path),
            "-o",
            str(output_path),
            "-f",
            "status == 'completed'",
        ],
    )

    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        # Only 2 completed entries (0.8 and 0.9)
        assert row["f1.count"] == "2"
        assert abs(float(row["f1.mean"]) - 0.85) < 0.01


# Test summarise command handles invalid filter in JSON.
def test_summarise_filter_exception_json(cli_runner, tmp_path):
    """Test summarise command handles filter exception in JSON records."""
    import json

    # Records that will cause filter evaluation to fail
    input_data = [
        {"f1": 0.8, "value": "normal"},
        {"f1": 0.9, "value": "normal"},
    ]
    input_path = tmp_path / "data.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    output_path = tmp_path / "summary.csv"

    # Use a filter that references undefined variable
    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.count",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
            "-f",
            "undefined_var > 5",
        ],
    )

    # Command should succeed but skip records that fail filter evaluation
    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        # All records skipped due to filter exception
        assert row["f1.count"] == "0"


# Test summarise command handles write error.
def test_summarise_write_error(cli_runner, tmp_path, monkeypatch):
    """Test summarise command handles write output error."""
    import json

    input_path = tmp_path / "data.json"
    with open(input_path, "w") as f:
        json.dump([{"f1": 0.8}], f)

    # Create a directory where the output file should be
    output_path = tmp_path / "summary.csv"
    output_path.mkdir()  # Make it a directory so write fails

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code != 0
    assert "Failed to write output" in result.output


# Test summarise command handles cache read error.
def test_summarise_cache_read_error(cli_runner, tmp_path):
    """Test summarise command handles workflow cache read error."""
    # Create an invalid .db file
    cache_path = tmp_path / "invalid.db"
    cache_path.write_text("not a valid sqlite database")

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-i",
            str(cache_path),
            "-o",
            str(tmp_path / "out.csv"),
        ],
    )

    assert result.exit_code != 0
    assert "Failed to read cache" in result.output


# Test _flatten_metadata helper function.
def test_flatten_metadata_nested_structure():
    """Test _flatten_metadata flattens provider/action structure."""
    from causaliq_analysis.cli import _flatten_metadata

    metadata = {
        "causaliq-analysis": {
            "evaluate_graph": {"f1": 0.9, "shd": 2},
            "other_action": {"score": 0.5},
        },
        "simple_provider": "simple_value",
    }

    flat = _flatten_metadata(metadata)

    # Simple keys from nested structure
    assert flat["f1"] == 0.9
    assert flat["shd"] == 2
    assert flat["score"] == 0.5

    # Qualified keys also present
    assert flat["causaliq-analysis.evaluate_graph.f1"] == 0.9
    assert flat["causaliq-analysis.other_action.score"] == 0.5

    # Non-dict provider value
    assert flat["simple_provider"] == "simple_value"


# Test _flatten_metadata with action data not a dict.
def test_flatten_metadata_action_not_dict():
    """Test _flatten_metadata handles non-dict action data."""
    from causaliq_analysis.cli import _flatten_metadata

    metadata = {
        "provider": {
            "action": "scalar_value",  # Not a dict
        }
    }

    flat = _flatten_metadata(metadata)
    assert flat["provider.action"] == "scalar_value"


# Test _get_nested_value helper function.
def test_get_nested_value_direct_key():
    """Test _get_nested_value with direct key access."""
    from causaliq_analysis.cli import _get_nested_value

    data = {"f1": 0.9, "precision": 0.85}
    assert _get_nested_value(data, "f1") == 0.9
    assert _get_nested_value(data, "precision") == 0.85


# Test _get_nested_value with dotted path.
def test_get_nested_value_dotted_path():
    """Test _get_nested_value with dotted path traversal."""
    from causaliq_analysis.cli import _get_nested_value

    data = {"metrics": {"f1": 0.9, "nested": {"value": 42}}}
    assert _get_nested_value(data, "metrics.f1") == 0.9
    assert _get_nested_value(data, "metrics.nested.value") == 42


# Test _get_nested_value returns None for missing keys.
def test_get_nested_value_missing_key():
    """Test _get_nested_value returns None for missing keys."""
    from causaliq_analysis.cli import _get_nested_value

    data = {"f1": 0.9}
    assert _get_nested_value(data, "missing") is None
    assert _get_nested_value(data, "a.b.c") is None


# Test summarise command handles filter exception in workflow cache.
def test_summarise_workflow_cache_filter_exception(cli_runner, tmp_path):
    """Test summarise skips cache entries that fail filter evaluation."""
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    cache_path = tmp_path / "results.db"
    with WorkflowCache(str(cache_path)) as cache:
        entry = CacheEntry(
            metadata={"causaliq-analysis": {"evaluate_graph": {"f1": 0.8}}}
        )
        cache.put({"seed": 1}, entry)

    output_path = tmp_path / "summary.csv"

    # Use a filter that references undefined variable
    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.count",
            "-i",
            str(cache_path),
            "-o",
            str(output_path),
            "-f",
            "undefined_var > 5",
        ],
    )

    # Command should succeed but skip entries that fail filter evaluation
    assert result.exit_code == 0
    import csv

    with open(output_path) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        # Entry skipped due to filter exception
        assert row["f1.count"] == "0"


# Test summarise command with terminal output using "-o -".
def test_summarise_terminal_output(cli_runner, tmp_path):
    """Test summarise command outputs to terminal with -o -."""
    import json

    input_data = [
        {"f1": 0.8, "shd": 2},
        {"f1": 0.9, "shd": 1},
    ]
    input_path = tmp_path / "data.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.mean",
            "-m",
            "shd.count",
            "-i",
            str(input_path),
            "-o",
            "-",
        ],
    )

    assert result.exit_code == 0
    # Check formatted table output
    assert "f1.mean" in result.output
    assert "shd.count" in result.output
    assert "0.85" in result.output
    assert "2" in result.output


# Test summarise command terminal output with None values.
def test_summarise_terminal_output_with_none(cli_runner, tmp_path):
    """Test summarise terminal output formats None values correctly."""
    import json

    # Single value means SD will be None
    input_data = [{"f1": 0.8}]
    input_path = tmp_path / "data.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.sd",
            "-i",
            str(input_path),
            "-o",
            "-",
        ],
    )

    assert result.exit_code == 0
    assert "f1.sd" in result.output
    assert "None" in result.output  # None displayed in output


# Test summarise command terminal output with empty results.
def test_summarise_terminal_output_empty(cli_runner, tmp_path):
    """Test summarise terminal output with no matching data."""
    import json

    # No matching field
    input_data = [{"other": 0.8}]
    input_path = tmp_path / "data.json"
    with open(input_path, "w") as f:
        json.dump(input_data, f)

    result = cli_runner.invoke(
        cli,
        [
            "summarise",
            "-m",
            "f1.count",
            "-i",
            str(input_path),
            "-o",
            "-",
        ],
    )

    assert result.exit_code == 0
    assert "f1.count" in result.output
    assert "0" in result.output  # count is 0


# Test _print_summary_table helper function directly.
def test_print_summary_table_formatting(capsys):
    """Test _print_summary_table formats output correctly."""
    from causaliq_analysis.cli import _print_summary_table

    results = {
        "f1.mean": 0.85,
        "f1.sd": 0.03535533905932738,
        "shd.count": 5,
        "missing.value": None,
    }

    _print_summary_table(results)

    captured = capsys.readouterr()
    output = captured.out

    # Check metric names are in header row
    assert "f1.mean" in output
    assert "f1.sd" in output
    assert "shd.count" in output
    assert "missing.value" in output

    # Check values are formatted
    assert "0.8500" in output  # 4 decimal places for float
    assert "0.0354" in output  # 4 decimal places for float
    assert "5" in output  # integers as-is

    # Check separator line exists
    assert "---" in output


# Test _print_summary_table with empty results.
def test_print_summary_table_empty_results(capsys):
    """Test _print_summary_table handles empty results dict."""
    from causaliq_analysis.cli import _print_summary_table

    _print_summary_table({})

    captured = capsys.readouterr()
    assert "No results to display" in captured.out
