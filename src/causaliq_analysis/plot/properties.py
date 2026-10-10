"""Parsing of chart property strings into typed values.

Property strings use the form ``<name>=<value>`` where the value is
written in Python literal syntax. The parser lives here as a
self-contained group so the chart builders and the runner can share it.
"""

import ast
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Sentinel returned when a property value is not a Python literal.
_NOT_A_LITERAL = object()


def _try_literal(value: str) -> Any:
    """Return the value parsed as a Python literal, or a sentinel.

    Args:
        value: string value to parse.

    Returns:
        The parsed literal, or ``_NOT_A_LITERAL`` when parsing fails.
    """
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError, TypeError):
        return _NOT_A_LITERAL


def _convert_value(value: Optional[str]) -> Any:
    """Convert a string property value to its correct type.

    The value is parsed as a Python literal first, so ``22`` becomes an
    integer, ``0.23`` a float, ``'string value'`` a string, ``(2, 'dad')``
    a tuple, ``['a', 1, 2.3]`` a list, ``{'key1': 1, 'key2': 'me'}`` a
    dict and ``{1, 'two'}`` a set. Values which are not valid Python
    literals (e.g. ``lightgray``) fall back to legacy conversions:
    integers and floats are converted, blank values become ``""`` and
    the ``¬`` character converts to ``None`` (used to blank a property).

    Args:
        value: string value to convert, or None for a blank value.

    Returns:
        Value converted to the appropriate type.
    """
    if value is None:
        return ""
    if value == "¬":
        return None
    converted = _try_literal(value)
    if converted is not _NOT_A_LITERAL and not isinstance(converted, bytes):
        return converted
    if value.startswith("(") and value.endswith(")"):
        return _convert_sequence(value, tuple)
    if value.startswith("[") and value.endswith("]"):
        return _convert_sequence(value, list)
    if value.startswith("{") and value.endswith("}"):
        return _convert_mapping(value)
    return _convert_scalar(value)


def _convert_sequence(value: str, factory: Callable[[Any], Any]) -> Any:
    """Convert a legacy ``(a,b)``/``[a,b]`` value using a factory.

    Args:
        value: delimited value without the surrounding brackets.
        factory: callable building the sequence, e.g. ``tuple`` or ``list``.

    Returns:
        The sequence with each element converted.
    """
    return factory(_convert_value(v) for v in value[1:-1].split(","))


def _convert_mapping(value: str) -> Dict[str, Any]:
    """Convert a legacy ``{a,A,b,B}`` value into a key/value dict.

    Args:
        value: braced value without the surrounding braces.

    Returns:
        Dictionary mapping alternating key/value pairs.
    """
    items = [item.strip() for item in value[1:-1].split(",")]
    return {items[2 * i]: items[2 * i + 1] for i in range(len(items) // 2)}


def _convert_scalar(value: str) -> Any:
    """Convert a legacy scalar, falling back to the original string.

    Args:
        value: string value which is not a Python literal or collection.

    Returns:
        The value as an int or float, or the original string.
    """
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _split_property(item: str) -> Tuple[str, Optional[str]]:
    """Split a property string into its name and value parts.

    The ``=`` character separates the property name from its value, which
    is written in Python literal syntax (e.g. ``"int.property=22"``).

    Args:
        item: property string to split.

    Returns:
        Tuple of (name, value); value is None for a blank value.

    Raises:
        ValueError: If the legacy ``:`` separator is used.
    """
    name, _, value = item.strip().partition("=")
    name = name.strip()
    value = value.strip()
    if ":" in name:
        raise ValueError(
            f"Plot property '{item}' uses the legacy ':' separator; "
            "use '=' instead (e.g. 'xaxis.label=Sample size')."
        )
    return name, value or None


def parse_properties(
    properties: Optional[Union[str, List[str]]],
) -> Dict[str, Any]:
    """Parse chart property strings into a typed dictionary.

    Each property is a string of the form ``<name>=<value>`` (e.g.
    ``"int.property=22"``). Values are parsed as Python literals so
    ``"0.05"`` becomes a float, ``"[1, 2]"`` a list, ``"{'a': 1}"`` a
    dict and ``"True"`` a boolean.

    Args:
        properties: list of property strings, a single string, or None.

    Returns:
        Dictionary of parsed property names to typed values.

    Raises:
        ValueError: If a property string is malformed.
    """
    parsed: Dict[str, Any] = {}
    if properties is None:
        return parsed
    if isinstance(properties, str):
        properties = [properties]
    for item in properties:
        name, value = _split_property(item)
        if not name:
            raise ValueError(f"Malformed plot property: '{item}'")
        parsed[name] = _convert_value(value)
    return parsed
