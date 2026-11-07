"""Derived-column formulas for the summarise action.

A formula is an arithmetic expression over aliases of the columns that
precede it, written in Python syntax::

    "fusion - max(bnsl, llm)"

An expression may use the operators ``+``, ``-``, ``*`` and ``/``, unary
sign, parentheses, numeric literals and the functions ``min``, ``max``,
``abs`` and ``round``. A column is addressed by the alias it declares with
``as``, never by its position, so a numeric literal is always a number and
reordering the columns cannot change a formula's meaning.

Empty cells propagate as they do in a spreadsheet: arithmetic over a
missing value yields an empty cell, ``min`` and ``max`` ignore empty
values, and a division by zero yields an empty cell.
"""

import ast
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set

from causaliq_analysis.workflow_action.types import ActionExecutionError

__all__ = ["FUNCTIONS", "_evaluate_formula", "_validate_formula"]

_BINARY_OPS = (ast.Add, ast.Sub, ast.Mult, ast.Div)
_UNARY_OPS = (ast.USub, ast.UAdd)

# Functions accepted in a formula, with their minimum and maximum arity
_FUNCTION_ARITY: Dict[str, Sequence[Optional[int]]] = {
    "abs": (1, 1),
    "max": (1, None),
    "min": (1, None),
    "round": (1, 2),
}

# Function names, which a column alias may not shadow
FUNCTIONS = tuple(sorted(_FUNCTION_ARITY))


def _validate_formula(
    formula: str,
    aliases: Optional[Set[str]] = None,
) -> None:
    """Validate a formula's syntax, functions and column references.

    Args:
        formula: Formula expression written by the user.
        aliases: Aliases available to the formula, or None to validate the
            expression without resolving column names.

    Raises:
        ValueError: If the formula uses an unsupported construct, an
            unknown function or an unavailable alias.

    """
    _validate_node(_parse_formula(formula), aliases)


def _parse_formula(formula: str) -> ast.expr:
    """Parse a formula into an expression node.

    Args:
        formula: Formula expression written by the user.

    Returns:
        Root node of the parsed expression.

    Raises:
        ValueError: If the formula is not a valid expression.

    """
    try:
        return ast.parse(formula, mode="eval").body
    except SyntaxError as e:
        raise ValueError(f"Invalid formula '{formula}': {e.msg}") from e


def _validate_node(node: ast.expr, aliases: Optional[Set[str]]) -> None:
    """Validate one node of a formula expression tree.

    Args:
        node: Expression node to validate.
        aliases: Aliases available to the formula, if known.

    Raises:
        ValueError: If the node uses an unsupported construct.

    """
    if isinstance(node, ast.Constant):
        return _validate_constant(node)
    if isinstance(node, ast.Name):
        return _validate_name(node, aliases)
    if isinstance(node, ast.BinOp) and isinstance(node.op, _BINARY_OPS):
        return _validate_operands(node, aliases)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, _UNARY_OPS):
        return _validate_node(node.operand, aliases)
    if isinstance(node, ast.Call):
        return _validate_call(node, aliases)
    raise ValueError(f"Unsupported element in formula: {type(node).__name__}")


def _validate_constant(node: ast.Constant) -> None:
    """Validate a numeric literal.

    Args:
        node: Constant node to validate.

    Raises:
        ValueError: If the literal is not a number.

    """
    value = node.value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"Unsupported literal {value!r} in formula: use numbers, "
            "column aliases and functions only"
        )


def _validate_name(node: ast.Name, aliases: Optional[Set[str]]) -> None:
    """Validate a column alias reference.

    Args:
        node: Name node to validate.
        aliases: Aliases available to the formula, if known.

    Raises:
        ValueError: If the name is not an alias of an earlier column.

    """
    if aliases is None or node.id in aliases:
        return
    raise ValueError(
        f"Formula references '{node.id}', which is not an alias of an "
        f"earlier column. Declare that column with 'as {node.id}'."
    )


def _validate_operands(node: ast.BinOp, aliases: Optional[Set[str]]) -> None:
    """Validate both operands of a binary operation.

    Args:
        node: Binary-operation node.
        aliases: Aliases available to the formula, if known.

    """
    _validate_node(node.left, aliases)
    _validate_node(node.right, aliases)


