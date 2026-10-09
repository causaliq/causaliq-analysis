"""
Analysis workflow action sub-package.

Individual workflow actions live here as small single-responsibility
classes. ``ACTION_CLASSES`` maps workflow action names to their classes so
the provider can validate and execute them without knowing their details.
"""

from typing import Dict, Type

from causaliq_analysis.workflow_action.actions.base import AnalysisAction
from causaliq_analysis.workflow_action.actions.plot import PlotAction

__all__ = ["ACTION_CLASSES", "PlotAction"]

# Registry mapping action names to action classes
ACTION_CLASSES: Dict[str, Type[AnalysisAction]] = {
    "plot": PlotAction,
}
