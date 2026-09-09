"""Condition and domain restriction models.

This module provides the condition and domain restriction types used by
transformations to express mathematical constraints and domain restrictions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sympy import Basic, Symbol


@dataclass(frozen=True, slots=True)
class Condition:
    """A mathematical condition or constraint.

    Conditions represent mathematical constraints that must hold for a
    transformation to be valid, or that describe domain restrictions on
    the solution set.

    Conditions are represented as symbolic expressions to preserve
    mathematical meaning and enable future symbolic reasoning.
    """

    expression: Basic
    """The symbolic condition expression (e.g., x != 0, x >= 0)."""

    description: str = ""
    """Human-readable description of the condition."""

    def __str__(self) -> str:
        return self.description or str(self.expression)

    def __bool__(self) -> bool:
        """A condition is truthy if it has a non-empty expression."""
        return self.expression is not None


@dataclass(frozen=True, slots=True)
class DomainRestriction:
    """A domain restriction on the variable(s) in an expression.

    Domain restrictions specify the valid domain of variables for a
    transformation to be mathematically valid.
    """

    variable: str
    """The variable name this restriction applies to."""

    condition: Condition
    """The condition describing the restriction."""

    description: str = ""
    """Human-readable description of the domain restriction."""


def non_zero(symbol: Symbol) -> "Condition":
    """Condition that a symbol is non-zero."""
    from sympy import Ne
    return Condition(
        expression=Ne(symbol, 0),
        description=f"{symbol} ≠ 0",
    )


def non_negative(symbol: Symbol) -> "Condition":
    """Condition that a symbol is non-negative."""
    from sympy import Ge
    return Condition(
        expression=Ge(symbol, 0),
        description=f"{symbol} ≥ 0",
    )


def positive(symbol: Symbol) -> "Condition":
    """Condition that a symbol is positive."""
    from sympy import Gt
    return Condition(
        expression=Gt(symbol, 0),
        description=f"{symbol} > 0",
    )


__all__ = [
    "Condition",
    "DomainRestriction",
    "non_zero",
    "non_negative",
    "positive",
]