def _validate_call(node: ast.Call, aliases: Optional[Set[str]]) -> None:
    """Validate a function call in a formula.

    Args:
        node: Call node to validate.
        aliases: Aliases available to the formula, if known.

    Raises:
        ValueError: If the function is unknown, is called with the wrong
            number of arguments, or takes an invalid digit count.

    """
    if not isinstance(node.func, ast.Name) or node.keywords:
        raise ValueError(
            "Formula calls must be simple functions taking positional "
            "arguments"
        )
    name = node.func.id
    if name not in _FUNCTION_ARITY:
        raise ValueError(
            f"Unknown formula function '{name}'. Supported: "
            f"{', '.join(FUNCTIONS)}"
        )
    _require_arity(name, len(node.args))
    for argument in node.args:
        _validate_node(argument, aliases)
    _require_round_digits(name, node.args)


def _require_arity(name: str, count: int) -> None:
    """Require a function call to pass an acceptable argument count.

    Args:
        name: Function name.
        count: Number of arguments passed.

    Raises:
        ValueError: If too few or too many arguments are passed.

    """
    minimum, maximum = _FUNCTION_ARITY[name]
    if count < (minimum or 0):
        raise ValueError(
            f"Formula function '{name}' needs at least {minimum} "
            "argument(s)"
        )
    if maximum is not None and count > maximum:
        raise ValueError(
            f"Formula function '{name}' takes at most {maximum} argument(s)"
        )


def _require_round_digits(name: str, arguments: Sequence[ast.expr]) -> None:
    """Require ``round`` to take a literal number of digits.

    Args:
        name: Function name.
        arguments: Argument nodes of the call.

    Raises:
        ValueError: If the digit count is not a non-negative integer
            literal.

    """
    if name != "round" or len(arguments) < 2:
        return
    digits = arguments[1]
    if isinstance(digits, ast.Constant) and isinstance(digits.value, int):
        if digits.value >= 0:
            return
    raise ValueError(
        "Formula function 'round' needs a non-negative whole number of "
        "digits, e.g. round(x, 3)"
    )


def _evaluate_formula(
    formula: str,
    values: Mapping[str, Any],
) -> Any:
    """Evaluate a formula against the values of the named columns.

    Args:
        formula: Formula expression written by the user.
        values: Computed values keyed by column alias.

    Returns:
        Computed value, or an empty string when a referenced column is
        empty or a division by zero occurs.

    Raises:
        ActionExecutionError: If the formula references an alias that has
            no value.

    """
    return _evaluate_node(_parse_formula(formula), values)


def _evaluate_node(node: ast.expr, values: Mapping[str, Any]) -> Any:
    """Evaluate one node of a formula expression tree.

    Args:
        node: Expression node to evaluate.
        values: Computed values keyed by column alias.

    Returns:
        Computed value of the node.

    """
    if isinstance(node, ast.Constant):
        assert isinstance(node.value, (int, float))  # Validated
        return float(node.value)
    if isinstance(node, ast.Name):
        return _name_value(node.id, values)
    if isinstance(node, ast.BinOp):
        return _binary_value(node, values)
    if isinstance(node, ast.UnaryOp):
        return _unary_value(node, values)
    assert isinstance(node, ast.Call)  # Guaranteed by _validate_formula
    return _call_value(node, values)


def _name_value(name: str, values: Mapping[str, Any]) -> Any:
    """Return the value of a column alias.

    Args:
        name: Column alias.
        values: Computed values keyed by column alias.

    Returns:
        Value of the column.

    Raises:
        ActionExecutionError: If the alias has no value.

    """
    if name not in values:
        raise ActionExecutionError(
            f"Formula references unknown column '{name}'"
        )
    return values[name]


def _binary_value(node: ast.BinOp, values: Mapping[str, Any]) -> Any:
    """Evaluate a binary arithmetic operation.

    Args:
        node: Binary-operation node.
        values: Computed values keyed by column alias.

    Returns:
        Computed value, or an empty string when an operand is empty.

    """
    left = _number_value(_evaluate_node(node.left, values))
    right = _number_value(_evaluate_node(node.right, values))
    if left is None or right is None:
        return ""
    return _apply_binary(node.op, left, right)


