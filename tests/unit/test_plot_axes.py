"""Unit tests for the plot axis styling and annotation helpers."""

import matplotlib.pyplot as plt
import pytest

from causaliq_analysis.plot import (
    _plot_violin_means,
    _report_boxplot_values,
    _set_axes_props,
)


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
