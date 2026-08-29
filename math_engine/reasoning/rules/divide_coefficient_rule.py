"""Rule that simplifies the coefficient of the variable term.

:class:`DivideCoefficientRule` implements the second transformation applied
while solving a linear equation: both sides are divided by the coefficient of
the variable, leaving the variable alone on the left-hand side. It owns exactly
that single responsibility.
"""

from __future__ import annotations

from sympy import Eq, Equality, latex, simplify

from ...models import Step
from .base_rule import BaseRule, linear_components, make_step


class DivideCoefficientRule(BaseRule):
    """Divide both sides by the coefficient to solve for the variable."""

    def can_apply(self, expression: Equality) -> bool:
        """Return whether the variable still has a coefficient not equal to 1.

        Once the variable is alone on the left (coefficient ``1``) the rule no
        longer applies.
        """
        _, coefficient, _ = linear_components(expression)
        return coefficient != 1

    def apply(self, expression: Equality) -> tuple[Equality, Step]:
        """Divide both sides by the coefficient and return the new equation.

        Returns
        -------
        tuple[Equality, Step]
            The equation with the variable alone on the left, and the reasoning
            step that explains the transformation.
        """
        self._ensure_applicable(expression)
        symbol, coefficient, constant = linear_components(expression)
        rhs = simplify(-constant)
        value = simplify(rhs / coefficient)
        updated = Eq(symbol, value)
        step = make_step(
            "Divide by the coefficient to solve for the variable",
            f"Divide both sides by the coefficient {coefficient} to isolate "
            "the variable.",
            self._format_divide_latex(expression, updated, coefficient, rhs),
            "divide",
        )
        return updated, step

    def _format_divide_latex(self, original, updated, coefficient, rhs):
        """Format the division step showing the division on both sides."""
        return (
            "\\begin{aligned}\n"
            f"{latex(original)} \\\\\n"
            f"\\div {latex(coefficient)} \\\\\n"
            f"{latex(updated)}\n"
            "\\end{aligned}"
        )