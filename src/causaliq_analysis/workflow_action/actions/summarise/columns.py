"""Column specifications for the summarise action.

A summarise table is an ordered list of columns: the grouping dimensions
first, in matrix order, then one column per ``metric`` specification. A
metric column is either a base column, computed from the metric values of
one or all input caches, or a derived column, computed by a formula from
the columns that precede it.

Metric specifications extend the shared ``<field>.<stat>`` grammar with an
optional one-based source index (``f1.mean[2]``) and a bare
``<field>[n]`` form, which reports the single distinct value of a field.
An ``argmax`` column may also select one element of a list-valued
dimension with a trailing ``{n}`` (``f1.argmax.fusion_weights{1}``),
indexed from one like the source index.
A specification holding an operator or a function call is a derived column
and is parsed by ``formula``.

A specification may also declare an alias with a trailing ``as <name>``.
Aliases name the column in later formulas and provide its default label,
so a formula never refers to a column position.
"""

import re
from dataclasses import dataclass
from typing import Any, FrozenSet, List, Optional, Sequence, Set, Tuple

from causaliq_analysis.validation import SUPPORTED_STATS

from .formula import FUNCTIONS, _validate_formula

__all__ = [
    "ACTION_STATS",
    "ColumnSpec",
    "_normalise_list",
    "_normalise_optional_list",
    "_parse_column_spec",
    "_parse_column_specs",
    "_table_labels",
    "_unique_fields",
]

# Statistics available to the summarise action, in addition to the shared
# statistics understood by the CLI. 'unique' reports the single distinct
# value of a field and rejects a field holding conflicting values.
ACTION_STATS: FrozenSet[str] = SUPPORTED_STATS | {"unique"}

_SOURCE_PATTERN = re.compile(r"^(?P<body>.+?)\[(?P<index>\d+)\]$")

_ALIAS_PATTERN = re.compile(r"^(?P<body>.+?)\s+as\s+(?P<alias>[A-Za-z_]\w*)$")

_ELEMENT_PATTERN = re.compile(r"^(?P<body>.+?)\{(?P<index>\d+)\}$")

# Characters that mark a specification as a derived-column expression
_FORMULA_CHARS = ("+", "-", "*", "/", "(")


@dataclass(frozen=True)
class ColumnSpec:
    """One column of a summarise table.

    Attributes:
        text: Specification text, without any alias.
        source: One-based index of the input cache supplying the values,
            or None when every input cache contributes.
        field: Metric field name of a base column.
        stat: Statistic name of a base column.
        dimension: Matrix dimension reported by an ``argmax`` column.
        element: One-based element of a list-valued ``argmax`` dimension
            to report, or None to report the whole value.
        formula: Derived-column expression, or None for a base column.
        alias: Short name the column declares for use in later formulas
            and as its default label, or None.

    """

    text: str
    source: Optional[int] = None
    field: Optional[str] = None
    stat: Optional[str] = None
    dimension: Optional[str] = None
    element: Optional[int] = None
    formula: Optional[str] = None
    alias: Optional[str] = None

    @property
    def is_derived(self) -> bool:
        """Return True when the column is computed from earlier columns."""
        return self.formula is not None

    @property
    def key(self) -> str:
        """Return the name that identifies the column in the table."""
        return self.alias or self.text


def _parse_column_specs(specs: Sequence[str]) -> List[ColumnSpec]:
    """Parse metric specifications into column specifications.

    Specifications are parsed in table order so that a formula is
    validated against the aliases of the columns that precede it.

    Args:
        specs: Metric specifications, or derived-column expressions.

    Returns:
        Column specifications in table order.

    Raises:
        ValueError: If a specification is invalid, an alias is reserved or
            repeated, or a formula references an unavailable alias.

    """
    parsed: List[ColumnSpec] = []
    aliases: Set[str] = set()
    keys: Set[str] = set()
    for spec in specs:
        column = _parse_column_spec(spec)
        _require_unique_key(column, keys)
        if column.is_derived:
            _validate_formula(column.formula or "", aliases)
        parsed.append(column)
        keys.add(column.key)
        if column.alias:
            aliases.add(column.alias)
    return parsed


