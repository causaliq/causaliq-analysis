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
        ["merge-graphs", "-i", str(graphml1), "-o", str(output), "--cpdag"],
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
