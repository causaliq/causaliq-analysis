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


# Migrate-trace command help displays correct usage and options.
def test_migrate_trace_help(runner):
    result = runner.invoke(cli, ["migrate-trace", "--help"])
    assert result.exit_code == 0
    assert "Migrate legacy Trace pickle files" in result.output
    assert "--network" in result.output
    assert "--series" in result.output
    assert "--root-dir" in result.output


# Migrate-trace command fails when required options are missing.
def test_migrate_trace_missing_options(runner):
    result = runner.invoke(cli, ["migrate-trace"])
    assert result.exit_code != 0
    assert "Missing option" in result.output


# Help shows merge-graph command.
def test_cli_help_shows_merge_graph(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "merge-graph" in result.output


# Merge-graph command help displays correct usage and options.
def test_merge_graph_help(runner):
    result = runner.invoke(cli, ["merge-graph", "--help"])
    assert result.exit_code == 0
    assert "Merge multiple graphs" in result.output
    assert "--output" in result.output
    assert "--weights" in result.output
    assert "INPUTS" in result.output


# Merge-graph command fails when no inputs provided.
def test_merge_graph_no_inputs(runner):
    result = runner.invoke(cli, ["merge-graph", "-o", "out.graphml"])
    assert result.exit_code != 0
    assert "Missing argument" in result.output


# Merge-graph command fails when output not provided.
def test_merge_graph_no_output(runner, tmp_path):
    graphml_file = tmp_path / "test.graphml"
    graphml_file.write_text(
        '<?xml version="1.0"?><graphml xmlns="http://graphml.graphdrawing.org'
        '/xmlns"><graph id="G" edgedefault="directed">'
        '<node id="A"/><node id="B"/>'
        '<edge source="A" target="B"/></graph></graphml>'
    )
    result = runner.invoke(cli, ["merge-graph", str(graphml_file)])
    assert result.exit_code != 0
    assert "Missing option" in result.output


# Merge-graph succeeds with valid GraphML files.
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
        cli, ["merge-graph", str(graphml1), str(graphml2), "-o", str(output)]
    )

    assert result.exit_code == 0
    assert "Merged 2 graphs" in result.output
    assert output.exists()


# Merge-graph with custom weights succeeds.
def test_merge_graph_with_weights(runner, tmp_path):
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
            "merge-graph",
            str(graphml1),
            str(graphml2),
            "-o",
            str(output),
            "-w",
            "0.7,0.3",
        ],
    )

    assert result.exit_code == 0
    assert output.exists()


# Merge-graph fails with mismatched weights count.
def test_merge_graph_weights_mismatch(runner, tmp_path):
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
        ["merge-graph", str(graphml1), "-o", str(output), "-w", "0.5,0.5"],
    )

    assert result.exit_code != 0
    assert "must match" in result.output


# Merge-graph fails with invalid weights format.
def test_merge_graph_invalid_weights(runner, tmp_path):
    graphml1 = tmp_path / "g1.graphml"
    graphml1.write_text(
        '<?xml version="1.0"?><graphml xmlns="http://graphml.graphdrawing.org'
        '/xmlns"><graph id="G" edgedefault="directed">'
        '<node id="A"/><node id="B"/>'
        '<edge source="A" target="B"/></graph></graphml>'
    )

    output = tmp_path / "merged.graphml"
    result = runner.invoke(
        cli, ["merge-graph", str(graphml1), "-o", str(output), "-w", "abc"]
    )

    assert result.exit_code != 0
    assert "Invalid weights" in result.output


# Merge-graph fails with invalid GraphML file.
def test_merge_graph_invalid_graphml(runner, tmp_path):
    # Create a file that exists but contains invalid GraphML
    invalid_file = tmp_path / "invalid.graphml"
    invalid_file.write_text("this is not valid graphml")

    output = tmp_path / "merged.graphml"
    result = runner.invoke(
        cli, ["merge-graph", str(invalid_file), "-o", str(output)]
    )

    assert result.exit_code != 0
    assert "Failed to read" in result.output


# Merge-graph fails when graphs have different nodes.
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
        cli, ["merge-graph", str(graphml1), str(graphml2), "-o", str(output)]
    )

    assert result.exit_code != 0
    assert "Merge failed" in result.output


# Merge-graph fails when output directory is not writable.
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
        cli, ["merge-graph", str(graphml1), "-o", str(output)]
    )

    assert result.exit_code != 0
    assert "Failed to write" in result.output