def _apply_binary(op: ast.operator, left: float, right: float) -> Any:
    """Apply an arithmetic operator to two numbers.

    Args:
        op: Operator node.
        left: Left operand.
        right: Right operand.

    Returns:
        Result of the operation, or an empty string for division by zero.

    """
    if isinstance(op, ast.Sub):
        return left - right
    if isinstance(op, ast.Mult):
        return left * right
    if isinstance(op, ast.Div):
        return "" if right == 0 else left / right
    return left + right


def _unary_value(node: ast.UnaryOp, values: Mapping[str, Any]) -> Any:
    """Evaluate a unary sign operation.

    Args:
        node: Unary-operation node.
        values: Computed values keyed by column alias.

    Returns:
        Computed value, or an empty string when the operand is empty.

    """
    value = _number_value(_evaluate_node(node.operand, values))
    if value is None:
        return ""
    return -value if isinstance(node.op, ast.USub) else value


def _call_value(node: ast.Call, values: Mapping[str, Any]) -> Any:
    """Evaluate a function call.

    Args:
        node: Call node to evaluate.
        values: Computed values keyed by column alias.

    Returns:
        Computed value of the call.

    """
    func = node.func
    assert isinstance(func, ast.Name)  # Guaranteed by _validate_call
    arguments = [_evaluate_node(argument, values) for argument in node.args]
    return _HANDLERS[func.id](arguments)


def _number_value(value: Any) -> Optional[float]:
    """Return the numeric value of a cell, or None when it is empty.

    Args:
        value: Cell value to convert.

    Returns:
        Numeric value, or None for an empty or non-numeric cell.

    """
    if value is None or isinstance(value, bool) or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _numeric_values(
    values: List[Any],
    ignore_empty: bool = False,
) -> Optional[List[float]]:
    """Convert call arguments to numbers.

    Args:
        values: Arguments of a formula function.
        ignore_empty: Whether empty arguments are skipped rather than
            propagating an empty result.

    Returns:
        Numeric arguments, or None when an argument is empty and empty
        arguments do not propagate.

    """
    numbers = [_number_value(value) for value in values]
    if ignore_empty:
        return [number for number in numbers if number is not None]
    if None in numbers:
        return None
    return [number for number in numbers if number is not None]


def _absolute(values: List[Any]) -> Any:
    """Return the absolute value of the first argument.

    Args:
        values: Arguments of the function.

    Returns:
        Absolute value, or an empty string when the argument is empty.

    """
    numbers = _numeric_values(values)
    return "" if not numbers else abs(numbers[0])


def _maximum(values: List[Any]) -> Any:
    """Return the largest argument, ignoring empty arguments.

    Args:
        values: Arguments of the function.

    Returns:
        Largest numeric argument, or an empty string when none is numeric.

    """
    numbers = _numeric_values(values, ignore_empty=True)
    return "" if not numbers else max(numbers)


def _minimum(values: List[Any]) -> Any:
    """Return the smallest argument, ignoring empty arguments.

    Args:
        values: Arguments of the function.

    Returns:
        Smallest numeric argument, or an empty string when none is
        numeric.

    """
    numbers = _numeric_values(values, ignore_empty=True)
    return "" if not numbers else min(numbers)


def _rounded(values: List[Any]) -> Any:
    """Return the first argument rounded to a number of digits.

    Args:
        values: Arguments of the function; the optional second argument is
            the number of digits, which validation requires to be a
            literal.

    Returns:
        Rounded value, or an empty string when the value is empty.

    """
    number = _number_value(values[0])
    if number is None:
        return ""
    digits = 0 if len(values) < 2 else int(_number_value(values[1]) or 0)
    return round(number, digits)


_HANDLERS: Dict[str, Callable[[List[Any]], Any]] = {
    "abs": _absolute,
    "max": _maximum,
    "min": _minimum,
    "round": _rounded,
}
