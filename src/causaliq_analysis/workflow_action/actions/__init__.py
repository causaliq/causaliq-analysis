"""
Analysis workflow action sub-package.

Individual workflow actions live here as small single-responsibility
classes. ``ACTION_CLASSES`` maps workflow action names to their classes so
the provider can validate and execute them without knowing their details.
"""

from typing import Dict, Type

from causaliq_analysis.workflow_action.actions.base import AnalysisAction
from causaliq_analysis.workflow_action.actions.best_graph import (
    BestGraphAction,
)
from causaliq_analysis.workflow_action.actions.evaluate_graph import (
    EvaluateGraphAction,
)
from causaliq_analysis.workflow_action.actions.merge_graphs import (
    MergeGraphsAction,
)
from causaliq_analysis.workflow_action.actions.migrate_trace import (
    MigrateTraceAction,
)
from causaliq_analysis.workflow_action.actions.plot import PlotAction

__all__ = [
    "ACTION_CLASSES",
    "BestGraphAction",
    "EvaluateGraphAction",
    "MergeGraphsAction",
    "MigrateTraceAction",
    "PlotAction",
]

# Registry mapping action names to action classes
ACTION_CLASSES: Dict[str, Type[AnalysisAction]] = {
    "best_graph": BestGraphAction,
    "evaluate_graph": EvaluateGraphAction,
    "merge_graphs": MergeGraphsAction,
    "migrate_trace": MigrateTraceAction,
    "plot": PlotAction,
}
