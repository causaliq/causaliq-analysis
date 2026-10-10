"""Unit tests for the plot entry point."""

import pytest
from pandas import DataFrame

from causaliq_analysis.plot import run_plot


# Run plot rejects unknown plot kinds.
def test_run_plot_unknown_kind(tmp_path):
    """Test run_plot raises ValueError for unsupported kinds."""
    csv_path = tmp_path / "data.csv"
    DataFrame(
        {
            "subplot": ["a"],
            "group": ["g"],
            "x": [1],
            "y": [0.5],
        }
    ).to_csv(csv_path, index=False)
    with pytest.raises(ValueError, match="Unknown plot type"):
        run_plot(
            input_csv=str(csv_path),
            output=str(tmp_path / "out.png"),
            kind="pie",
            subplot="subplot",
            group="group",
            x="x",
            y="y",
        )


# Run plot raises ValueError when the input file is missing.
def test_run_plot_missing_file(tmp_path):
    """Test run_plot raises ValueError for a missing input file."""
    with pytest.raises(ValueError, match="Input file not found"):
        run_plot(
            input_csv=str(tmp_path / "missing.csv"),
            output=str(tmp_path / "out.png"),
            kind="line",
            subplot="subplot",
            group="group",
            x="x",
            y="y",
        )


# Run plot raises ValueError when required columns are missing.
def test_run_plot_missing_column(tmp_path):
    """Test run_plot raises ValueError for missing input columns."""
    csv_path = tmp_path / "data.csv"
    DataFrame({"subplot": ["a"]}).to_csv(csv_path, index=False)
    with pytest.raises(ValueError, match="missing required column"):
        run_plot(
            input_csv=str(csv_path),
            output=str(tmp_path / "out.png"),
            kind="line",
            subplot="subplot",
            group="group",
            x="x",
            y="y",
        )


# Run plot generates a line chart and metadata.
def test_run_plot_generates_line_chart(tmp_path):
    """Test run_plot produces an output chart file."""
    csv_path = tmp_path / "data.csv"
    DataFrame(
        {
            "subplot": ["a", "a"],
            "group": ["g1", "g1"],
            "x": [1, 2],
            "y": [0.5, 0.6],
        }
    ).to_csv(csv_path, index=False)
    out_path = tmp_path / "charts" / "out.png"
    metadata = run_plot(
        input_csv=str(csv_path),
        output=str(out_path),
        kind="line",
        subplot="subplot",
        group="group",
        x="x",
        y="y",
    )
    assert out_path.exists()
    assert out_path.stat().st_size > 0
    assert metadata["type"] == "line"
    assert metadata["columns"] == {
        "subplot": "subplot",
        "group": "group",
        "x": "x",
        "y": "y",
    }


# Run plot logs progress messages when a log function is provided.
def test_run_plot_logging(tmp_path, capsys):
    """Test run_plot calls the log function with progress messages."""
    csv_path = tmp_path / "data.csv"
    DataFrame(
        {
            "subplot": ["a"],
            "group": ["g1"],
            "x": [1],
            "y": [0.5],
        }
    ).to_csv(csv_path, index=False)
    messages = []
    run_plot(
        input_csv=str(csv_path),
        output=str(tmp_path / "out.png"),
        kind="line",
        subplot="subplot",
        group="group",
        x="x",
        y="y",
        log_fn=messages.append,
    )
    assert any("Plotting line" in m for m in messages)


# Run plot handles whitespace-padded column names and values.
def test_run_plot_strips_padded_columns(tmp_path):
    """Test run_plot tolerates whitespace-padded summarise CSV output."""
    csv_path = tmp_path / "padded.csv"
    csv_path.write_text(
        " network , series   , sample_size , f1.mean \n"
        " asia    , HC_STD   , 100         , 0.5     \n"
        " asia    , HC_OPT   , 100         , 0.7     \n"
    )
    out_path = tmp_path / "out.png"
    run_plot(
        input_csv=str(csv_path),
        output=str(out_path),
        kind="line",
        subplot="network",
        group="series",
        x="sample_size",
        y="f1.mean",
    )
    assert out_path.exists()


# Run plot generates a scatter chart when type is scatter.
def test_run_plot_scatter(tmp_path):
    """Test run_plot dispatches scatter plots to plot_scatter."""
    csv_path = tmp_path / "data.csv"
    DataFrame(
        {
            "subplot": ["a", "a"],
            "group": ["g1", "g1"],
            "x": [1, 2],
            "y": [0.5, 0.6],
        }
    ).to_csv(csv_path, index=False)
    out_path = tmp_path / "out.png"
    run_plot(
        input_csv=str(csv_path),
        output=str(out_path),
        kind="scatter",
        subplot="subplot",
        group="group",
        x="x",
        y="y",
    )
    assert out_path.exists()
