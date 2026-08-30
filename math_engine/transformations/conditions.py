"""Condition and domain restriction models.

This module provides the condition and domain restriction types used by
transformations to express mathematical constraints and domain restrictions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sympy import Basic, Symbol, Eq, Ne, Gt, Ge, Lt, Le

from .base import Condition, DomainRestriction


@dataclass(frozen=True, slots=True)
class Condition:
    """A mathematical condition or constraint.

    Conditions represent mathematical constraints that must hold for a
    transformation to be valid, or that describe domain restrictions on
    the solution set.

    Conditions are represented as symbolic expressions to preserve
    mathematical meaning and enable future symbolic reasoning.
    """

    expression: object  # sympy.Basic
    """The symbolic condition expression (e.g., x != 0, x >= 0)."""

    description: str = ""
    """Human-readable description of the condition."""

    def __str__(self) -> str:
        return self.description or str(self.expression)

    def __bool__(self) -> bool:
        return self.expression is not None


@dataclass(frozen=True, slots=True)
class DomainRestriction:
    """A domain restriction on the variable(s) in an expression."""

    variable: str
    """The variable name this restriction applies to."""

    condition: Condition
    """The condition describing the restriction."""

    description: str = ""
    """Human-readable description of the domain restriction."""


# Pre-defined common conditions


def non_zero(symbol: Symbol) -> "NonZeroCondition":
    """Condition that a symbol is non-zero."""
    return NonZeroCondition(symbol)


def non_negative(symbol: Symbol) -> "NonNegativeCondition":
    """Condition that a symbol is non-negative."""
    return NonNegativeCondition(symbol)


def positive(symbol: Symbol) -> "PositiveCondition":
    """Condition that a symbol is positive."""
    return PositiveCondition(symbol)


def equal(lhs, rhs) -> "EqualCondition":
    """Condition that two expressions are equal."""
    return EqualCondition(lhs, rhs)


def not_equal(lhs, rhs) -> "NotEqualCondition":
    """Condition that two expressions are not equal."""
    return NotEqualCondition(lhs, rhs)


def greater_than(lhs, rhs) -> "GreaterThanCondition":
    """Condition that lhs > rhs."""
    return GreaterThanCondition(lhs, rhs)


def greater_equal(lhs, rhs) -> "GreaterEqualCondition":
    """Condition that lhs >= rhs."""
    return GreaterEqualCondition(lhs, rhs)


def less_than(lhs, rhs) -> "LessThanCondition":
    """Condition that lhs < rhs."""
    return LessThanCondition(lhs, rhs)


def less_equal(lhs, rhs) -> "LessEqualCondition":
    """Condition that lhs <= rhs."""
    return LessEqualCondition(lhs, rhs)


# Concrete condition classes for specific common cases


@dataclass(frozen=True, slots=True)
class NonZeroCondition:
    """Condition that a symbol is non-zero."""

    symbol: Symbol

    @property
    def expression(self):
        from sympy import Ne
        return Ne(self.symbol, 0)

    @property
    def description(self) -> str:
        return f"{self.symbol} ≠ 0"


@dataclass(frozen=True, slots=True)
class NonNegativeCondition:
    """Condition that a symbol is non-negative (>= 0)."""

    symbol: Symbol

    @property
    def expression(self):
        from sympy import Ge
        return Ge(self.symbol, 0)

    @property
    def description(self) -> str:
        return f"{self.symbol} ≥ 0"


@dataclass(frozen=True, slots=True)
class PositiveCondition:
    """Condition that a symbol is positive (> 0)."""

    symbol: Symbol

    @property
    def expression(self):
        from sympy import Gt
        return Gt(self.symbol, 0)

    @property
    def description(self) -> str:
        return f"{self.symbol} > 0"


@dataclass(frozen=True, slots=True)
class EqualCondition:
    """Condition that two expressions are equal."""

    lhs: object
    rhs: object

    @property
    def expression(self):
        from sympy import Eq
        return Eq(self.lhs, self.rhs)

    @property
    def description(self) -> str:
        return f"{self.lhs} = {self.rhs}"


@dataclass(frozen=True, slots=True)
class NotEqualCondition:
    """Condition that two expressions are not equal."""

    lhs: object
    rhs: object

    @property
    def expression(self):
        from sympy import Ne
        return Ne(self.lhs, self.rhs)

    @property
    def description(self) -> str:
        return f"{self.lhs} ≠ {self.rhs}"


@dataclass(frozen=True, slots=True)
class GreaterThanCondition:
    """Condition that lhs > rhs."""

    lhs: object
    rhs: object

    @property
    def expression(self):
        from sympy import Gt
        return Gt(self.lhs, self.rhs)

    @property
    def description(self) -> str:
        return f"{self.lhs} > {self.rhs}"


@dataclass(frozen=True, slots=True)
class GreaterEqualCondition:
    """Condition that lhs >= rhs."""

    lhs: object
    rhs: object

    @property
    def expression(self):
        from sympy import Ge
        return Ge(self.lhs, self.rhs)

    @property
    def description(self) -> str:
        return f"{self.lhs} ≥ {self.rhs}"


@dataclass(frozen=True, slots=True)
class LessThanCondition:
    """Condition that lhs < rhs."""

    lhs: object
    rhs: object

    @property
    def expression(self):
        from sympy import Lt
        return Lt(self.lhs, self.rhs)

    @property
    def description(self) -> str:
        return f"{self.lhs} < {self.rhs}"


@dataclass(frozen=True, slots=True)
class LessEqualCondition:
    """Condition that lhs <= rhs."""

    lhs: object
    rhs: object

    @property
    def expression(self):
        from sympy import Le
        return Le(self.lhs, self.rhs)

    @property
    def description(self) -> str:
        return f"{self.lhs} ≤ {self.rhs}"


# Convenience functions for creating conditions


def condition_from_expression(expr: object, description: str = "") -> "Condition":
    """Create a Condition from a raw expression."""
    from .base import Condition
    return Condition(expression=expr, description=description)


def domain_restriction(variable: str, condition: Condition, description: str = "") -> "DomainRestriction":
    """Create a DomainRestriction."""
    return DomainRestriction(variable=variable, condition=condition, description=description)


__all__ = [
    "Condition",
    "DomainRestriction",
    "NonZeroCondition",
    "NonNegativeCondition",
    "PositiveCondition",
    "EqualCondition",
    "NotEqualCondition",
    "GreaterThanCondition",
    "GreaterEqualCondition",
    "LessThanCondition",
    "LessEqualCondition",
    "non_zero",
    "non_negative",
    "positive",
    "equal",
    "not_equal",
    "greater_than",
    "greater_equal",
    "less_than",
    "less_equal",
    "condition_from_expression",
    "domain_restriction",
]