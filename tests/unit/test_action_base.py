"""Unit tests for the analysis action base contract."""

from typing import Any, Dict, Optional

import pytest

from causaliq_analysis.workflow_action import (
    ActionPattern,
    ActionResult,
    ActionValidationError,
)
from causaliq_analysis.workflow_action.actions.base import AnalysisAction


class _StubAction(AnalysisAction):
    """Minimal concrete action used to exercise the base contract."""

    action_name = "stub"
    required_parameters = ("input",)

    def run(
        self,
        parameters: Dict[str, Any],
        mode: str,
        context: Optional[Any] = None,
        logger: Optional[Any] = None,
    ) -> ActionResult:
        """Return a minimal successful result."""
        return ("success", {"action": self.action_name}, [])


# Test a concrete action exposes its declared action name
def test_concrete_action_name() -> None:
    assert _StubAction().action_name == "stub"


# Test the default action pattern is NOCACHES
def test_base_action_pattern_default() -> None:
    assert _StubAction().pattern == ActionPattern.NOCACHES


# Test validate accepts parameters providing all required values
def test_validate_accepts_required_parameter() -> None:
    _StubAction().validate({"input": "pdg.graphml"})


# Test validate requires all declared required parameters
def test_validate_rejects_missing_parameter() -> None:
    with pytest.raises(ActionValidationError, match="requires input"):
        _StubAction().validate({})


# Test validate rejects an explicit None value for a required parameter
def test_validate_rejects_none_parameter() -> None:
    with pytest.raises(ActionValidationError):
        _StubAction().validate({"input": None})


# Test the abstract run contract raises NotImplementedError
def test_abstract_run_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        AnalysisAction.run(_StubAction(), {}, "run")


# Test the concrete run returns the documented result tuple
def test_stub_action_run_returns_result() -> None:
    status, metadata, objects = _StubAction().run({}, "run")
    assert status == "success"
    assert metadata["action"] == "stub"
    assert objects == []
