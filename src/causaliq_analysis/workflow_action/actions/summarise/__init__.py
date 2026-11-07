"""
Summarise workflow action.

Aggregates numerical metrics from cache entries into summary statistics
(mean, standard deviation, count) and writes a table in CSV, LaTeX or
Markdown format, named by the output extension. The action is stateless,
so validation and execution delegate to module-level helpers and each step
stays within the module and method limits.

The action class lives in ``action`` and delegates to ``request``
(parameter parsing and validation), ``execution`` (collect, compute,
render), ``collect`` (value collection from entries and caches),
``columns`` (column specifications), ``formula`` (derived columns),
``stats`` (statistic computation), ``present`` (display columns shared by
the renderers), ``footer`` (footer rows) and ``render`` (renderer
selection). Public names are re-exported here so the provider and
existing imports keep working.

The output extension selects the renderer: ``.csv`` writes raw values,
``.tex`` writes a LaTeX ``tabular`` fragment and ``.md`` writes a
Markdown table. Only the presentation formats apply the ``format`` and
``footer`` parameters, so a ``plot`` step can still read a CSV
numerically.
"""

from .action import SummariseAction

__all__ = ["SummariseAction"]
