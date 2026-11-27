"""Parsing and validating significance specifications for summarise.

A specification names a registered test and its one or two sample columns::

    wilcoxon-signed-rank-2-sided(fusion, bnsl) as "Fusion vs BNSL"

The ``as`` label is optional; without it the label is derived from the
argument aliases. Arguments must name aliases declared by the metric list.
"""

import re
from typing import Sequence, Set

from .significance import (
    SIGNIFICANCE_TESTS,
    SignificanceSpec,
    SignificanceTest,
)

__all__ = [
    "_parse_significance_spec",
    "_parse_significance_specs",
]

_SPEC_PATTERN = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9_-]*)\("
    r"(?P<arguments>[^()]*)\)"
    r"(?:\s+as\s+(?P<label>.+))?$"
)


def _parse_significance_specs(
    specs: Sequence[str],
    aliases: Set[str],
) -> list[SignificanceSpec]:
    """Parse and validate every significance specification.

    Args:
        specs: Specification strings in declaration order.
        aliases: Aliases declared by the metric list.

    Returns:
        Parsed significance specifications.

    Raises:
        ValueError: If a specification is invalid, an alias is unknown, a
            label is repeated or the rows use different tests.
    """
    parsed = [_parse_significance_spec(spec, aliases) for spec in specs]
    _require_single_test(parsed)
    _require_unique_labels(parsed)
    return parsed


def _parse_significance_spec(
    spec: str,
    aliases: Set[str],
) -> SignificanceSpec:
    """Parse and validate one significance specification.

    Args:
        spec: Specification string.
        aliases: Aliases declared by the metric list.

    Returns:
        Parsed significance specification.

    Raises:
        ValueError: If the specification is invalid.
    """
    match = _SPEC_PATTERN.match(spec.strip())
    if match is None:
        raise ValueError(
            f"Invalid significance spec '{spec}': use "
            "'<test>(<left>, <right>) [as <label>]'"
        )
    name = match.group("name")
    test = _require_test(name, spec)
    arguments = _split_arguments(match.group("arguments"), spec)
    _require_arity(test, arguments, spec)
    _require_aliases(arguments, aliases, spec)
    label = _spec_label(match.group("label"), arguments)
    text = spec.split(" as ", 1)[0].strip()
    return SignificanceSpec(
        text=text,
        test=test,
        left=arguments[0],
        right=arguments[1] if len(arguments) > 1 else None,
        label=label,
    )


def _require_test(name: str, spec: str) -> SignificanceTest:
    """Return the registered test, or raise for an unknown name.

    Args:
        name: Test name from the specification.
        spec: Full specification, used in the error message.

    Returns:
        Registered test.

    Raises:
        ValueError: If the test is not registered.
    """
    test = SIGNIFICANCE_TESTS.get(name)
    if test is None:
        supported = ", ".join(sorted(SIGNIFICANCE_TESTS))
        raise ValueError(
            f"Unknown significance test '{name}' in '{spec}'. "
            f"Supported: {supported}"
        )
    return test


def _split_arguments(arguments: str, spec: str) -> list[str]:
    """Return the non-empty argument names of a specification.

    Args:
        arguments: Text inside the parentheses.
        spec: Full specification, used in the error message.

    Returns:
        Argument names in declaration order.

    Raises:
        ValueError: If an argument is empty.
    """
    names = [name.strip() for name in arguments.split(",")]
    if not all(names):
        raise ValueError(
            f"Invalid significance spec '{spec}': missing an argument"
        )
    return names


def _require_arity(
    test: SignificanceTest,
    arguments: Sequence[str],
    spec: str,
) -> None:
    """Require the declared argument count to match the test arity.

    Args:
        test: Registered test.
        arguments: Declared argument names.
        spec: Full specification, used in the error message.

    Raises:
        ValueError: If the argument count does not match the test.
    """
    if len(arguments) != test.arity:
        raise ValueError(
            f"Significance test '{test.name}' takes {test.arity} "
            f"argument(s) in '{spec}', got {len(arguments)}"
        )


def _require_aliases(
    arguments: Sequence[str],
    aliases: Set[str],
    spec: str,
) -> None:
    """Require every argument to name a declared metric alias.

    Args:
        arguments: Declared argument names.
        aliases: Aliases declared by the metric list.
        spec: Full specification, used in the error message.

    Raises:
        ValueError: If an argument names an unknown alias.
    """
    for argument in arguments:
        if argument in aliases:
            continue
        available = ", ".join(sorted(aliases)) or "none"
        raise ValueError(
            f"Unknown column '{argument}' in significance spec "
            f"'{spec}'. Declare it with 'as <alias>' in metric. "
            f"Available: {available}"
        )


def _spec_label(
    label: str | None,
    arguments: Sequence[str],
) -> str:
    """Return the declared label, or one derived from the arguments.

    Args:
        label: Declared label, or None.
        arguments: Declared argument names.

    Returns:
        Comparison label for the result row.
    """
    if label and label.strip():
        return _strip_quotes(label.strip())
    return " vs ".join(arguments)


def _strip_quotes(text: str) -> str:
    """Return text without a matching pair of surrounding quotes.

    Args:
        text: Label text to normalise.

    Returns:
        The text without matching single or double quotes.
    """
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1].strip()
    return text


def _require_single_test(specs: Sequence[SignificanceSpec]) -> None:
    """Require every test in one table to use the same registered test.

    Args:
        specs: Parsed significance specifications.

    Raises:
        ValueError: If the specifications use different tests.
    """
    names = {spec.test.name for spec in specs}
    if len(names) > 1:
        raise ValueError(
            "All significance tests in one table must use the same test; "
            f"got {', '.join(sorted(names))}"
        )


def _require_unique_labels(specs: Sequence[SignificanceSpec]) -> None:
    """Require comparison labels to be unique.

    Args:
        specs: Parsed significance specifications.

    Raises:
        ValueError: If two rows use the same label.
    """
    labels: Set[str] = set()
    for spec in specs:
        if spec.label in labels:
            raise ValueError(
                f"Significance label '{spec.label}' is declared twice"
            )
        labels.add(spec.label)
