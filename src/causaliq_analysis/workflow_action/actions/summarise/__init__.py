"""
Summarise workflow action.

Aggregates numerical metrics from cache entries into summary statistics
(mean, standard deviation, count) and writes them to a CSV file. The action
is stateless, so validation and execution delegate to module-level helpers
and each step stays within the module and method limits.

The action class lives in ``action`` and delegates to ``request`` (parameter
parsing and validation), ``execution`` (collect, compute, render), ``collect``
(value collection from entries and caches), ``stats`` (statistic computation)
and ``render_csv`` (CSV output). Public names are re-exported here so the
provider and existing imports keep working.

The package is laid out for the reporting stage: ``collect`` grows named
source columns, ``stats`` grows the statistic vocabulary, and sibling
modules ``columns``, ``tests`` and ``render_latex`` slot in beside
``render_csv`` without changing the action.
"""

from .action import SummariseAction

__all__ = ["SummariseAction"]
