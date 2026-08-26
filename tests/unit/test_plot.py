"""Unit tests for the plot module."""

import os

os.environ.setdefault("MPLBACKEND", "Agg")  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")  # noqa: E402

from types import SimpleNamespace  # noqa: E402
from unittest.mock import patch  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402
from pandas import DataFrame  # noqa: E402

from causaliq_analysis.plot import (  # noqa: E402
    SUPPORTED_KINDS,
    _plot_violin_means,
    _report_boxplot_values,
    _set_axes_props,
    parse_properties,
    plot_degree_distribution,
    plot_scatter,
    relplot,
    run_plot,
)


def _make_relplot_data() -> DataFrame:
    """Return small long-form data for relplot tests."""
    return DataFrame(
        {
            "subplot": ["a", "a", "a", "b", "b", "b"],
            "x_val": [1, 2, 3, 1, 2, 3],
            "y_var": ["s1", "s1", "s1", "s1", "s1", "s1"],
            "y_val": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        }
    )


def _make_box_data() -> DataFrame:
    """Return data with repeated categories for box/violin plots."""
    return DataFrame(
        {
            "subplot": ["a"] * 6,
            "x_val": [1, 1, 2, 2, 3, 3],
            "y_var": ["s1"] * 6,
            "y_val": [0.1, 0.2, 0.15, 0.3, 0.25, 0.35],
        }
    )


@pytest.fixture(autouse=True)
def _close_figures():
    """Close any matplotlib figures after each test."""
    yield
    plt.close("all")


# Parse properties converts scalar values to correct types.
def test_parse_properties_scalars():
    """Test parse_properties converts scalars to their types."""
    props = parse_properties(
        [
            "subplot.aspect:1.05",
            "figure.subplots_top:0.9",
            "subplot.grid:True",
            "legend.outside:False",
        ]
    )
    assert props["subplot.aspect"] == 1.05
    assert props["figure.subplots_top"] == 0.9
    assert props["subplot.grid"] is True
    assert props["legend.outside"] is False


# Parse properties converts blank values to empty strings.
def test_parse_properties_blank_value():
    """Test parse_properties handles blank and no-value properties."""
    props = parse_properties(["figure.title:", "subplot.kind"])
    assert props["figure.title"] == ""
    assert props["subplot.kind"] == ""


# Parse properties converts the not symbol to None.
def test_parse_properties_not_symbol():
    """Test parse_properties converts the not symbol to None."""
    props = parse_properties(["yaxis.range:¬"])
    assert props["yaxis.range"] is None


# Parse properties converts tuples, lists and dicts.
def test_parse_properties_collections():
    """Test parse_properties handles tuples, lists and dicts."""
    props = parse_properties(
        [
            "yaxis.range:(0,1.05)",
            "xaxis.ticks:[10,100,1000]",
            "palette:[#66bd63,#d73027]",
            "legend.labels:{a,A,b,B}",
        ]
    )
    assert props["yaxis.range"] == (0, 1.05)
    assert props["xaxis.ticks"] == [10, 100, 1000]
    assert props["palette"] == ["#66bd63", "#d73027"]
    assert props["legend.labels"] == {"a": "A", "b": "B"}


# Parse properties accepts a single string input.
def test_parse_properties_string_input():
    """Test parse_properties accepts a single property string."""
    props = parse_properties("subplot.aspect:2.0")
    assert props["subplot.aspect"] == 2.0


# Parse properties returns an empty dict for None input.
def test_parse_properties_none():
    """Test parse_properties returns an empty dict for None input."""
    assert parse_properties(None) == {}


# Parse properties raises ValueError for malformed strings.
def test_parse_properties_malformed():
    """Test parse_properties raises ValueError for bad property names."""
    with pytest.raises(ValueError, match="Malformed plot property"):
        parse_properties([":1.05"])


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


# Set axes props applies simple axis properties.
def test_set_axes_props_simple():
    """Test _set_axes_props applies xaxis and yaxis properties."""
    fig, axes = plt.subplots()
    _set_axes_props(
        axes,
        {
            "xaxis.label": "Sample size",
            "yaxis.label": "F1",
            "xaxis.range": (0, 10),
            "yaxis.range": (0, 1.05),
            "xaxis.scale": "log",
        },
        "a",
    )
    assert axes.get_xlabel() == "Sample size"
    assert axes.get_ylabel() == "F1"
    assert axes.get_xlim() == (0, 10)
    assert axes.get_ylim() == (0, 1.05)
    assert axes.get_xscale() == "log"


# Set axes props applies subplot-specific dict values.
def test_set_axes_props_subplot_dict():
    """Test _set_axes_props selects values for the current subplot."""
    fig, axes = plt.subplots()
    _set_axes_props(
        axes,
        {
            "yaxis.range": {"a": (0, 1), "b": (0, 2)},
            "xaxis.ticks": {"a": [1, 2, 3]},
        },
        "a",
    )
    assert axes.get_ylim() == (0, 1)
    assert list(axes.get_xticks()) == [1, 2, 3]


