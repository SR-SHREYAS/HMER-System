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
            "Simplify the coefficient",
            "Divide both sides by the coefficient of the variable to leave "
            "the variable alone on the left.",
            latex(updated),
            "divide",
        )
        return updated, step