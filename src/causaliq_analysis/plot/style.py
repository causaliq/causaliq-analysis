"""Figure-level styling helpers for the plot charts.

The helpers apply the optional theme, figure size, layout engine, title
weights and save options read from the chart properties. They live outside
``plot.charts`` so each module stays within the code size limits.
"""

from typing import Any

import seaborn as sns

from causaliq_analysis.plot.axes import SUBPLOT_ADJUST

# Layout engines accepted by the figure.layout property.
LAYOUT_ENGINES = ("tight", "constrained")

# Facet keywords which catplot also accepts as explicit parameters.
CATPLOT_FACET_PROPS = frozenset({"sharex", "sharey", "legend_out"})

# Default font size of the figure super-title.
DEFAULT_TITLE_SIZE = 30


__all__ = [
    "CATPLOT_FACET_PROPS",
    "LAYOUT_ENGINES",
    "apply_figure_size",
    "apply_figure_title",
    "apply_layout",
    "apply_layout_or_adjust",
    "catplot_kwargs",
    "save_figure",
    "scatter_kws",
    "scatter_markers",
    "theme_rc_params",
]


def theme_rc_params(props: dict[str, Any]) -> dict[str, Any]:
    """Return the rc parameters of the requested Seaborn axes style.

    Args:
        props: chart properties holding an optional ``theme``.

    Returns:
        Dictionary of rc parameters, empty when no theme is requested.
    """
    style = props.get("theme")
    if not style:
        return {}
    return dict(sns.axes_style(style))


def apply_figure_size(g: Any, props: dict[str, Any]) -> None:
    """Set an exact figure size in inches.

    Args:
        g: Seaborn figure grid.
        props: chart properties holding an optional ``figure.size``.
    """
    size = props.get("figure.size")
    if not size:
        return
    width, height = size
    g.fig.set_size_inches(width, height)


def apply_layout(g: Any, props: dict[str, Any]) -> bool:
    """Apply the requested figure layout engine.

    Args:
        g: Seaborn figure grid.
        props: chart properties holding an optional ``figure.layout``.

    Returns:
        True when a layout engine was applied, otherwise False.
    """
    layout = props.get("figure.layout")
    if layout not in LAYOUT_ENGINES:
        return False
    g.fig.set_layout_engine(layout)
    return True


def apply_layout_or_adjust(g: Any, props: dict[str, Any]) -> None:
    """Apply the layout engine, or the subplot adjustments when absent.

    Args:
        g: Seaborn figure grid.
        props: chart properties holding an optional ``figure.layout`` and
            the ``figure.subplots_*`` adjustments.
    """
    if apply_layout(g, props):
        return
    adjust = {p: props[k] for k, p in SUBPLOT_ADJUST.items() if k in props}
    if adjust:
        g.fig.subplots_adjust(**adjust)


def catplot_kwargs(
    props: dict[str, Any], facet_kws: dict[str, Any]
) -> dict[str, Any]:
    """Return the explicit catplot parameters and facet keywords.

    ``sharex``, ``sharey`` and ``legend_out`` are explicit catplot
    parameters, so they are removed from the facet keywords to avoid a
    duplicate keyword argument.

    Args:
        props: chart properties holding the shared-axis and legend
            settings.
        facet_kws: facet keywords derived from the chart properties.

    Returns:
        Keyword arguments for :func:`seaborn.catplot`.
    """
    return {
        "sharex": props.get("xaxis.shared", True),
        "sharey": props.get("yaxis.shared", True),
        "legend_out": props.get("legend.outside", True),
        "facet_kws": {
            key: value
            for key, value in facet_kws.items()
            if key not in CATPLOT_FACET_PROPS
        },
    }


def scatter_markers(props: dict[str, Any]) -> Any:
    """Return the marker of each hue group, or a single marker."""
    markers = props.get("scatter.markers")
    if not markers:
        return "o"
    return markers[0] if len(markers) == 1 else markers


def scatter_kws(props: dict[str, Any]) -> dict[str, Any]:
    """Return the scatter keyword arguments from the properties."""
    kws: dict[str, Any] = {}
    if "scatter.size" in props:
        kws["s"] = props["scatter.size"]
    if "scatter.alpha" in props:
        kws["alpha"] = props["scatter.alpha"]
    return kws


def apply_figure_title(g: Any, props: dict[str, Any]) -> None:
    """Set the figure super-title when requested.

    Args:
        g: Seaborn figure grid.
        props: chart properties with optional ``figure.title``,
            ``figure.title_fontsize`` and ``figure.title_fontweight``.
    """
    if "figure.title" not in props:
        return
    size = props.get("figure.title_fontsize", DEFAULT_TITLE_SIZE)
    g.fig.suptitle(
        props["figure.title"],
        size=size,
        fontweight=props.get("figure.title_fontweight"),
    )


def save_figure(
    g: Any, props: dict[str, Any], plot_file: str, default_dpi: int
) -> None:
    """Save the figure to a file at the configured dpi.

    Args:
        g: Seaborn figure grid.
        props: chart properties with optional ``figure.dpi`` and
            ``figure.bbox_inches``.
        plot_file: path of the output image file.
        default_dpi: resolution used when ``figure.dpi`` is not set.
    """
    dpi = props.get("figure.dpi", default_dpi)
    kwargs: dict[str, Any] = {}
    bbox = props.get("figure.bbox_inches")
    if bbox:
        kwargs["bbox_inches"] = bbox
    g.fig.savefig(plot_file, dpi=dpi, **kwargs)
