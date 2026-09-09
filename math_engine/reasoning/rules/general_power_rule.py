"""Rule that applies the general power rule of differentiation.

:class:`GeneralPowerRule` implements the derivative of a power whose exponent
depends on the differentiation variable:

.. math::

    \\frac{d}{dx} f(x)^{g(x)} = f(x)^{g(x)} \\cdot \\left( \\ln f(x) \\cdot g'(x)
    + g(x) \\cdot \\frac{f'(x)}{f(x)} \\right)

This is the case the classical power rule (constant exponent) and the chain
rule (constant exponent over a composite base) explicitly leave out: forms like
``x**x``, ``(x + 1)**x`` or ``sin(x)**x``. The rule rewrites the power through
the identity ``f^g = exp(g * ln(f))`` and differentiates the exponent part
``g * ln(f)`` by routing it through the full rule pipeline the solver uses
(implicit, constant, power, sum, product, quotient, chain, trigonometric and
exp/log rules) -- nothing is differentiated by hand. The result
``f**g * (g * ln(f))'`` is returned raw: nothing is simplified. The rule only
applies when the exponent depends on the variable; otherwise it leaves the
expression unchanged.
"""

from __future__ import annotations

from sympy import Integer, Mul, Pow, exp, latex, log

from ...models import Step
from .base_rule import BaseRule, make_step
from .rule_exceptions import UnsupportedExpressionError


class GeneralPowerRule(BaseRule):
    """Evaluate ``d/dx f**g = f**g * (g * ln(f))'`` for a variable exponent.

    Consumes the derivative structure metadata, rewrites the power as an
    exponential, differentiates the exponent part through the existing rules
    and returns the combined result together with a single exponential-rule
    step.
    """

    def can_apply(self, structure) -> bool:
        """Return whether the expression is a power with a variable exponent.

        The expression is a candidate when it is a :class:`sympy.Pow` whose
        exponent contains the differentiation variable (e.g. ``x**x``,
        ``(x + 1)**x``, ``sin(x)**x``).

        Parameters
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        bool
            ``True`` when the expression is a supported variable-exponent
            power.
        """
        try:
            expression = structure["expression"]
            variable = structure["variable"]
        except (KeyError, TypeError):
            return False
        return isinstance(expression, Pow) and expression.exp.has(variable)

    def apply(self, structure) -> tuple[object, Step]:
        """Return the general power derivative result.

        Parameters
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        tuple[object, Step]
            The combined derivative ``(f**g * (g * ln(f))', step)``. The step
            is titled "Apply the exponential rule" and carries kind
            ``exponential_rule``.

        Raises
        ------
        UnsupportedExpressionError
            If the expression is not a power with a variable exponent.
        """
        self._ensure_applicable(structure)
        expression = structure["expression"]
        variable = structure["variable"]
        base = expression.base
        exponent = expression.exp

        inner = Mul(exponent, log(base), evaluate=False)
        inner_prime = GeneralPowerRule._differentiate(inner, variable)

        result = Mul(expression, inner_prime, evaluate=False)

        # Educational content: show f^g = exp(g*ln f) transformation and differentiation
        formula = "\\frac{d}{dx} f(x)^{g(x)} = f(x)^{g(x)} \\cdot \\left( \\ln f(x) \\cdot g'(x) + g(x) \\cdot \\frac{f'(x)}{f(x)} \\right)"
        
        substitution = (
            f"\\frac{{d}}{{d{latex(variable)}}} {latex(base)}^{{{latex(exponent)}}} = "
            f"{latex(expression)} \\cdot \\left( "
            f"\\ln\\left({latex(base)}\\right) \\cdot {latex(GeneralPowerRule._differentiate(exponent, variable))} "
            f"+ {latex(exponent)} \\cdot \\frac{{{latex(GeneralPowerRule._differentiate(base, variable))}}}{{{latex(base)}}} "
            f"\\right)"
        )
        evaluation = f"= {latex(result)}"

        step = make_step(
            "Differentiate using the general power rule",
            f"Rewrite f(x)^g(x) as exp(g(x)*ln(f(x))) and differentiate the exponent. "
            f"Here f = {latex(base)}, g = {latex(exponent)}. "
            f"The derivative is f^g * (g' * ln(f) + g * f'/f).",
            "\\begin{aligned}\n"
            f"{formula} \\\\\n"
            f"{substitution} \\\\\n"
            f"= {latex(result)}\n"
            "\\end{aligned}",
            "general_power_rule",
        )
        step.metadata["base"] = base
        step.metadata["exponent"] = exponent
        step.metadata["inner"] = Mul(exponent, log(base), evaluate=False)
        step.metadata["inner_derivative"] = inner_prime
        step.metadata["result"] = result
        return result, step

    @staticmethod
    def _differentiable(expression, variable) -> bool:
        """Return whether the exponent part can be differentiated.

        The transformed inner ``g * ln(f)`` groups a constant with a pure
        number the module handles: whether it can be differentiated through the
        full pipeline decides applicability, mirroring the other composition
        rules.
        """
        return GeneralPowerRule._differentiate_supported(expression, variable)

    @staticmethod
    def _differentiate_supported(expression, variable) -> bool:
        """Return whether ``expression`` is differentiable by the pipeline."""
        from ...solver.derivative_solver import DerivativeSolver

        result, _ = DerivativeSolver._solve_single(expression, variable)
        return result is not None

    @staticmethod
    def _differentiate(expression, variable):
        """Differentiate an exponent part through the full rule pipeline.

        Each exponent part is routed through the same ordered chain the solver
        uses -- implicit, constant, power, sum, product, quotient, chain,
        trigonometric and exp/log.
        """
        from ...solver.derivative_solver import DerivativeSolver

        result, _ = DerivativeSolver._solve_single(expression, variable)
        if result is None:
            raise UnsupportedExpressionError(
                f"GeneralPowerRule cannot differentiate the exponent part "
                f"{expression!r}."
            )
        return result


__all__ = ["GeneralPowerRule"]