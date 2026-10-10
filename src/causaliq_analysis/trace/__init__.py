"""Detailed tracing of structure learning processes.

The package re-exports the public names previously available from the
``causaliq_analysis.trace`` module, so existing imports and the backward
compatibility class mapping keep resolving:

- ``Trace`` and ``CONTEXT_FIELDS`` from ``trace.trace``;
- ``DiffType`` from ``trace.diffs``;
- ``CompatibilityUnpickler`` and ``load_with_compatibility`` from
  ``trace.compatibility``.
"""

from causaliq_analysis.trace.compatibility import (
    CompatibilityUnpickler,
    load_with_compatibility,
)
from causaliq_analysis.trace.diffs import DiffType
from causaliq_analysis.trace.trace import CONTEXT_FIELDS, Trace

__all__ = [
    "CompatibilityUnpickler",
    "CONTEXT_FIELDS",
    "DiffType",
    "Trace",
    "load_with_compatibility",
]
