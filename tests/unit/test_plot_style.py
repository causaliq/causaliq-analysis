"""Unit tests for the plot figure styling helpers."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from causaliq_analysis.plot.style import (
    apply_figure_size,
    apply_figure_title,
    apply_layout,
    apply_layout_or_adjust,
    save_figure,
    theme_rc_params,
)


def _grid() -> SimpleNamespace:
    """Return a minimal grid holding an open figure."""
    figure, _ = plt.subplots()
    return SimpleNamespace(fig=figure)


# No theme property yields no rc parameters.
def test_theme_rc_params_empty() -> None:
    """Test theme_rc_params returns an empty mapping without a theme."""
    assert theme_rc_params({}) == {}


# A theme property yields the suite of Seaborn axes parameters.
def test_theme_rc_params_whitegrid() -> None:
    """Test theme_rc_params returns the whitegrid axes style."""
    params = theme_rc_params({"theme": "whitegrid"})
    assert params["axes.grid"] is True
    assert params["axes.axisbelow"] is True


# The figure size property sets the figure dimensions in inches.
def test_apply_figure_size() -> None:
    """Test apply_figure_size sets the figure size in inches."""
    g = _grid()
    apply_figure_size(g, {"figure.size": (14, 6)})
    assert tuple(g.fig.get_size_inches()) == (14, 6)
    plt.close(g.fig)


# No figure size property leaves the figure unchanged.
def test_apply_figure_size_absent() -> None:
    """Test apply_figure_size keeps the figure size when unset."""
    g = _grid()
    before = tuple(g.fig.get_size_inches())
    apply_figure_size(g, {})
    assert tuple(g.fig.get_size_inches()) == before
    plt.close(g.fig)


# The layout property applies the requested layout engine.
def test_apply_layout() -> None:
    """Test apply_layout sets the requested layout engine."""
    figure = MagicMock()
    grid = SimpleNamespace(fig=figure)
    assert apply_layout(grid, {"figure.layout": "tight"})
    figure.set_layout_engine.assert_called_once_with("tight")


# An unsupported layout engine leaves the figure unchanged.
def test_apply_layout_unknown() -> None:
    """Test apply_layout ignores an unsupported layout engine."""
    figure = MagicMock()
    grid = SimpleNamespace(fig=figure)
    assert not apply_layout(grid, {"figure.layout": "grid"})
    figure.set_layout_engine.assert_not_called()


# The figure title property sets the text, size and weight.
def test_apply_figure_title() -> None:
    """Test apply_figure_title sets a bold figure title."""
    g = _grid()
    apply_figure_title(
        g,
        {
            "figure.title": "Results",
            "figure.title_fontsize": 15,
            "figure.title_fontweight": "bold",
        },
    )
    title = g.fig._suptitle
    assert title.get_text() == "Results"
    assert title.get_fontsize() == 15
    assert title.get_fontweight() == "bold"
    plt.close(g.fig)


# No figure title property adds no title.
def test_apply_figure_title_absent() -> None:
    """Test apply_figure_title adds no title when unset."""
    g = _grid()
    apply_figure_title(g, {})
    assert g.fig._suptitle is None
    plt.close(g.fig)


# The save helper forwards the dpi and the tight bounding box.
def test_save_figure(tmp_path: Any) -> None:
    """Test save_figure passes the dpi and bounding box to matplotlib."""
    figure = MagicMock(spec=Figure)
    path = str(tmp_path / "chart.png")
    save_figure(
        SimpleNamespace(fig=figure),
        {"figure.dpi": 150, "figure.bbox_inches": "tight"},
        path,
        80,
    )
    figure.savefig.assert_called_once_with(path, dpi=150, bbox_inches="tight")


# The save helper uses the default dpi when no property is set.
def test_save_figure_default_dpi(tmp_path: Any) -> None:
    """Test save_figure uses the default dpi without a property."""
    figure = MagicMock(spec=Figure)
    path = str(tmp_path / "chart.png")
    save_figure(SimpleNamespace(fig=figure), {}, path, 600)
    figure.savefig.assert_called_once_with(path, dpi=600)


# A layout engine takes precedence over the subplot adjustments.
def test_apply_layout_or_adjust_layout() -> None:
    """Test apply_layout_or_adjust applies the layout engine only."""
    figure = MagicMock()
    grid = SimpleNamespace(fig=figure)
    apply_layout_or_adjust(grid, {"figure.layout": "tight"})
    figure.set_layout_engine.assert_called_once_with("tight")
    figure.subplots_adjust.assert_not_called()


# Without a layout engine the subplot adjustments are applied.
def test_apply_layout_or_adjust_adjust() -> None:
    """Test apply_layout_or_adjust applies the subplot adjustments."""
    figure = MagicMock()
    grid = SimpleNamespace(fig=figure)
    apply_layout_or_adjust(grid, {"figure.subplots_top": 0.9})
    figure.set_layout_engine.assert_not_called()
    figure.subplots_adjust.assert_called_once_with(top=0.9)