# Set axes props uses current values for other subplots.
def test_set_axes_props_other_subplot():
    """Test _set_axes_props keeps values for a different subplot."""
    fig, axes = plt.subplots()
    axes.set_xlim(0, 100)
    _set_axes_props(axes, {"xaxis.range": {"a": (0, 10)}}, "b")
    assert axes.get_xlim() == (0, 100)


# Set axes props sets custom x-axis tick labels.
def test_set_axes_props_tick_labels():
    """Test _set_axes_props applies custom tick labels."""
    fig, axes = plt.subplots()
    axes.set_xticks([0, 1, 2])
    _set_axes_props(
        axes,
        {
            "xaxis.tick_labels": ["one", "two", "three"],
        },
        "a",
    )
    labels = [t.get_text() for t in axes.get_xticklabels()]
    assert labels == ["one", "two", "three"]


# Set axes props rotates and aligns x-axis tick labels.
def test_set_axes_props_tick_rotation():
    """Test _set_axes_props applies tick rotation and alignment."""
    fig, axes = plt.subplots()
    _set_axes_props(
        axes,
        {
            "xaxis.ticks_rotation": 45,
            "xaxis.ticks_halign": "right",
        },
        "a",
    )
    rotation = axes.get_xticklabels()[0].get_rotation()
    assert rotation == 45.0


# Set axes props inverts bars with a negative range.
def test_set_axes_props_yaxis_invert():
    """Test _set_axes_props inverts bars using the yaxis range."""
    fig, axes = plt.subplots()
    axes.bar([1, 2], [0.5, 0.8])
    _set_axes_props(
        axes,
        {
            "yaxis.invert": {"a": True},
            "yaxis.range": {"a": (-1, 0)},
        },
        "a",
    )
    bars = axes.patches
    assert bars[0].get_y() == -1
    assert bars[0].get_height() == pytest.approx(1.5)


# Relplot raises ValueError for unsupported kinds.
def test_relplot_bad_kind(tmp_path):
    """Test relplot raises ValueError for unsupported kinds."""
    with pytest.raises(ValueError, match="bad arg values"):
        relplot(
            _make_relplot_data(),
            {"subplot.kind": "pie"},
            str(tmp_path / "out.png"),
        )


# Relplot generates line charts.
def test_relplot_line(tmp_path):
    """Test relplot produces a line chart."""
    out_path = tmp_path / "line.png"
    relplot(_make_relplot_data(), {"subplot.kind": "line"}, str(out_path))
    assert out_path.exists()
    assert out_path.stat().st_size > 0


# Relplot generates bar charts.
def test_relplot_bar(tmp_path):
    """Test relplot produces a bar chart."""
    out_path = tmp_path / "bar.png"
    relplot(_make_box_data(), {"subplot.kind": "bar"}, str(out_path))
    assert out_path.exists()


# Relplot generates box plots.
def test_relplot_box(tmp_path):
    """Test relplot produces a box plot."""
    out_path = tmp_path / "box.png"
    relplot(_make_box_data(), {"subplot.kind": "box"}, str(out_path))
    assert out_path.exists()


# Relplot generates violin plots.
def test_relplot_violin(tmp_path):
    """Test relplot produces a violin plot."""
    out_path = tmp_path / "violin.png"
    props = {"subplot.kind": "violin", "violin.scale": "width"}
    relplot(_make_box_data(), props, str(out_path))
    assert out_path.exists()


# Relplot generates histograms using the weight column.
def test_relplot_histogram(tmp_path):
    """Test relplot produces a histogram plot."""
    data = _make_relplot_data()
    data["weight"] = [1] * len(data)
    out_path = tmp_path / "hist.png"
    relplot(data, {"subplot.kind": "histogram"}, str(out_path))
    assert out_path.exists()


# Relplot generates regression plots.
def test_relplot_regression(tmp_path):
    """Test relplot produces a regression plot."""
    out_path = tmp_path / "regression.png"
    relplot(
        _make_relplot_data(),
        {"subplot.kind": "regression"},
        str(out_path),
    )
    assert out_path.exists()


# Relplot applies figure title and legend properties.
def test_relplot_figure_and_legend_props(tmp_path):
    """Test relplot applies figure title, legend title and labels."""
    data = _make_relplot_data()
    props = {
        "subplot.kind": "line",
        "figure.title": "My title",
        "figure.title_fontsize": 20,
        "legend.title": "Series",
        "legend.labels": {"s1": "Series one"},
        "figure.subplots_top": 0.95,
        "subplot.grid": True,
    }
    out_path = tmp_path / "props.png"
    relplot(data, props, str(out_path))
    assert out_path.exists()
    fig = plt.gcf()
    assert fig.axes[0].get_title().startswith("subplot")
    assert fig.axes[0].get_xgridlines()


# Relplot applies the legend.title property to the grid legend.
def test_relplot_legend_key(tmp_path):
    """Test relplot sets the legend title on the grid legend."""
    props = {
        "subplot.kind": "box",
        "legend.key": {"Alpha": "#66bd63"},
        "legend.loc": "lower right",
        "legend.ncol": 2,
        "legend.title": "Key",
    }
    out_path = tmp_path / "legend_key.png"
    relplot(_make_box_data(), props, str(out_path))
    assert out_path.exists()


