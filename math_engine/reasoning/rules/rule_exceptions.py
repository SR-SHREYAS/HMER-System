"""Exceptions for the mathematical rule engine.

The rule engine has its own small exception hierarchy rooted at
:class:`RuleError`. Concrete rules raise :class:`RuleNotApplicableError` when a
transformation is attempted on a state that does not match it, and
:class:`UnsupportedExpressionError` when a state is fundamentally outside a
rule's domain. The engine raises :class:`RuleEngineError` for failures that
belong to the execution loop itself.
"""

from __future__ import annotations


class RuleError(Exception):
    """Base class for every error raised by the rule layer."""


class RuleNotApplicableError(RuleError):
    """Raised when a rule cannot be applied to the current expression."""


class UnsupportedExpressionError(RuleError):
    """Raised when an expression is outside what a rule can reason about."""


class RuleEngineError(RuleError):
    """Raised when the rule engine fails to execute rules correctly."""