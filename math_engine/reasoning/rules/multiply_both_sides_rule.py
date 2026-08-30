"""Rule that multiplies both sides of an equation by the least common denominator.

:class:`MultiplyBothSidesRule` handles linear equations that contain fractions
(e.g. ``x/2 + 5 = 10`` or ``(x+1)/3 = 4``). It detects the equation's
denominators, computes the least common denominator (LCD) using SymPy, and
multiplies both sides by that value, leaving a fraction-free equation that the
remaining rules solve. The rule uses SymPy's symbolic arithmetic and performs
no manual distribution or cancellation.
"""

from __future__ import annotations

from functools import reduce

from sympy import Eq, lcm, latex, simplify, sympify

from ...models import Step
from .base_rule import BaseRule, _single_symbol, denominators, make_step


class MultiplyBothSidesRule(BaseRule):
    """Multiply both sides by the least common denominator of the fractions."""

    def can_apply(self, expression) -> bool:
        """Return whether the equation contains clearable denominators.

        The rule applies whenever the equation holds at least one fraction and
        the variable is not yet isolated. Once the variable stands alone on the
        left, the equation is solved and a remaining fraction is the answer —
        clearing it would un-solve the equation and cause the engine to loop.
        """
        if not denominators(expression):
            return False
        symbol = _single_symbol(expression)
        return simplify(expression.lhs) != symbol

    def apply(self, expression) -> tuple:
        """Multiply both sides by the LCD and return the new equation.

        Returns
        -------
        tuple
            The fraction-free equation, and the single reasoning step that
            explains the transformation.
        """
        self._ensure_applicable(expression)
        denoms = sorted(denominators(expression))
        lcd = reduce(lcm, [sympify(d) for d in denoms], sympify(1))

        new_lhs = simplify(expression.lhs * lcd)
        new_rhs = simplify(expression.rhs * lcd)
        updated = Eq(new_lhs, new_rhs)
        step = make_step(
            "Multiply both sides to clear fractions",
            f"Multiply both sides by the least common denominator ({lcd}) "
            "to eliminate fractions.",
            self._format_multiplication_latex(expression, updated, lcd),
            "multiply_both_sides",
        )
        return updated, step

    def _format_multiplication_latex(self, original, updated, lcd):
        """Format the multiplication step showing the LCD applied to both sides."""
        return (
            "\\begin{aligned}\n"
            f"{latex(original)} \\\\\n"
            f"\\times {latex(lcd)} \\\\\n"
            f"{latex(updated)}\n"
            "\\end{aligned}"
        )