"""Rule that isolates the variable term of a linear equation.

:class:`MoveConstantRule` implements the first transformation a linear equation
goes through while being solved: the constant term is moved to the
right-hand side, leaving only the variable term on the left. It owns no other
responsibility.
"""

from __future__ import annotations

from sympy import Eq, Equality, latex, simplify

from ...models import Step
from .base_rule import BaseRule, linear_components, make_step


class MoveConstantRule(BaseRule):
    """Move the constant term of a linear equation to the right-hand side."""

    def can_apply(self, expression: Equality) -> bool:
        """Return whether the equation has a constant term on the left side.

        The rule applies only when the left side still holds a nonzero
        constant next to the variable term.
        """
        symbol, coefficient, _ = linear_components(expression)
        lhs_constant = simplify(expression.lhs - coefficient * symbol)
        return lhs_constant != 0

    def apply(self, expression: Equality) -> tuple[Equality, Step]:
        """Move the constant term to the right and return the new equation.

        Returns
        -------
        tuple[Equality, Step]
            The equation after the constant has been moved, and the reasoning
            step that explains the transformation.
        """
        self._ensure_applicable(expression)
        symbol, coefficient, constant = linear_components(expression)
        lhs_constant = simplify(expression.lhs - coefficient * symbol)
        rhs = simplify(-constant)
        updated = Eq(coefficient * symbol, rhs)
        step = make_step(
            "Isolate the variable term",
            f"Move the constant term {latex(lhs_constant)} to the right-hand "
            "side, applying the opposite operation to both sides.",
            latex(updated),
            "isolate",
        )
        return updated, step