"""Functional tests for merge-graphs CLI command.

These tests verify the merge-graphs command works correctly
using the CliRunner and mocked/real file system dependencies.
"""

from causaliq_analysis.cli import cli


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


# Test merge-graphs with filter referencing undefined variable.
def test_merge_graphs_filter_undefined_variable(cli_runner, tmp_path):
    """Test merge-graphs filter fails with undefined variable at runtime."""
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

    # Filter uses valid syntax but references undefined variable
    result = cli_runner.invoke(
        cli,
        [
            "merge-graphs",
            f"--input={cache_path}",
            f"--output={output_path}",
            "--filter=undefined_var > 5",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid filter expression" in result.output
