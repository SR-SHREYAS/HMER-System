"""Mathematical expression dispatcher.

Determines the :class:`TaskType` of a parsed expression by inspecting its
SymPy object type. This layer performs classification *only*: it never solves
mathematics, never modifies the SymPy expression, and never produces reasoning.

The single public function is :func:`dispatch`.
"""

from __future__ import annotations

from dataclasses import replace

from sympy import Basic, Derivative, Equality, Integral, Limit, MatrixBase

from ..models import Expression, TaskType
from .dispatcher_exceptions import InvalidExpressionError


def dispatch(expression: Expression) -> Expression:
    """Classify the task type of a parsed expression.

    Returns a new, immutably-populated :class:`Expression` whose ``task`` field
    is derived from the SymPy object type. The input expression is left
    unchanged.

    Parameters
    ----------
    expression : Expression
        A parsed expression, typically with an unclassified ``task``.

    Returns
    -------
    Expression
        A new expression carrying the classified :class:`TaskType`.

    Raises
    ------
    InvalidExpressionError
        If ``expression`` is not an :class:`Expression`.
    """
    _validate_input(expression)
    task = _classify(expression.sympy_expression)
    return replace(expression, task=task)


def _validate_input(expression: object) -> None:
    """Ensure dispatcher input is a model Expression.

    Raises
    ------
    InvalidExpressionError
        If ``expression`` is not an :class:`Expression`.
    """
    if not isinstance(expression, Expression):
        raise InvalidExpressionError(
            f"dispatch expects an Expression, got {type(expression).__name__}."
        )


def _classify(expr: Basic) -> TaskType:
    """Map a SymPy expression to its task type.

    Checks the concrete SymPy object type. Semantic tasks (expand, factor,
    simplify, series) are intentionally not classified here.

    Returns
    -------
    TaskType
        The classified task, or :attr:`TaskType.UNKNOWN` when unsure.
    """
    if _is_equation(expr):
        return TaskType.EQUATION
    if _is_matrix(expr):
        return TaskType.MATRIX
    if _is_derivative(expr):
        return TaskType.DERIVATIVE
    if _is_integral(expr):
        return TaskType.INTEGRAL
    if _is_limit(expr):
        return TaskType.LIMIT
    return TaskType.UNKNOWN


def _is_equation(expr: Basic) -> bool:
    """Return whether the expression is an equality relation."""
    return isinstance(expr, Equality)


def _is_matrix(expr: Basic) -> bool:
    """Return whether the expression is a matrix."""
    return isinstance(expr, MatrixBase)


def _is_derivative(expr: Basic) -> bool:
    """Return whether the expression is a derivative."""
    return isinstance(expr, Derivative)


def _is_integral(expr: Basic) -> bool:
    """Return whether the expression is an integral."""
    return isinstance(expr, Integral)


def _is_limit(expr: Basic) -> bool:
    """Return whether the expression is a limit."""
    return isinstance(expr, Limit)