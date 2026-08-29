"""Functional tests for the plot CLI command."""

import os
import re

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib  # noqa: E402

matplotlib.use("Agg")  # noqa: E402

from pathlib import Path  # noqa: E402

from causaliq_analysis.cli import cli  # noqa: E402

REFERENCE_DIR = Path(__file__).parent.parent / "data" / "functional"


def _ord_hc_f1_properties() -> list:
    """Return the properties which replicate the ord_hc_f1 figure."""
    return [
        "figure.subplots_top=0.98",
        "figure.subplots_left=0.04",
        "figure.subplots_right=0.86",
        "figure.subplots_hspace=0.22",
        "figure.subplots_wspace=0.2",
        "figure.per_row=2",
        "figure.title=",
        "subplot.aspect=1.05",
        "subplot.grid=True",
        "subplot.grid_colour=lightgray",
        "subplot.background=white",
        "subplot.axes_fontsize=22",
        "subplot.title_fontsize=22",
        "xaxis.ticks_fontsize=22",
        "yaxis.ticks_fontsize=22",
        "xaxis.scale=log",
        "xaxis.ticks=[10,100,1000,10000,100000,1000000,10000000]",
        "xaxis.range=(10,10000000)",
        "xaxis.label=Sample size",
        "yaxis.range=(0,1.05)",
        "yaxis.label=F1 (CPDAG)",
        "yaxis.shared=True",
        "legend.outside=True",
        "legend.fontsize=22",
        "legend.title_fontsize=22",
        "legend.title=variable ordering",
        "legend.labels={'BNLEARN/HC_OPT': 'optimal', 'BNLEARN/HC_BAD': "
        "'worst', 'BNLEARN/HC_STD': 'alphabetic'}",
        "palette=['#66bd63','#d73027','#000000']",
    ]


def _plot_args(input_path: Path, output_path: Path) -> list:
    """Return the CLI arguments for the ord_hc_f1 line chart."""
    args = [
        "plot",
        "-i",
        str(input_path),
        "-o",
        str(output_path),
        "--type",
        "line",
        "--subplot",
        "network",
        "--group",
        "series",
        "-x",
        "sample_size",
        "-y",
        "f1.mean",
    ]
    for prop in _ord_hc_f1_properties():
        args.extend(["-p", prop])
    return args


def _svg_replication_bytes(path: Path) -> bytes:
    """Return SVG content with generated artefacts removed.

    Matplotlib embeds a creation timestamp, its version string and random
    element IDs in the SVG metadata and defs, so these are stripped and
    normalised before comparison. The remaining vector content is
    deterministic across platforms for a given matplotlib version, unlike
    rasterised PNG output.
    """
    content = path.read_text(encoding="utf-8")
    content = re.sub(r"<metadata>.*?</metadata>", "", content, flags=re.DOTALL)
    content = _normalise_svg_ids(content)
    return content.encode("utf-8")


def _normalise_svg_ids(content: str) -> str:
    """Replace matplotlib's random element IDs with stable placeholders.

    Matplotlib assigns a new random identifier (e.g. ``p8cb8d4b024``) to
    each clip path and marker on every save, so the identifiers are
    replaced with sequential placeholders before comparison.
    """
    seen: dict[str, str] = {}

    def _repl(match: re.Match) -> str:
        prefix: str = match.group(1)
        guid: str = match.group(2)
        if guid not in seen:
            seen[guid] = f"{guid[0]}{len(seen) + 1}"
        return prefix + seen[guid]

    pattern = re.compile(r'(id="|url\(#|xlink:href="#)([mp][0-9a-f]{10})')
    return pattern.sub(_repl, content)


# Plot command help displays the available options.
def test_plot_help(cli_runner):
    """Test the plot command help shows all options."""
    result = cli_runner.invoke(cli, ["plot", "--help"])
    assert result.exit_code == 0
    assert "Plot charts from a summarise CSV output" in result.output
    assert "--input" in result.output
    assert "--subplot" in result.output
    assert "--group" in result.output
    assert "--property" in result.output


# Plot command fails when required options are missing.
def test_plot_missing_options(cli_runner):
    """Test the plot command fails without required options."""
    result = cli_runner.invoke(cli, ["plot"])
    assert result.exit_code != 0
    assert "Missing option" in result.output


# Plot command generates a line chart from a test CSV.
def test_plot_generates_line_chart(cli_runner, tmp_path):
    """Test the plot command produces an output image file."""
    input_path = REFERENCE_DIR / "ord_hc_f1.csv"
    output_path = tmp_path / "chart.png"

    result = cli_runner.invoke(cli, _plot_args(input_path, output_path))

    assert result.exit_code == 0, result.output
    assert output_path.exists()
    assert output_path.stat().st_size > 0


# Plot command output exactly replicates the reference SVG image.
def test_plot_exact_replication(cli_runner, tmp_path):
    """Test the plot output matches the legacy reference image exactly."""
    input_path = REFERENCE_DIR / "ord_hc_f1.csv"
    reference_path = REFERENCE_DIR / "ord_hc_f1.svg"
    output_path = tmp_path / "chart.svg"

    result = cli_runner.invoke(cli, _plot_args(input_path, output_path))

    assert result.exit_code == 0, result.output
    assert _svg_replication_bytes(output_path) == _svg_replication_bytes(
        reference_path
    )


# Plot command accepts equals-separated Python literal properties.
def test_plot_accepts_equals_properties(cli_runner, tmp_path):
    """Test the plot command accepts Python-typed property values."""
    input_path = tmp_path / "data.csv"
    input_path.write_text(
        "network,series,sample_size,f1.mean\nasia,s1,100,0.5\n"
    )
    output_path = tmp_path / "chart.png"

    result = cli_runner.invoke(
        cli,
        [
            "plot",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
            "--type",
            "line",
            "--subplot",
            "network",
            "--group",
            "series",
            "-x",
            "sample_size",
            "-y",
            "f1.mean",
            "-p",
            "figure.title='Test chart'",
            "-p",
            "yaxis.range=(0,1)",
        ],
    )

    assert result.exit_code == 0, result.output
    assert output_path.exists()


# Plot command converts action failures to click errors.
def test_plot_action_failure_raises_click_error(cli_runner, tmp_path):
    """Test the plot command reports action execution failures."""
    input_path = tmp_path / "data.csv"
    input_path.write_text("foo,bar\n1,2\n")
    output_path = tmp_path / "chart.png"

    result = cli_runner.invoke(
        cli,
        [
            "plot",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
            "--type",
            "line",
            "--subplot",
            "network",
            "--group",
            "series",
            "-x",
            "sample_size",
            "-y",
            "f1.mean",
        ],
    )

    assert result.exit_code != 0
    assert "Plot failed" in result.output


# Plot command reports a non-success action status.
def test_plot_non_success_status(cli_runner, tmp_path, monkeypatch):
    """Test the plot command reports a non-success action status."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    input_path = tmp_path / "data.csv"
    input_path.write_text(
        "network,series,sample_size,f1.mean\nasia,s1,100,0.5\n"
    )
    output_path = tmp_path / "chart.png"

    def fake_run(self, action, parameters, mode):
        return ("error", {"error": "boom"}, [])

    monkeypatch.setattr(AnalysisActionProvider, "run", fake_run)

    result = cli_runner.invoke(
        cli,
        [
            "plot",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
            "--type",
            "line",
            "--subplot",
            "network",
            "--group",
            "series",
            "-x",
            "sample_size",
            "-y",
            "f1.mean",
        ],
    )

    assert result.exit_code != 0
    assert "Action failed" in result.output
