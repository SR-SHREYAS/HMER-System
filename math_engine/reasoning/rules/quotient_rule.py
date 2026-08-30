"""Rule that applies the quotient rule of differentiation.

:class:`QuotientRule` implements the quotient rule of differentiation:

.. math::

    \\frac{d}{dx} \\left(\\frac{f}{g}\\right) = \\frac{f' \\cdot g - f \\cdot g'}{g^2}

It reads the expression and variable from the structured metadata produced by
:class:`ExtractDerivativeStructureRule`. When the expression is a division --
represented in SymPy as a :class:`sympy.Mul` whose factors include a power with
a negative exponent (e.g. ``x/x``, ``3/x``) -- the rule splits it into the
numerator ``f`` and denominator ``g``. Both ``f'`` and ``g'`` are computed by
routing the sub-expressions through the full rule pipeline the solver uses
(implicit, constant, power, sum, product, quotient, chain, trigonometric and
exp/log rules) -- no derivative is computed by hand. The result
``(f'*g - f*g') / g**2`` is returned raw: nothing is simplified, cancelled or
reduced. The rule only applies when it can differentiate both the numerator and
the denominator; otherwise it leaves the expression unchanged.
"""

from __future__ import annotations

from sympy import Add, Integer, Mul, Pow, Rational, latex

from ...models import Step
from .base_rule import BaseRule, make_step
from .rule_exceptions import UnsupportedExpressionError


class QuotientRule(BaseRule):
    """Evaluate ``d/dx (f/g) = (f'*g - f*g')/g**2`` for a division.

    Consumes the derivative structure metadata, splits the expression into
    numerator and denominator, differentiates each through the existing rules
    and returns the combined result together with a single quotient-rule step.
    """

    def can_apply(self, structure) -> bool:
        """Return whether the expression is a fully-supported division.

        The expression is a candidate when it represents a division -- a
        :class:`sympy.Mul` carrying at least one negative-power factor, or a
        standalone power with a negative exponent -- whose numerator and
        denominator can both be differentiated by the existing rules.

        Parameters
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        bool
            ``True`` when the expression is a supported division.
        """
        try:
            expression = structure["expression"]
            variable = structure["variable"]
        except (KeyError, TypeError):
            return False
        numerator, denominator = QuotientRule._parts(expression)
        if numerator is None or denominator is None:
            return False
        return QuotientRule._differentiable(
            numerator, variable
        ) and QuotientRule._differentiable(denominator, variable)

    def apply(self, structure) -> tuple[object, Step]:
        """Return the quotient-rule derivative result.

        Parameters
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        tuple[object, Step]
            The combined derivative ``((f'*g - f*g')/g**2, step)``. The step is
            titled "Apply the quotient rule" and carries kind ``quotient_rule``.

        Raises
        ------
        UnsupportedExpressionError
            If the expression is not a supported division.
        """
        self._ensure_applicable(structure)
        expression = structure["expression"]
        variable = structure["variable"]

        numerator, denominator = QuotientRule._parts(expression)
        numerator_derivative = QuotientRule._differentiate(
            numerator, variable
        )
        denominator_derivative = QuotientRule._differentiate(
            denominator, variable
        )

        positive = Mul(numerator_derivative, denominator, evaluate=False)
        negative = Mul(
            Integer(-1),
            Mul(numerator, denominator_derivative, evaluate=False),
            evaluate=False,
        )
        total = Add(positive, negative, evaluate=False)
        result = Mul(total, Pow(denominator, Integer(-2)), evaluate=False)

        # Educational content: show quotient rule formula, substitution, and evaluation
        formula = "\\frac{d}{dx} \\left(\\frac{f}{g}\\right) = \\frac{f' \\cdot g - f \\cdot g'}{g^2}"
        
        # Add parentheses around denominator if it's a compound expression
        denom_latex = latex(denominator)
        if isinstance(denominator, (Add, Mul, Pow)):
            denom_latex = f"\\left({denom_latex}\\right)"
        
        substitution = (
            f"\\frac{{d}}{{d{latex(variable)}}} \\left(\\frac{{{latex(numerator)}}}{{{denom_latex}}}\\right) = "
            f"\\frac{{{latex(numerator_derivative)} \\cdot {denom_latex} - {latex(numerator)} \\cdot {latex(denominator_derivative)}}}{{{denom_latex}^2}}"
        )
        evaluation = f"= {latex(result)}"

        step = make_step(
            "Apply the quotient rule",
            f"The derivative of a quotient f/g is (f'*g - f*g')/g^2. "
            f"Here f = {latex(numerator)}, g = {latex(denominator)}.",
            "\\begin{aligned}\n"
            f"{formula} \\\\\n"
            f"{substitution} \\\\\n"
            f"= {latex(result)}\n"
            "\\end{aligned}",
            "quotient_rule",
        )
        step.metadata["numerator"] = numerator
        step.metadata["denominator"] = denominator
        step.metadata["numerator_derivative"] = numerator_derivative
        step.metadata["denominator_derivative"] = denominator_derivative
        step.metadata["result"] = result
        return result, step

    @staticmethod
    def _parts(expression) -> tuple[object, object | None]:
        """Split an expression into ``(numerator, denominator)``.

        Returns ``(None, None)`` when the expression is not a division. A
        division is a :class:`sympy.Mul` whose factors include a power with a
        negative exponent (e.g. ``x/x`` is ``Mul(x, Pow(x, -1))``), or a
        standalone power with a negative exponent (e.g. ``1/(x+1)``). The
        numerator is the product of the remaining factors (``1`` when there are
        none) and the denominator is the product of the negative-power bases,
        each raised to the absolute value of its exponent.
        """
        if isinstance(expression, Pow) and QuotientRule._negative(expression):
            return Integer(1), expression.base
        if not isinstance(expression, Mul):
            return None, None
        numerator_factors = []
        denominator_factors = []
        for factor in expression.args:
            if isinstance(factor, Pow) and QuotientRule._negative(factor):
                denominator_factors.append(factor.base ** (-factor.exp))
            else:
                numerator_factors.append(factor)
        if not denominator_factors:
            return None, None
        numerator = Mul(*numerator_factors, evaluate=False) if numerator_factors else Integer(1)
        denominator = Mul(*denominator_factors, evaluate=False)
        return numerator, denominator

    @staticmethod
    def _negative(expression) -> bool:
        """Return whether a power has a strictly negative numeric exponent."""
        return (
            isinstance(expression, Pow)
            and expression.exp.is_number
            and expression.exp < 0
        )

    @staticmethod
    def _differentiable(expression, variable) -> bool:
        """Return whether a part can be differentiated by the full pipeline."""
        from ...solver.derivative_solver import DerivativeSolver

        result, _ = DerivativeSolver._solve_single(expression, variable)
        return result is not None

    @staticmethod
    def _differentiate(expression, variable):
        """Differentiate a single part through the full rule pipeline.

        Each part is routed through the same ordered chain the solver uses
        -- implicit, constant, power, sum, product, quotient, chain,
        trigonometric and exp/log.
        """
        from ...solver.derivative_solver import DerivativeSolver

        result, _ = DerivativeSolver._solve_single(expression, variable)
        if result is None:
            raise UnsupportedExpressionError(
                f"QuotientRule cannot differentiate the part {expression!r}."
            )
        return result


__all__ = ["QuotientRule"]