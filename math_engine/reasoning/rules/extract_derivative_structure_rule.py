"""Rule that extracts the structure of a derivative expression.

:class:`ExtractDerivativeStructureRule` inspects a SymPy
:class:`~sympy.Derivative` object and extracts the parts that future
differentiation phases will need:

* the inner expression being differentiated (``Derivative.expr``),
* the variable(s) of differentiation (``Derivative.variables``),
* the order of differentiation.

The rule performs no mathematics: it never computes a derivative, never
simplifies, never modifies the expression, and does not aggressively flatten
its structure. It only reads the SymPy object and records what it found in the
reasoning-step metadata.
"""

from __future__ import annotations

from sympy import Derivative, latex

from ...models import Step
from .base_rule import BaseRule, make_step
from .rule_exceptions import UnsupportedExpressionError


class ExtractDerivativeStructureRule(BaseRule):
    """Extract the structure of a SymPy derivative.

    Reads the derivative's expression, variables and order from the SymPy
    object without performing any mathematics.
    """

    def can_apply(self, expression) -> bool:
        """Return whether the expression is a SymPy derivative.

        Parameters
        ----------
        expression :
            The expression to inspect.

        Returns
        -------
        bool
            ``True`` when the expression is a :class:`~sympy.Derivative`.
        """
        return isinstance(expression, Derivative)

    def apply(self, expression) -> tuple[Derivative, Step]:
        """Extract and expose the derivative structure in metadata.

        Parameters
        ----------
        expression :
            The SymPy derivative to inspect.

        Returns
        -------
        tuple[Derivative, Step]
            The unchanged ``Derivative`` object and a reasoning step whose
            metadata carries the extracted structure:
            ``metadata['expression']`` -- the sub-expression being
            differentiated; ``metadata['variables']`` -- the tuple of
            differentiation variables (repeated for higher order); and
            ``metadata['order']`` -- the total order of differentiation.

        Raises
        ------
        UnsupportedExpressionError
            If the expression is not a SymPy derivative.
        """
        self._ensure_applicable(expression)
        variables = tuple(expression.variables)
        order = len(variables)

        if variables and all(var == variables[0] for var in variables):
            variable = variables[0]
        else:
            variable = variables

        step = make_step(
            "Identify the function and variable of differentiation",
            f"Differentiate {latex(expression.expr)} with respect to {latex(variable)} (order {order}).",
            f"\\frac{{d^{order}}}{{d{latex(variable)}^{order}}} \\left({latex(expression.expr)}\\right)",
            "extract_derivative_structure",
        )
        step.metadata["expression"] = expression.expr
        step.metadata["variables"] = variables
        step.metadata["order"] = order
        step.metadata["variable"] = variable
        return expression, step


__all__ = ["ExtractDerivativeStructureRule"]