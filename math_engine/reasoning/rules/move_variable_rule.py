"""Rule that collects variable terms onto the left-hand side.

:class:`MoveVariableRule` implements the transformation that broadens the
engine from equations with a single variable side to equations where the
variable appears on both sides: every variable term on the right-hand side is
moved to the left, applying the opposite operation to both sides. Like-term
combining happens as part of SymPy's canonical form, so the resulting step
shows the collected equation directly.

The rule owns exactly one responsibility and is never used as a substitute for
the constant-moving or coefficient-clearing rules.
"""

from __future__ import annotations

from sympy import Eq, Equality, Poly, latex, simplify

from ...models import Step
from .base_rule import BaseRule, linear_components, make_step
from .rule_exceptions import RuleNotApplicableError


class MoveVariableRule(BaseRule):
    """Move the variable terms of the right-hand side to the left-hand side."""

    def can_apply(self, expression: Equality) -> bool:
        """Return whether the right-hand side still holds variable terms.

        The rule applies only when the variable is present on the right-hand
        side of the equality.
        """
        symbol, _, _ = linear_components(expression)
        return expression.rhs.has(symbol)

    def apply(self, expression: Equality) -> tuple[Equality, Step]:
        """Move the right-hand variable term to the left and return the result.

        Returns
        -------
        tuple[Equality, Step]
            The equation after the variable term has been moved, and the
            reasoning step that explains the transformation.
        """
        self._ensure_applicable(expression)
        symbol, _, _ = linear_components(expression)

        rhs_coefficient = Poly(expression.rhs, symbol).coeff_monomial(symbol)
        if rhs_coefficient == 0:
            raise RuleNotApplicableError(
                "MoveVariableRule found no variable term to move on the "
                "right-hand side."
            )
        rhs_term = rhs_coefficient * symbol

        new_lhs = simplify(expression.lhs - rhs_term)
        new_rhs = simplify(expression.rhs - rhs_term)
        updated = Eq(new_lhs, new_rhs)
        
        # Format the operation nicely
        if rhs_coefficient < 0:
            operation_desc = f"Add {latex(-rhs_term)} to both sides"
            operation_latex = f"+ {latex(-rhs_term)}"
        else:
            operation_desc = f"Subtract {latex(rhs_term)} from both sides"
            operation_latex = f"- {latex(rhs_term)}"
        
        step = make_step(
            "Move variable terms to one side",
            f"{operation_desc} to collect variable terms on the left-hand side.",
            self._format_move_variable_latex(expression, updated, operation_latex),
            "move_variable",
        )
        return updated, step

    def _format_move_variable_latex(self, original, updated, operation_latex):
        """Format the variable moving step showing the operation on both sides."""
        return (
            "\\begin{aligned}\n"
            f"{latex(original)} \\\\\n"
            f"{operation_latex} \\\\\n"
            f"{latex(updated)}\n"
            "\\end{aligned}"
        )