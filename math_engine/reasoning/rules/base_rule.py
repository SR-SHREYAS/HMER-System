"""Abstract base class and shared helpers for mathematical rules.

A rule owns exactly one mathematical transformation. The base class fixes the
contract every concrete rule follows: given the current expression, it can be
asked whether the transformation applies (:meth:`BaseRule.can_apply`) and, if
so, asked to produce the transformed expression together with the reasoning
step that explains it (:meth:`BaseRule.apply`).

The module also exposes the small, shared decomposition helpers that both
initial rules rely on. Centralising them here keeps the linear-equation
arithmetic in one place so no rule duplicates mathematical logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from sympy import Poly, Symbol

from ...models import Step
from .rule_exceptions import (
    RuleNotApplicableError,
    UnsupportedExpressionError,
)


class BaseRule(ABC):
    """A reusable mathematical transformation.

    Subclasses implement two operations. :meth:`can_apply` inspects the
    current expression and reports whether this rule's transformation can be
    performed. :meth:`apply` performs the transformation and returns a tuple of
    the updated expression and the :class:`Step` explaining it.

    A transformation is always validated before execution; calling
    :meth:`apply` on an expression the rule cannot handle raises
    :class:`RuleNotApplicableError`.
    """

    @abstractmethod
    def can_apply(self, expression) -> bool:
        """Return whether the rule applies to ``expression``."""
        ...

    @abstractmethod
    def apply(self) -> tuple:
        """Apply the rule and return ``(updated_expression, Step)``."""
        ...

    def _ensure_applicable(self, expression) -> None:
        """Raise if this rule cannot be applied to ``expression``."""
        if not self.can_apply(expression):
            raise RuleNotApplicableError(
                f"The rule {type(self).__name__} cannot be applied to "
                f"{expression!r}."
            )


def _single_symbol(expression) -> Symbol:
    """Return the only free symbol of an expression.

    Raises
    ------
    UnsupportedExpressionError
        If the expression does not contain exactly one free symbol.
    """
    symbols = expression.free_symbols
    if len(symbols) != 1:
        raise UnsupportedExpressionError(
            "Rules only support a single variable; "
            f"found {len(symbols)} free symbols."
        )
    return next(iter(symbols))


def linear_components(expression) -> tuple[Symbol, object, object]:
    """Decompose a linear equality into ``(symbol, coefficient, constant)``.

    The expression is read as ``coefficient * symbol + constant`` where the
    constant and coefficient respect ``lhs - rhs``. This is the single source
    of the decomposition arithmetic shared by the initial rules.

    Parameters
    ----------
    expression :
        The linear equality to decompose.

    Returns
    -------
    tuple[Symbol, object, object]
        The variable, its coefficient and the remaining constant.

    Raises
    ------
    UnsupportedExpressionError
        If the expression is not a single-variable linear equation with a
        nonzero variable coefficient.
    """
    symbol = _single_symbol(expression)

    polynomial = Poly(expression.lhs - expression.rhs, symbol)
    if polynomial.is_zero or polynomial.degree() > 1:
        raise UnsupportedExpressionError(
            "Rules only support linear equations; "
            f"got polynomial of degree {polynomial.degree()}."
        )
    coefficient = polynomial.coeff_monomial(symbol)
    constant = polynomial.coeff_monomial(1)
    if coefficient == 0:
        raise UnsupportedExpressionError(
            "Rules only support equations with a nonzero variable coefficient."
        )
    return symbol, coefficient, constant


def make_step(
    title: str, description: str, step_latex: str, kind: str
) -> Step:
    """Build a reasoning step with explanatory metadata."""
    return Step(
        title=title,
        description=description,
        latex=step_latex,
        metadata={"kind": kind},
    )


__all__ = [
    "BaseRule",
    "_single_symbol",
    "linear_components",
    "make_step",
]