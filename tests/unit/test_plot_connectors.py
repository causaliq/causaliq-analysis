"""Unit tests for scatter connectors and bar chart styling."""

from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd


def _long_frame() -> pd.DataFrame:
    """Return long-form data with two groups at each x value."""
    return pd.DataFrame(
        {
            "subplot": ["all", "all", "all", "all"],
            "x_val": [1, 1, 2, 2],
            "y_var": ["a", "b", "a", "b"],
            "y_val": [0.2, 0.3, 0.5, 0.4],
        }
    )


def test_connect_axes_draws_one_line_per_pair() -> None:
    """One connector is drawn for each x value with two values."""
    import matplotlib.pyplot as plt

    from causaliq_analysis.plot.charts import _connect_axes

    frame = _long_frame()
    figure, axes = plt.subplots()
    _connect_axes(axes, frame)

    assert len(axes.lines) == 2
    plt.close(figure)


def test_connect_axes_skips_incomplete_groups() -> None:
    """An x value without exactly two values gets no connector."""
    import matplotlib.pyplot as plt

    from causaliq_analysis.plot.charts import _connect_axes

    frame = pd.DataFrame(
        {
            "x_val": [1, 1, 1, 2, 2],
            "y_val": [0.1, 0.2, 0.3, 0.4, 0.5],
        }
    )
    figure, axes = plt.subplots()
    _connect_axes(axes, frame)

    assert len(axes.lines) == 1
    plt.close(figure)


def test_connect_scatter_matches_subplot_titles() -> None:
    """Connectors are drawn on the subplot whose title names the panel."""
    from types import SimpleNamespace

    import matplotlib.pyplot as plt

    from causaliq_analysis.plot.charts import _connect_scatter

    figure, axes = plt.subplots()
    axes.set_title("subplot = all")
    grid = SimpleNamespace(axes=SimpleNamespace(flat=[axes]))
    _connect_scatter(grid, _long_frame())

    assert len(axes.lines) == 2
    plt.close(figure)


def test_build_bar_passes_palette_and_facets() -> None:
    """Bar charts receive the palette and facet parameters."""
    from causaliq_analysis.plot.charts import _build_bar, _FigureStyle

    style = _FigureStyle(
        palette=[(1.0, 0.0, 0.0)],
        facet_kws={"legend_out": True},
        col_wrap=None,
        aspect=1,
        rc_params={},
        sizes={},
        dashes={},
    )
    with patch("seaborn.catplot", return_value="grid") as mock_catplot:
        grid = _build_bar({}, _long_frame(), style)

    assert grid == "grid"
    kwargs = mock_catplot.call_args.kwargs
    assert kwargs["palette"] == [(1.0, 0.0, 0.0)]
    assert kwargs["facet_kws"] == {}
    assert kwargs["legend_out"] is True


def test_plot_scatter_disables_regression_and_connects(
    tmp_path: Any,
) -> None:
    """A scatter is drawn without a fitted line and with connectors."""
    from causaliq_analysis.plot.charts import plot_scatter

    grid = MagicMock()
    grid.axes.flat = [MagicMock()]
    grid.axes.flat[0].properties.return_value = {"title": "subplot = all"}
    with patch("seaborn.lmplot", return_value=grid) as mock_lmplot:
        with patch(
            "causaliq_analysis.plot.charts._connect_scatter"
        ) as mock_connect:
            plot_scatter(
                _long_frame(),
                {"scatter.connect": True},
                str(tmp_path / "scatter.png"),
            )

    assert mock_lmplot.call_args.kwargs["fit_reg"] is False
    mock_connect.assert_called_once()


def test_plot_scatter_without_connect(tmp_path: Any) -> None:
    """Connectors are not drawn unless the property is set."""
    from causaliq_analysis.plot.charts import plot_scatter

    grid = MagicMock()
    grid.axes.flat = []
    with patch("seaborn.lmplot", return_value=grid):
        with patch(
            "causaliq_analysis.plot.charts._connect_scatter"
        ) as mock_connect:
            plot_scatter(
                _long_frame(),
                {},
                str(tmp_path / "scatter.png"),
            )

    mock_connect.assert_not_called()


def test_plot_scatter_applies_legend_location(tmp_path: Any) -> None:
    """The legend location property moves the scatter legend."""
    from causaliq_analysis.plot.charts import plot_scatter

    grid = MagicMock()
    grid.axes.flat = []
    with patch("seaborn.lmplot", return_value=grid):
        plot_scatter(
            _long_frame(),
            {"legend.loc": "lower left"},
            str(tmp_path / "scatter.png"),
        )

    grid._legend.set_loc.assert_called_once_with("lower left")


# Connectors are paired by row key when an x value repeats.
def test_connect_axes_pairs_by_key() -> None:
    """Two networks sharing an x value get two short connectors."""
    import matplotlib.pyplot as plt

    from causaliq_analysis.plot.charts import _connect_axes

    frame = pd.DataFrame(
        {
            "x_val": [10, 10, 10, 10],
            "y_val": [0.2, 0.25, 0.6, 0.7],
            "row_key": ["a", "a", "b", "b"],
        }
    )
    figure, axes = plt.subplots()
    _connect_axes(axes, frame)

    assert len(axes.lines) == 2
    assert list(axes.lines[0].get_ydata()) == [0.2, 0.25]
    plt.close(figure)


# Connectors use the configured colour and width.
def test_connect_axes_style() -> None:
    """The connector style properties are applied to each line."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_hex

    from causaliq_analysis.plot.charts import _connect_axes

    figure, axes = plt.subplots()
    _connect_axes(
        axes,
        _long_frame(),
        {
            "scatter.connect_colour": "#123456",
            "scatter.connect_linewidth": 2,
        },
    )
    line = axes.lines[0]
    assert to_hex(line.get_color()) == "#123456"
    assert line.get_linewidth() == 2
    plt.close(figure)