def _require_unique_key(column: ColumnSpec, keys: Set[str]) -> None:
    """Require a column's alias or text to be unique in the table.

    Args:
        column: Parsed column specification.
        keys: Keys of the preceding columns.

    Raises:
        ValueError: If the alias shadows a formula function, or the key
            repeats an earlier column's key.

    """
    if column.alias is not None and column.alias in FUNCTIONS:
        raise ValueError(
            f"Alias '{column.alias}' is a formula function name; choose "
            "another alias"
        )
    if column.key in keys:
        raise ValueError(
            f"Column '{column.key}' is declared twice; give one of them a "
            "distinct alias"
        )


def _parse_column_spec(spec: str) -> ColumnSpec:
    """Parse one metric specification or derived-column expression.

    Args:
        spec: Metric specification (e.g. 'f1.mean[2] as bnsl') or formula.

    Returns:
        Parsed column specification.

    Raises:
        ValueError: If the specification is invalid.

    """
    body, alias = _split_alias(spec)
    if _is_formula(body):
        _validate_formula(body)
        return ColumnSpec(text=body, formula=body, alias=alias)
    plain, source = _split_source(body)
    plain, element = _split_element(plain, body)
    field, stat, dimension = _split_stat(plain, body, source is not None)
    _require_argmax_element(element, stat, body, dimension)
    return ColumnSpec(
        text=body,
        source=source,
        field=field,
        stat=stat,
        dimension=dimension,
        element=element,
        alias=alias,
    )


def _is_formula(body: str) -> bool:
    """Return True when a specification is a derived-column expression.

    An entry is a formula when it holds an operator or a function call, so
    a metric specification (which is a single dotted token, optionally with
    a source index) is never mistaken for one.

    Args:
        body: Specification without its alias.

    Returns:
        True for a derived-column expression.

    """
    return any(character in body for character in _FORMULA_CHARS)


def _split_alias(spec: str) -> Tuple[str, Optional[str]]:
    """Split a trailing ``as <alias>`` from a specification.

    Args:
        spec: Specification to split.

    Returns:
        Tuple of (specification without the alias, alias or None).

    """
    match = _ALIAS_PATTERN.match(spec)
    if match is None:
        return spec, None
    return match.group("body"), match.group("alias")


def _split_source(spec: str) -> Tuple[str, Optional[int]]:
    """Split a trailing ``[n]`` source index from a specification.

    Args:
        spec: Specification to split.

    Returns:
        Tuple of (specification without the index, one-based index or
        None when the specification names no source).

    Raises:
        ValueError: If the index is not positive.

    """
    match = _SOURCE_PATTERN.match(spec)
    if match is None:
        return spec, None
    index = int(match.group("index"))
    if index < 1:
        raise ValueError(
            f"Invalid metric spec '{spec}': the source index is one-based"
        )
    return match.group("body"), index


def _split_element(
    spec: str,
    full: str,
) -> Tuple[str, Optional[int]]:
    """Split a trailing ``{n}`` element index from a specification.

    The element index selects one element of a list-valued matrix
    dimension reported by an ``argmax`` column, so it is peeled off before
    the field, statistic and dimension are split.

    Args:
        spec: Specification without its source index.
        full: Full specification, used in error messages.

    Returns:
        Tuple of (specification without the element index, one-based
        element index or None when the specification names no element).

    Raises:
        ValueError: If the element index is not positive.

    """
    match = _ELEMENT_PATTERN.match(spec)
    if match is None:
        return spec, None
    index = int(match.group("index"))
    if index < 1:
        raise ValueError(
            f"Invalid metric spec '{full}': the element index is one-based"
        )
    return match.group("body"), index


def _require_argmax_element(
    element: Optional[int],
    stat: str,
    spec: str,
    dimension: Optional[str],
) -> None:
    """Require an element selector to belong to a clean ``argmax`` column.

    Args:
        element: Parsed one-based element index, or None.
        stat: Statistic of the column.
        spec: Full specification, used in error messages.
        dimension: Matrix dimension reported by the column, or None.

    Raises:
        ValueError: If an element index is used outside an ``argmax``
            column, or a bracket survives inside the dimension name.

    """
    if _has_bracket(dimension):
        raise ValueError(
            f"Invalid metric spec '{spec}': write the element before the "
            "source index as "
            "'<field>.argmax.<dimension>{<element>}[<source>]'"
        )
    if element is not None and stat != "argmax":
        raise ValueError(
            f"Invalid metric spec '{spec}': an element index is only "
            "valid for an argmax column (e.g. "
            "'f1.argmax.fusion_weights{1}')"
        )


