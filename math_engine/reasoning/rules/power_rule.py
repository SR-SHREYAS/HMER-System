"""Rule that applies the power rule of differentiation.

:class:`PowerRule` implements the power rule of differentiation:

.. math::

    \\frac{d}{dx} x^n = n \\cdot x^{n-1}

It reads the expression and variable from the structured metadata produced by
:class:`ExtractDerivativeStructureRule` and only applies when the expression is
exactly the differentiation variable raised to a power. The base of the power
must be exactly the variable, so forms like ``(x+1)**n``, ``sin(x)``, products
and sums are not handled. The result is returned raw; nothing is simplified
beyond the rule application itself.
"""

from __future__ import annotations

from sympy import Integer, Pow, latex

from ...models import Step
from .base_rule import BaseRule, make_step
from .rule_exceptions import UnsupportedExpressionError


class PowerRule(BaseRule):
    """Evaluate ``d/dx (x**n) = n * x**(n-1)`` for a simple power of ``x``.

    Consumes the derivative structure metadata and, when the expression is
    exactly the variable or a power of it, returns the derivative result
    together with the power-rule step.
    """

    def can_apply(self, structure) -> bool:
        """Return whether the expression is a power of the differentiation variable.

        The expression is a power when the base is exactly the variable and the
        exponent is a constant (independent of the variable), or when the
        expression is simply the variable itself (implicit exponent one).

        Parameters
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        bool
            ``True`` when the expression is exactly ``variable**n`` with a
            constant exponent, or the variable itself.
        """
        try:
            expression = structure["expression"]
            variable = structure["variable"]
        except (KeyError, TypeError):
            return False
        return PowerRule._power_of(expression, variable) is not None

    def apply(self, structure) -> tuple[object, Step]:
        """Return the power-rule derivative result.

        Parameters
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        tuple[object, Step]
            ``(n * x**(n-1), step)`` for a supported power. The step is titled
            "Apply the power rule" and carries kind ``power_rule``.

        Raises
        ------
        UnsupportedExpressionError
            If the expression is not a power of the variable.
        """
        self._ensure_applicable(structure)
        expression = structure["expression"]
        variable = structure["variable"]

        exponent = PowerRule._power_of(expression, variable)
        if exponent is None:
            raise UnsupportedExpressionError(
                "PowerRule expects the expression to be a power of the "
                "differentiation variable."
            )

        result = exponent * variable ** (exponent - 1)

        # Educational content: show the power rule formula, substitution, and evaluation
        if exponent == 1:
            formula = "\\frac{d}{dx} x = 1"
            substitution = f"\\frac{{d}}{{d{latex(variable)}}} {latex(variable)} = 1"
        else:
            formula = f"\\frac{{d}}{{dx}} x^{{{latex(exponent)}}} = {latex(exponent)} \\cdot x^{{{latex(exponent)} - 1}}"
            substitution = f"\\frac{{d}}{{d{latex(variable)}}} {latex(expression)} = {latex(exponent)} \\cdot {latex(variable)}^{{{latex(exponent)} - 1}}"

        evaluation = f"= {latex(result)}"

        step = make_step(
            "Apply the power rule",
            f"For {latex(variable)}^{{{latex(exponent)}}}, the power rule gives: "
            f"d/dx(x^n) = n*x^(n-1). Here n = {latex(exponent)}, so the derivative is "
            f"{latex(exponent)} * {latex(variable)}^{{{latex(exponent - 1)}}} = {latex(result)}.",
            "\\begin{aligned}\n"
            f"{formula} \\\\\n"
            f"{substitution} \\\\\n"
            f"{evaluation}\n"
            "\\end{aligned}",
            "power_rule",
        )
        step.metadata["base"] = variable
        step.metadata["exponent"] = exponent
        step.metadata["result"] = result
        return result, step

    @staticmethod
    def _power_of(expression, variable):
        """Return the exponent when ``expression`` is a power of ``variable``.

        Returns the exponent ``n`` when the expression is exactly
        ``variable**n`` with ``n`` a constant exponent, ``1`` when it is the
        variable itself, and ``None`` when the expression is not a power of the
        variable or the exponent depends on the variable (e.g. ``x**x``).
        """
        if expression == variable:
            return Integer(1)
        if (
            isinstance(expression, Pow)
            and expression.base == variable
            and not expression.exp.has(variable)
        ):
            return expression.exp
        return None


__all__ = ["PowerRule"]