# Relplot builds a manual legend when the grid has no legend.
def test_relplot_legend_key_no_legend(tmp_path):
    """Test relplot uses legend.key to create a legend when none exists."""
    fig, axes = plt.subplots()
    axes.set_title("subplot = a")
    fake_grid = SimpleNamespace(
        fig=fig,
        axes=np.array([[axes]], dtype=object),
        _legend=None,
    )
    props = {
        "subplot.kind": "box",
        "legend.key": {"Alpha": "#66bd63", "Beta": "#d73027"},
        "legend.loc": "lower right",
        "legend.ncol": 2,
        "legend.title": "Key",
    }
    out_path = tmp_path / "legend_key_manual.png"
    with patch("seaborn.catplot", return_value=fake_grid):
        relplot(_make_box_data(), props, str(out_path))
    assert out_path.exists()


# Relplot displays means on violin plots when info is provided.
def test_relplot_violin_with_info(tmp_path, capsys):
    """Test relplot adds mean labels to violin subplots with info."""
    info = {
        "a": {
            "1": {"mean": 0.15},
            "2": {"mean": 0.25},
            "3": {"mean": 0.3},
        }
    }
    out_path = tmp_path / "violin_info.png"
    relplot(
        _make_box_data(),
        {"subplot.kind": "violin"},
        str(out_path),
        info=info,
    )
    assert out_path.exists()
    captured = capsys.readouterr()
    assert "Data for 1 is {'mean': 0.15}" in captured.out


# Report boxplot values prints data and adds mean labels.
def test_report_boxplot_values(capsys):
    """Test _report_boxplot_values reports boxplot statistics."""
    axes = _FakeAxes()
    _report_boxplot_values(axes, {"0": {"mean": 0.5}, "1": {"mean": 0.6}})
    captured = capsys.readouterr()
    assert "Box plot values are" in captured.out
    assert len(axes.texts) == 2


# Report boxplot values returns early when info is None.
def test_report_boxplot_values_no_info(capsys):
    """Test _report_boxplot_values does nothing without info."""
    axes = _FakeAxes()
    _report_boxplot_values(axes, None)
    captured = capsys.readouterr()
    assert captured.out == ""


# Plot violin means adds mean labels to the axes.
def test_plot_violin_means(capsys):
    """Test _plot_violin_means displays means on violin plots."""
    axes = _FakeAxes()
    _plot_violin_means(
        axes, {"0": {"mean": 0.5}, "1": {"mean": 0.6}}, {"violin.fontsize": 12}
    )
    captured = capsys.readouterr()
    assert "Data for 0 is {'mean': 0.5}" in captured.out
    assert len(axes.texts) == 2


# Plot scatter generates a scatter plot.
def test_plot_scatter(tmp_path):
    """Test plot_scatter produces a scatter plot file."""
    out_path = tmp_path / "scatter.png"
    props = {
        "figure.title": "Scatter",
        "palette": ["#66bd63", "#d73027"],
        "legend.title": "Series",
        "legend.labels": {"s1": "Series one"},
        "figure.subplots_top": 0.95,
    }
    plot_scatter(_make_relplot_data(), props, str(out_path))
    assert out_path.exists()
    assert out_path.stat().st_size > 0


# Plot degree distribution generates a distribution plot.
def test_plot_degree_distribution(tmp_path):
    """Test plot_degree_distribution produces a distribution plot."""
    dist = DataFrame(
        {
            "network": ["asia", "asia", "sports", "sports"],
            "metric": ["in", "total", "in", "total"],
            "value": [2, 5, 3, 6],
        }
    )
    out_path = tmp_path / "degrees.png"
    plot_degree_distribution(dist, str(out_path))
    assert out_path.exists()


# Supported kinds contains the expected plot types.
def test_supported_kinds():
    """Test SUPPORTED_KINDS contains all legacy plot kinds."""
    assert SUPPORTED_KINDS == {
        "line",
        "regression",
        "histogram",
        "box",
        "violin",
        "bar",
        "scatter",
    }


class _FakeAxes:
    """Simple mock axes for boxplot value reporting tests."""

    def __init__(self):
        lines = []
        for box in (
            (0.25, 0.75, 0.1, 0.9, 0.5, (0.05, 0.95)),
            (0.35, 0.85, 0.2, 1.0, 0.6, ()),
        ):
            for item in box:
                ydata = item if isinstance(item, tuple) else (item,)
                lines.append(_FakeLine(ydata))
        self.lines = lines
        self.texts = []

    def get_lines(self):
        return self.lines

    def get_xticklabels(self):
        return [_FakeLabel("0"), _FakeLabel("1")]

    def get_xticks(self):
        return [0, 1]

    def text(self, x, y, text, **kwargs):
        self.texts.append((x, y, text))


class _FakeLine:
    """Mock matplotlib line with fixed ydata."""

    def __init__(self, ydata):
        self.ydata = ydata

    def get_ydata(self):
        return self.ydata


class _FakeLabel:
    """Mock matplotlib text label."""

    def __init__(self, text):
        self.text = text

    def get_text(self):
        return self.text


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
