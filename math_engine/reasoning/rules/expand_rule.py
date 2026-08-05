"""Rule that expands parentheses using symbolic expansion.

:class:`ExpandRule` handles linear equations that contain a single level of
parentheses (for example ``2(x + 3) = 10``). It relies on SymPy's own
:func:`expand` to distribute products over sums — the rule performs no manual
distribution arithmetic. Once the parentheses are removed the remaining rules
(``MoveVariableRule``, ``MoveConstantRule``, ``DivideCoefficientRule``) take
over, so the rule owns exactly one responsibility.
"""

from __future__ import annotations

from sympy import expand, latex

from ...models import Step
from .base_rule import BaseRule, make_step


class ExpandRule(BaseRule):
    """Expand the parentheses of an equation to remove its brackets."""

    def can_apply(self, expression) -> bool:
        """Return whether the expression contains expandable parentheses.

        The rule applies whenever SymPy's symbolic expansion changes the
        equation, which happens exactly when a product of a coefficient and a
        parenthesised sum (or any other expandable term) is present.
        """
        return expand(expression) != expression

    def apply(self, expression) -> tuple:
        """Expand the equation and return the result together with a step.

        Returns
        -------
        tuple
            The fully expanded equation, and the reasoning step that explains
            the transformation.
        """
        self._ensure_applicable(expression)
        expanded = expand(expression)
        step = make_step(
            "Expand the parentheses",
            "Expand the parentheses using the distributive law to remove the "
            "brackets from the equation.",
            latex(expanded),
            "expand",
        )
        return expanded, step