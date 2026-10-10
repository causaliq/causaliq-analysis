"""Unit tests for the plot chart builders."""

from types import SimpleNamespace
from unittest.mock import patch

import matplotlib.pyplot as plt
import numpy as np
import pytest
from pandas import DataFrame

from causaliq_analysis.plot import (
    SUPPORTED_KINDS,
    plot_degree_distribution,
    plot_scatter,
    relplot,
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
