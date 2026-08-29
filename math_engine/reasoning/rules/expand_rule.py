"""Rule that expands parentheses using symbolic expansion.

:class:`ExpandRule` handles linear equations that contain a single level of
parentheses (for example ``2(x + 3) = 10``). It relies on SymPy's own
:func:`expand` to distribute products over sums — the rule performs no manual
distribution arithmetic. Once the parentheses are removed the remaining rules
(``MoveVariableRule``, ``MoveConstantRule``, ``DivideCoefficientRule``) take
over, so the rule owns exactly one responsibility.
"""

from __future__ import annotations

from sympy import Add, Mul, expand, latex, preorder_traversal

from ...models import Step
from .base_rule import BaseRule, denominators, make_step


class ExpandRule(BaseRule):
    """Expand the parentheses of an equation to remove its brackets."""

    def can_apply(self, expression) -> bool:
        """Return whether the expression contains genuine parentheses.

        The rule applies when the expression holds a product of a coefficient
        and a parenthesised sum, e.g. ``2(x+3)``. It deliberately avoids
        treating rational coefficients (e.g. ``x/2``) or sums over a single
        denominator (e.g. ``(x+1)/3``) as expandable — those belong to the
        fraction-clearing rule.
        """
        return self._has_expandable_product(expression)

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
            "Expand the brackets",
            "Distribute the multiplier across each term inside the parentheses "
            "using the distributive law: a(b + c) = ab + ac.",
            self._format_expansion_latex(expression, expanded),
            "expand",
        )
        return expanded, step

    def _format_expansion_latex(self, original, expanded):
        """Format the expansion step showing the distributive law application."""
        return (
            "\\begin{aligned}\n"
            f"{latex(original)} \\\\\n"
            f"{latex(expanded)}\n"
            "\\end{aligned}"
        )

    def _has_expandable_product(self, expression) -> bool:
        """Return whether any subterm is a product containing a sum.

        A term ``Mul`` is considered expandable when it holds an ``Add`` (over
        one or more symbols) as a factor and does not carry a denominator
        (a rational factor with denominator greater than one).
        """
        for node in preorder_traversal(expression):
            if not isinstance(node, Mul):
                continue
            if not any(
                isinstance(factor, Add) and factor.free_symbols
                for factor in node.args
            ):
                continue
            if denominators(node):
                continue
            return True
        return False