def _has_bracket(dimension: Optional[str]) -> bool:
    """Return True when a dimension name still holds a bracket character.

    Args:
        dimension: Matrix dimension name, or None.

    Returns:
        True when the dimension holds ``[``, ``]``, ``{`` or ``}``.

    """
    if dimension is None:
        return False
    return any(character in dimension for character in "[]{}")


def _split_stat(
    body: str,
    spec: str,
    has_source: bool,
) -> Tuple[str, str, Optional[str]]:
    """Split a field, statistic and argmax dimension from a specification.

    Args:
        body: Specification without its source and element indexes.
        spec: Full specification, used in error messages.
        has_source: Whether the specification named a source cache.

    Returns:
        Tuple of (field, statistic, dimension); dimension is None unless
        the statistic is argmax.

    Raises:
        ValueError: If the specification is invalid.

    """
    parts = body.rsplit(".", 2)
    if len(parts) == 3 and parts[1] == "argmax" and parts[0] and parts[2]:
        return parts[0], parts[1], parts[2]
    if has_source and "." not in body:
        return body, "unique", None
    return _split_plain_stat(body, spec)


def _split_plain_stat(
    body: str,
    spec: str,
) -> Tuple[str, str, Optional[str]]:
    """Split a ``<field>.<stat>`` specification.

    Args:
        body: Specification without its source index.
        spec: Full specification, used in error messages.

    Returns:
        Tuple of (field, statistic, None).

    Raises:
        ValueError: If the specification is invalid.

    """
    if "," in body:
        raise ValueError(
            f"Invalid metric spec '{spec}': contains comma. "
            "Use YAML list syntax: metric: [f1.mean, shd.sd]"
        )
    if "." not in body:
        raise ValueError(
            f"Invalid metric spec '{spec}': must be <field>.<stat>, "
            "<field>[<source>] or a formula"
        )
    field, stat = body.rsplit(".", 1)
    if stat not in ACTION_STATS:
        raise ValueError(
            f"Unknown statistic '{stat}' in '{spec}'. "
            f"Supported: {', '.join(sorted(ACTION_STATS))}"
        )
    return field, stat, None


def _unique_fields(specs: Sequence[ColumnSpec]) -> List[str]:
    """Return the metric fields referenced by the base columns.

    Args:
        specs: Column specifications in table order.

    Returns:
        Field names in first-referenced order, without duplicates.

    """
    return list(dict.fromkeys(spec.field for spec in specs if spec.field))


def _normalise_list(value: Any) -> List[str]:
    """Normalise a list-valued parameter to a list of strings.

    Args:
        value: Parameter value: None, a single string or a list.

    Returns:
        List of strings, empty when the parameter is absent.

    Raises:
        ValueError: If the value is neither a string nor a list.

    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    raise ValueError(f"expected a string or list, got {type(value).__name__}")


def _normalise_optional_list(value: Any) -> List[Optional[str]]:
    """Normalise a list-valued parameter, preserving null entries.

    A null entry is retained for parameters in which it carries meaning,
    such as a ``format`` entry that hides its column from the presentation
    output. Every other entry is converted to text.

    Args:
        value: Parameter value: None, a single string or a list.

    Returns:
        List of strings and nulls, empty when the parameter is absent.

    Raises:
        ValueError: If the value is neither a string nor a list.

    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [None if item is None else str(item) for item in value]
    raise ValueError(f"expected a string or list, got {type(value).__name__}")


def _table_labels(
    dimensions: Sequence[str],
    specs: Sequence[ColumnSpec],
    headers: Sequence[str],
) -> List[str]:
    """Return the column labels of the table.

    Args:
        dimensions: Grouping dimension names, in matrix order.
        specs: Column specifications in table order.
        headers: Declared column labels, empty when the defaults are used.

    Returns:
        Column labels: the declared headers, or the dimension names
        followed by each column's alias or specification text.

    Raises:
        ValueError: If the headers do not match the table's column count.

    """
    keys = [spec.key for spec in specs]
    if not headers:
        return list(dimensions) + keys
    expected = len(dimensions) + len(keys)
    if len(headers) != expected:
        raise ValueError(
            f"'headers' must have {expected} entries (one per table "
            f"column), got {len(headers)}"
        )
    return list(headers)
