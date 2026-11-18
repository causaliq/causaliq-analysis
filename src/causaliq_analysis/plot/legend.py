"""Legend helpers for the plot charts.

The helpers draw the chart legend once per figure, or inside selected
subplots, and apply the legend location, title, labels and frame opacity.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# Property naming the subplots which carry their own legend.
SUBPLOT_PROP = "legend.subplots"

# Value of the property which selects every subplot.
ALL_SUBPLOTS = "all"

# Pairs of axes and subplot name.
Subplot = Tuple[Any, str]


__all__ = [
    "ALL_SUBPLOTS",
    "SUBPLOT_PROP",
    "apply_legend",
    "apply_scatter_legend",
    "apply_subplot_legends",
    "move_legend",
    "set_legend_labels",
    "set_legend_title",
]


def apply_legend(
    g: Any, subplots: Sequence[Subplot], props: Dict[str, Any]
) -> None:
    """Apply the chart legend.

    Args:
        g: Seaborn figure grid holding the chart.
        subplots: pairs of axes and subplot name.
        props: chart properties defining the legend.
    """
    if apply_subplot_legends(g, props, subplots):
        return
    legend = getattr(g, "_legend", None)
    if legend is None and "legend.key" in props:
        legend = _build_manual_legend(props)
    move_legend(legend, props)
    set_legend_title(legend, props)
    set_legend_labels(legend, props)


def apply_scatter_legend(
    g: Any, subplots: Sequence[Subplot], props: Dict[str, Any]
) -> None:
    """Apply the legend of a scatter chart.

    Args:
        g: Seaborn figure grid holding the chart.
        subplots: pairs of axes and subplot name.
        props: chart properties defining the legend.
    """
    if apply_subplot_legends(g, props, subplots):
        return
    legend = getattr(g, "_legend", None)
    move_legend(legend, props)
    set_legend_title(legend, props, size=18)
    set_legend_labels(legend, props)


def apply_subplot_legends(
    g: Any, props: Dict[str, Any], subplots: Sequence[Subplot]
) -> bool:
    """Draw the chart legend inside the configured subplots.

    The grid legend is removed and rebuilt on each selected subplot so
    the legend keys, labels and title are unchanged.

    Args:
        g: Seaborn figure grid holding the chart.
        props: chart properties holding an optional ``legend.subplots``.
        subplots: pairs of axes and subplot name, captured before any
            custom subplot title is applied.

    Returns:
        True when in-panel legends were drawn, otherwise False.
    """
    targets = _legend_targets(props, subplots)
    if not targets:
        return False
    entries = _take_legend(g)
    if entries is None:
        return False
    handles, labels = entries
    for axes in targets:
        _add_axes_legend(axes, handles, labels, props)
    return True


def _legend_targets(
    props: Dict[str, Any], subplots: Sequence[Subplot]
) -> List[Any]:
    """Return the axes which should carry an in-panel legend."""
    wanted = props.get(SUBPLOT_PROP)
    if not wanted:
        return []
    if wanted == ALL_SUBPLOTS:
        return [axes for axes, _ in subplots]
    if isinstance(wanted, str):
        wanted = [wanted]
    return [axes for axes, name in subplots if name in wanted]


def _take_legend(g: Any) -> Optional[Tuple[List[Any], List[str]]]:
    """Remove the grid legend and return its handles and labels."""
    legend = getattr(g, "_legend", None)
    if legend is None:
        legend = _axes_legend(g)
    if legend is None:
        return None
    handles = list(legend.legend_handles)
    labels = [text.get_text() for text in legend.texts]
    legend.remove()
    if getattr(g, "_legend", None) is legend:
        g._legend = None
    return handles, labels


def _axes_legend(g: Any) -> Any:
    """Return the legend of the last subplot, if any."""
    for axes in reversed(list(g.axes.flat)):
        legend = axes.get_legend()
        if legend is not None:
            return legend
    return None


def _add_axes_legend(
    axes: Any,
    handles: List[Any],
    labels: List[str],
    props: Dict[str, Any],
) -> Any:
    """Add one legend to an axes using the configured properties."""
    legend = axes.legend(handles, labels, **_legend_kwargs(props))
    set_legend_labels(legend, props)
    return legend


def _legend_kwargs(props: Dict[str, Any]) -> Dict[str, Any]:
    """Return the matplotlib legend keyword arguments."""
    kwargs: Dict[str, Any] = {}
    if "legend.loc" in props:
        kwargs["loc"] = props["legend.loc"]
    if "legend.ncol" in props:
        kwargs["ncol"] = props["legend.ncol"]
    if props.get("legend.title"):
        kwargs["title"] = props["legend.title"]
    if "legend.fontsize" in props:
        kwargs["fontsize"] = props["legend.fontsize"]
    if "legend.title_fontsize" in props:
        kwargs["title_fontsize"] = props["legend.title_fontsize"]
    if "legend.framealpha" in props:
        kwargs["framealpha"] = props["legend.framealpha"]
    return kwargs


def move_legend(legend: Any, props: Dict[str, Any]) -> None:
    """Move an existing legend to the configured location.

    The legend object is kept so its title and labels survive the move;
    rebuilding it with ``add_legend`` would leave the original drawn as
    well.

    Args:
        legend: legend to move, or None.
        props: chart properties holding an optional ``legend.loc``.
    """
    if legend is None or "legend.loc" not in props:
        return
    loc = props["legend.loc"]
    if hasattr(legend, "set_loc"):
        legend.set_loc(loc)
    else:  # pragma: no cover - older matplotlib
        legend._set_loc(loc)


def set_legend_title(
    legend: Any, props: Dict[str, Any], size: Optional[int] = None
) -> None:
    """Set the legend title, optionally at a fixed font size.

    An empty ``legend.title`` clears the title assigned by seaborn.
    """
    if legend is None or "legend.title" not in props:
        return
    title = props["legend.title"]
    if not title:
        legend.set_title("")
    elif size is None:
        legend.set_title(title)
    else:
        legend.set_title(title, {"size": size})


def set_legend_labels(legend: Any, props: Dict[str, Any]) -> None:
    """Apply the legend.labels mapping to the legend entries."""
    if legend is None or "legend.labels" not in props:
        return
    for label in legend.texts:
        metric = label.get_text()
        if metric in props["legend.labels"]:
            label.set_text(props["legend.labels"][metric])


def _build_manual_legend(props: Dict[str, Any]) -> Any:
    """Build a legend from the legend.key property."""
    loc = props["legend.loc"] if "legend.loc" in props else None
    ncol = props["legend.ncol"] if "legend.ncol" in props else 1
    artists = [
        Patch(fc=colour, ec="gray", label=key)
        for key, colour in props["legend.key"].items()
    ]
    return plt.legend(handles=artists, handlelength=1, ncol=ncol, loc=loc)
