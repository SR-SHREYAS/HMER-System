"""Task type classification for the math engine.

Describes the kind of mathematical problem a parsed expression represents.
Future modules use this classification to route work, but no routing logic
lives in this module.
"""

from __future__ import annotations

from enum import Enum


class TaskType(Enum):
    """The category of a mathematical expression.

    Values are lowercase strings so the classification survives serialization
    to JSON or other text-based formats.
    """

    UNKNOWN = "unknown"
    """The expression's task type could not be determined."""

    EQUATION = "equation"
    """An expression stating an equality between two sides."""

    QUADRATIC_EQUATION = "quadratic_equation"
    """A quadratic (second-degree) equation in a single variable."""

    DERIVATIVE = "derivative"
    """An expression representing a derivative of a function."""

    INTEGRAL = "integral"
    """An expression representing an integral of a function."""

    LIMIT = "limit"
    """An expression representing the limit of a function."""

    MATRIX = "matrix"
    """A matrix expression."""

    SIMPLIFY = "simplify"
    """A request to simplify an expression."""

    EXPAND = "expand"
    """A request to expand an expression."""

    FACTOR = "factor"
    """A request to factor an expression."""

    SERIES = "series"
    """An expression representing a series expansion or summation."""