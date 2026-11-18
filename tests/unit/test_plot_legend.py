"""Unit tests for the in-panel legend helpers."""

from types import SimpleNamespace
from typing import Any, Tuple

import matplotlib.pyplot as plt

from causaliq_analysis.plot.legend import (
    apply_legend,
    apply_scatter_legend,
    apply_subplot_legends,
)


def _grid() -> Tuple[Any, Any]:
    """Return a grid with two subplots and a figure legend."""
    figure, (first, second) = plt.subplots(1, 2)
    first.set_title("subplot = alpha")
    second.set_title("subplot = beta")
    first.plot([1, 2], [1, 2], label="one")
    first.plot([1, 2], [2, 1], label="two")
    handles, labels = first.get_legend_handles_labels()
    legend = figure.legend(handles, labels)
    grid = SimpleNamespace(
        fig=figure,
        axes=SimpleNamespace(flat=[first, second]),
        _legend=legend,
    )
    return grid, [(first, "alpha"), (second, "beta")]


# The legend is moved into every named subplot.
def test_apply_subplot_legends() -> None:
    """Test apply_subplot_legends draws a legend in each subplot."""
    grid, subplots = _grid()
    props = {"legend.subplots": ["alpha", "beta"]}
    assert apply_subplot_legends(grid, props, subplots) is True
    assert grid._legend is None
    assert subplots[0][0].get_legend() is not None
    assert subplots[1][0].get_legend() is not None
    plt.close(grid.fig)


# The 'all' value selects every subplot.
def test_apply_subplot_legends_all() -> None:
    """Test apply_subplot_legends accepts the 'all' value."""
    grid, subplots = _grid()
    assert apply_subplot_legends(grid, {"legend.subplots": "all"}, subplots)
    assert subplots[1][0].get_legend() is not None
    plt.close(grid.fig)


# A single name selects one subplot only.
def test_apply_subplot_legends_single() -> None:
    """Test apply_subplot_legends draws the legend on one subplot."""
    grid, subplots = _grid()
    apply_subplot_legends(grid, {"legend.subplots": "beta"}, subplots)
    assert subplots[0][0].get_legend() is None
    assert subplots[1][0].get_legend() is not None
    plt.close(grid.fig)


# No property leaves the grid legend in place.
def test_apply_subplot_legends_absent() -> None:
    """Test apply_subplot_legends does nothing without the property."""
    grid, subplots = _grid()
    assert apply_subplot_legends(grid, {}, subplots) is False
    assert grid._legend is not None
    plt.close(grid.fig)


# The legend labels, title and frame opacity are applied.
def test_apply_subplot_legends_properties() -> None:
    """Test apply_subplot_legends applies the legend properties."""
    grid, subplots = _grid()
    props = {
        "legend.subplots": ["alpha"],
        "legend.labels": {"one": "First", "two": "Second"},
        "legend.title": "source",
        "legend.framealpha": 0.9,
        "legend.ncol": 2,
        "legend.loc": "lower left",
    }
    apply_subplot_legends(grid, props, subplots)
    legend = subplots[0][0].get_legend()
    assert [text.get_text() for text in legend.texts] == ["First", "Second"]
    assert legend.get_title().get_text() == "source"
    assert legend.get_frame().get_alpha() == 0.9
    plt.close(grid.fig)


# A grid with no legend cannot produce in-panel legends.
def test_apply_subplot_legends_without_legend() -> None:
    """Test apply_subplot_legends returns False without a legend."""
    figure, (axes, _) = plt.subplots(1, 2)
    grid = SimpleNamespace(
        fig=figure, axes=SimpleNamespace(flat=[axes]), _legend=None
    )
    assert not apply_subplot_legends(
        grid, {"legend.subplots": "all"}, [(axes, "alpha")]
    )
    plt.close(figure)


# An empty legend title clears the title assigned by seaborn.
def test_set_legend_title_clears() -> None:
    """An empty legend.title property clears the title."""
    from unittest.mock import MagicMock

    from causaliq_analysis.plot.legend import set_legend_title

    legend = MagicMock()
    set_legend_title(legend, {"legend.title": ""})
    legend.set_title.assert_called_once_with("")


# The chart legend is drawn inside the panel when requested.
def test_apply_legend_in_panel() -> None:
    """Test apply_legend returns after drawing in-panel legends."""
    grid, subplots = _grid()
    apply_legend(grid, subplots, {"legend.subplots": ["alpha"]})
    assert grid._legend is None
    assert subplots[0][0].get_legend() is not None
    plt.close(grid.fig)


# The scatter legend is drawn inside the panels when requested.
def test_apply_scatter_legend_in_panel() -> None:
    """Test apply_scatter_legend returns after in-panel legends."""
    grid, subplots = _grid()
    apply_scatter_legend(grid, subplots, {"legend.subplots": "all"})
    assert subplots[1][0].get_legend() is not None
    plt.close(grid.fig)


# An axes legend is used when the grid has no figure legend.
def test_apply_subplot_legends_axes_legend() -> None:
    """Test apply_subplot_legends moves an axes-level legend."""
    figure, (first, second) = plt.subplots(1, 2)
    first.plot([1, 2], [1, 2], label="one")
    second.plot([1, 2], [2, 1], label="second")
    second.legend(loc="lower right")
    grid = SimpleNamespace(
        fig=figure, axes=SimpleNamespace(flat=[first, second]), _legend=None
    )
    assert apply_subplot_legends(
        grid,
        {"legend.subplots": ["alpha"]},
        [(first, "alpha"), (second, "beta")],
    )
    assert first.get_legend() is not None
    assert second.get_legend() is None
    plt.close(figure)


# The legend font sizes are applied in the panel.
def test_apply_subplot_legends_fontsizes() -> None:
    """Test apply_subplot_legends applies the legend font sizes."""
    grid, subplots = _grid()
    props = {
        "legend.subplots": ["alpha"],
        "legend.title": "source",
        "legend.fontsize": 13,
        "legend.title_fontsize": 14,
    }
    apply_subplot_legends(grid, props, subplots)
    legend = subplots[0][0].get_legend()
    assert legend.get_texts()[0].get_fontsize() == 13
    assert legend.get_title().get_fontsize() == 14
    plt.close(grid.fig)
