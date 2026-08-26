"""Unit tests for CLI"""

from click.testing import CliRunner
from pytest import fixture

from causaliq_analysis.cli import cli


@fixture
def runner():
    return CliRunner()


# Version option prints version correctly.
def test_cli_version(runner):
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "version" in result.output.lower()


# Help option prints main CLI help with available commands.
def test_cli_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "causaliq-analysis" in result.output
    assert "Commands:" in result.output
    assert "migrate-trace" in result.output


# migrate-trace command help displays correct usage and options.
def test_migrate_trace_help(runner):
    result = runner.invoke(cli, ["migrate-trace", "--help"])
    assert result.exit_code == 0
    assert "Migrate legacy Trace pickle files" in result.output
    assert "--network" in result.output
    assert "--series" in result.output
    assert "--root-dir" in result.output


# migrate-trace command fails when required options are missing.
def test_migrate_trace_missing_options(runner):
    result = runner.invoke(cli, ["migrate-trace"])
    assert result.exit_code != 0
    assert "Missing option" in result.output


# Help shows merge-graphs command.
def test_cli_help_shows_merge_graph(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "merge-graphs" in result.output


# merge-graphs command help displays correct usage and options.
def test_merge_graph_help(runner):
    result = runner.invoke(cli, ["merge-graphs", "--help"])
    assert result.exit_code == 0
    assert "Merge multiple graphs" in result.output
    assert "--output" in result.output
    assert "--weights" in result.output
    assert "--input" in result.output
    assert "--filter" in result.output


# merge-graphs command fails when no inputs provided.
def test_merge_graph_no_inputs(runner):
    result = runner.invoke(cli, ["merge-graphs", "-o", "out.graphml"])
    assert result.exit_code != 0
    # Click shows "Missing option" when required options are missing
    assert "--input" in result.output or "Missing" in result.output


# merge-graphs command fails when output not provided.
def test_merge_graph_no_output(runner, tmp_path):
    graphml_file = tmp_path / "test.graphml"
    graphml_file.write_text(
        '<?xml version="1.0"?><graphml xmlns="http://graphml.graphdrawing.org'
        '/xmlns"><graph id="G" edgedefault="directed">'
        '<node id="A"/><node id="B"/>'
        '<edge source="A" target="B"/></graph></graphml>'
    )
    result = runner.invoke(cli, ["merge-graphs", "-i", str(graphml_file)])
    assert result.exit_code != 0
    assert "Missing option" in result.output


# merge-graphs succeeds with valid GraphML files.
def test_merge_graph_success(runner, tmp_path):
    # Create two simple GraphML files
    graphml1 = tmp_path / "g1.graphml"
    graphml1.write_text(
        '<?xml version="1.0"?><graphml xmlns="http://graphml.graphdrawing.org'
        '/xmlns"><graph id="G" edgedefault="directed">'
        '<node id="A"/><node id="B"/>'
        '<edge source="A" target="B"/></graph></graphml>'
    )
    graphml2 = tmp_path / "g2.graphml"
    graphml2.write_text(
        '<?xml version="1.0"?><graphml xmlns="http://graphml.graphdrawing.org'
        '/xmlns"><graph id="G" edgedefault="directed">'
        '<node id="A"/><node id="B"/>'
        '<edge source="B" target="A"/></graph></graphml>'
    )

    output = tmp_path / "merged.graphml"
    result = runner.invoke(
        cli,
        [
            "merge-graphs",
            "-i",
            str(graphml1),
            "-i",
            str(graphml2),
            "-o",
            str(output),
        ],
    )

    assert result.exit_code == 0
    assert "Merged 2 graphs" in result.output
    assert output.exists()


# merge-graphs with weights requires cache input.
def test_merge_graph_weights_requires_cache(runner, tmp_path):
    import json

    graphml1 = tmp_path / "g1.graphml"
    graphml1.write_text(
        '<?xml version="1.0"?><graphml xmlns="http://graphml.graphdrawing.org'
        '/xmlns"><graph id="G" edgedefault="directed">'
        '<node id="A"/><node id="B"/>'
        '<edge source="A" target="B"/></graph></graphml>'
    )

    # Create a valid weights JSON file
    weights_file = tmp_path / "weights.json"
    weights_file.write_text(json.dumps({"algorithm": {"pc": 1.0}}))

    output = tmp_path / "merged.graphml"
    result = runner.invoke(
        cli,
        [
            "merge-graphs",
            "-i",
            str(graphml1),
            "-o",
            str(output),
            "-w",
            str(weights_file),
        ],
    )

    assert result.exit_code != 0
    assert "require .db cache" in result.output


# merge-graphs with --cpdag flag succeeds.
def test_merge_graph_with_cpdag(runner, tmp_path):
    graphml1 = tmp_path / "g1.graphml"
    graphml1.write_text(
        '<?xml version="1.0"?><graphml xmlns="http://graphml.graphdrawing.org'
        '/xmlns"><graph id="G" edgedefault="directed">'
        '<node id="A"/><node id="B"/>'
        '<edge source="A" target="B"/></graph></graphml>'
    )

    output = tmp_path / "merged.graphml"
    result = runner.invoke(
        cli,
        [
            "merge-graphs",
            "-i",
            str(graphml1),
            "-o",
            str(output),
            "--object-type=cpdag",
        ],
    )

    assert result.exit_code == 0
    assert output.exists()


# merge-graphs with invalid JSON weights file still fails on cache requirement.
def test_merge_graph_invalid_weights_json_requires_cache(runner, tmp_path):
    graphml1 = tmp_path / "g1.graphml"
    graphml1.write_text(
        '<?xml version="1.0"?><graphml xmlns="http://graphml.graphdrawing.org'
        '/xmlns"><graph id="G" edgedefault="directed">'
        '<node id="A"/><node id="B"/>'
        '<edge source="A" target="B"/></graph></graphml>'
    )

    # Create invalid JSON (cache check happens before JSON is loaded)
    weights_file = tmp_path / "weights.json"
    weights_file.write_text("not valid json")

    output = tmp_path / "merged.graphml"
    result = runner.invoke(
        cli,
        [
            "merge-graphs",
            "-i",
            str(graphml1),
            "-o",
            str(output),
            "-w",
            str(weights_file),
        ],
    )

    # Cache requirement is checked before JSON is loaded
    assert result.exit_code != 0
    assert "require .db cache" in result.output


# merge-graphs fails with non-existent weights file.
def test_merge_graph_weights_file_not_found(runner, tmp_path):
    graphml1 = tmp_path / "g1.graphml"
    graphml1.write_text(
        '<?xml version="1.0"?><graphml xmlns="http://graphml.graphdrawing.org'
        '/xmlns"><graph id="G" edgedefault="directed">'
        '<node id="A"/><node id="B"/>'
        '<edge source="A" target="B"/></graph></graphml>'
    )

    output = tmp_path / "merged.graphml"
    result = runner.invoke(
        cli,
        [
            "merge-graphs",
            "-i",
            str(graphml1),
            "-o",
            str(output),
            "-w",
            "nonexistent.json",
        ],
    )

    assert result.exit_code != 0
    # Click checks file existence due to type=click.Path(exists=True)
    assert "does not exist" in result.output or "Path" in result.output


# merge-graphs fails with invalid GraphML file.
def test_merge_graph_invalid_graphml(runner, tmp_path):
    # Create a file that exists but contains invalid GraphML
    invalid_file = tmp_path / "invalid.graphml"
    invalid_file.write_text("this is not valid graphml")

    output = tmp_path / "merged.graphml"
    result = runner.invoke(
        cli, ["merge-graphs", "-i", str(invalid_file), "-o", str(output)]
    )

    assert result.exit_code != 0
    assert "Failed to read" in result.output


# merge-graphs fails when graphs have different nodes.
def test_merge_graph_different_nodes(runner, tmp_path):
    graphml1 = tmp_path / "g1.graphml"
    graphml1.write_text(
        '<?xml version="1.0"?><graphml xmlns="http://graphml.graphdrawing.org'
        '/xmlns"><graph id="G" edgedefault="directed">'
        '<node id="A"/><node id="B"/>'
        '<edge source="A" target="B"/></graph></graphml>'
    )
    graphml2 = tmp_path / "g2.graphml"
    graphml2.write_text(
        '<?xml version="1.0"?><graphml xmlns="http://graphml.graphdrawing.org'
        '/xmlns"><graph id="G" edgedefault="directed">'
        '<node id="X"/><node id="Y"/>'
        '<edge source="X" target="Y"/></graph></graphml>'
    )

    output = tmp_path / "merged.graphml"
    result = runner.invoke(
        cli,
        [
            "merge-graphs",
            "-i",
            str(graphml1),
            "-i",
            str(graphml2),
            "-o",
            str(output),
        ],
    )

    assert result.exit_code != 0
    assert "Merge failed" in result.output


# merge-graphs fails when output directory is not writable.
def test_merge_graph_write_error(runner, tmp_path, monkeypatch):
    graphml1 = tmp_path / "g1.graphml"
    graphml1.write_text(
        '<?xml version="1.0"?><graphml xmlns="http://graphml.graphdrawing.org'
        '/xmlns"><graph id="G" edgedefault="directed">'
        '<node id="A"/><node id="B"/>'
        '<edge source="A" target="B"/></graph></graphml>'
    )

    output = tmp_path / "merged.graphml"

    # Mock open to raise an error
    original_open = open

    def mock_open(path, *args, **kwargs):
        if "merged.graphml" in str(path):
            raise PermissionError("Cannot write to file")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", mock_open)

    result = runner.invoke(
        cli, ["merge-graphs", "-i", str(graphml1), "-o", str(output)]
    )

    assert result.exit_code != 0
    assert "Failed to write" in result.output


# merge-graphs handles ImportError when causaliq-workflow not installed.
def test_merge_graph_import_error(runner, tmp_path, monkeypatch):
    cache_file = tmp_path / "test.db"
    cache_file.touch()  # Create empty file to pass click.Path(exists=True)
    output = tmp_path / "merged.graphml"

    # Mock the import to raise ImportError
    original_import = __builtins__["__import__"]

    def mock_import(name, *args, **kwargs):
        if name == "causaliq_workflow.cache":
            raise ImportError("No module named 'causaliq_workflow'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", mock_import)

    result = runner.invoke(
        cli, ["merge-graphs", "-i", str(cache_file), "-o", str(output)]
    )

    assert result.exit_code != 0
    assert "causaliq-workflow is required" in result.output


# merge-graphs handles FileNotFoundError for cache file.
def test_merge_graph_cache_file_not_found(runner, tmp_path, monkeypatch):
    from unittest.mock import MagicMock

    cache_file = tmp_path / "test.db"
    cache_file.touch()  # Create to pass click validation
    output = tmp_path / "merged.graphml"

    # Mock WorkflowCache to raise FileNotFoundError during open
    mock_cache_class = MagicMock()
    mock_cache_class.return_value.__enter__ = MagicMock(
        side_effect=FileNotFoundError("Cache file not found")
    )

    monkeypatch.setattr(
        "causaliq_analysis.cli.WorkflowCache",
        mock_cache_class,
        raising=False,
    )

    # Need to patch the import inside the function
    original_import = __builtins__["__import__"]

    def mock_import(name, *args, **kwargs):
        if name == "causaliq_workflow.cache":
            module = MagicMock()
            module.WorkflowCache = mock_cache_class
            return module
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", mock_import)

    result = runner.invoke(
        cli, ["merge-graphs", "-i", str(cache_file), "-o", str(output)]
    )

    assert result.exit_code != 0
    assert "Cache file not found" in result.output


# merge-graphs handles generic exception when reading cache.
def test_merge_graph_cache_generic_error(runner, tmp_path, monkeypatch):
    from unittest.mock import MagicMock

    cache_file = tmp_path / "test.db"
    cache_file.touch()
    output = tmp_path / "merged.graphml"

    mock_cache_class = MagicMock()
    mock_cache_class.return_value.__enter__ = MagicMock(
        side_effect=RuntimeError("Something went wrong")
    )

    original_import = __builtins__["__import__"]

    def mock_import(name, *args, **kwargs):
        if name == "causaliq_workflow.cache":
            module = MagicMock()
            module.WorkflowCache = mock_cache_class
            return module
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", mock_import)

    result = runner.invoke(
        cli, ["merge-graphs", "-i", str(cache_file), "-o", str(output)]
    )

    assert result.exit_code != 0
    assert "Failed to read from cache" in result.output


# merge-graphs handles cache.get() returning None.
def test_merge_graph_cache_get_returns_none(runner, tmp_path, monkeypatch):
    from io import StringIO
    from unittest.mock import MagicMock

    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    cache_file = tmp_path / "test.db"
    cache_file.touch()
    output = tmp_path / "merged.graphml"

    # Create a mock cache that returns None for some entries
    dag = DAG(["A", "B"], [("A", "->", "B")])
    buf = StringIO()
    graphml.write(dag, buf)
    graphml_content = buf.getvalue()

    mock_entry = MagicMock()
    mock_entry.metadata = {"sample_size": 1000}
    mock_entry.object_types.return_value = ["dag"]
    mock_obj = MagicMock()
    mock_obj.type = "dag"
    mock_obj.format = "graphml"
    mock_obj.content = graphml_content
    mock_entry.get_object.return_value = mock_obj

    mock_cache = MagicMock()
    mock_cache.list_entries.return_value = [
        {"matrix_values": {"seed": 1}},
        {"matrix_values": {"seed": 2}},  # This one will return None
    ]

    # First call returns entry, second returns None
    mock_cache.get.side_effect = [mock_entry, None]

    mock_cache_class = MagicMock()
    mock_cache_class.return_value.__enter__ = MagicMock(
        return_value=mock_cache
    )
    mock_cache_class.return_value.__exit__ = MagicMock(return_value=False)

    original_import = __builtins__["__import__"]

    def mock_import(name, *args, **kwargs):
        if name == "causaliq_workflow.cache":
            module = MagicMock()
            module.WorkflowCache = mock_cache_class
            return module
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", mock_import)

    result = runner.invoke(
        cli, ["merge-graphs", "-i", str(cache_file), "-o", str(output)]
    )

    assert result.exit_code == 0
    assert "Merged 1 graphs" in result.output


# merge-graphs handles generic exception loading weights file.
def test_merge_graph_weights_generic_error(runner, tmp_path, monkeypatch):
    from io import StringIO
    from unittest.mock import MagicMock

    from causaliq_core.graph import DAG
    from causaliq_core.graph.io import graphml

    cache_file = tmp_path / "test.db"
    cache_file.touch()
    output = tmp_path / "merged.graphml"
    weights_file = tmp_path / "weights.json"
    weights_file.write_text('{"sample_size": {"1000": 1.0}}')

    # Create mock cache with valid data
    dag = DAG(["A", "B"], [("A", "->", "B")])
    buf = StringIO()
    graphml.write(dag, buf)
    graphml_content = buf.getvalue()

    mock_entry = MagicMock()
    mock_entry.metadata = {"sample_size": 1000}
    mock_entry.object_types.return_value = ["dag"]
    mock_obj = MagicMock()
    mock_obj.type = "dag"
    mock_obj.format = "graphml"
    mock_obj.content = graphml_content
    mock_entry.get_object.return_value = mock_obj

    mock_cache = MagicMock()
    mock_cache.list_entries.return_value = [{"matrix_values": {"seed": 1}}]
    mock_cache.get.return_value = mock_entry

    mock_cache_class = MagicMock()
    mock_cache_class.return_value.__enter__ = MagicMock(
        return_value=mock_cache
    )
    mock_cache_class.return_value.__exit__ = MagicMock(return_value=False)

    original_import = __builtins__["__import__"]

    def mock_import(name, *args, **kwargs):
        if name == "causaliq_workflow.cache":
            module = MagicMock()
            module.WorkflowCache = mock_cache_class
            return module
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", mock_import)

    # Mock open to raise an unexpected error when reading weights
    original_open = open

    def mock_open(path, *args, **kwargs):
        if "weights.json" in str(path) and "r" in args:
            raise OSError("Unexpected I/O error")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", mock_open)

    result = runner.invoke(
        cli,
        [
            "merge-graphs",
            "-i",
            str(cache_file),
            "-o",
            str(output),
            "-w",
            str(weights_file),
        ],
    )

    assert result.exit_code != 0
    assert "Failed to load weights file" in result.output


# Help shows plot command.
def test_cli_help_shows_plot(runner):
    """Main CLI help lists the plot command."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "plot" in result.output


# plot command help displays correct usage and options.
def test_plot_help(runner):
    """The plot command help shows usage and options."""
    result = runner.invoke(cli, ["plot", "--help"])
    assert result.exit_code == 0
    assert "Plot charts from a summarise CSV output" in result.output
    assert "--input" in result.output
    assert "--output" in result.output
    assert "--subplot" in result.output
    assert "--group" in result.output
    assert "--property" in result.output


# plot command fails when required options are missing.
def test_plot_missing_options(runner):
    """The plot command fails without required options."""
    result = runner.invoke(cli, ["plot"])
    assert result.exit_code != 0
    assert "Missing option" in result.output
