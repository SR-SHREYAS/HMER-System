"""Rule that applies the chain rule of differentiation.

:class:`ChainRule` implements the chain rule of differentiation:

.. math::

    \\frac{d}{dx} f(g(x)) = f'(g(x)) \\cdot g'(x)

It reads the expression and variable from the structured metadata produced by
:class:`ExtractDerivativeStructureRule`. When the expression is a composition
-- a :class:`sympy.Pow` whose base is not just the differentiation variable,
such as ``(x+1)**2``, ``(x**2)**3`` or ``sqrt(x**2)`` -- the rule treats the
base as the inner function and the power as the outer function. The outer
derivative is computed by differentiating the outer function against a fresh
inner placeholder (reusing :class:`PowerRule`); the inner derivative is computed
by routing the base through the same existing rule pipeline
(:class:`ConstantDerivativeRule`, :class:`PowerRule`, :class:`SumRule`,
:class:`ProductRule`, :class:`QuotientRule`) -- the inner is never
differentiated by hand. The result ``outer'(inner) * inner'`` is returned raw:
nothing is simplified, expanded or merged. The rule only applies when the inner
can be differentiated by the existing pipeline; otherwise it leaves the
expression unchanged.
"""

from __future__ import annotations

from sympy import Mul, Pow, Symbol, latex

from ...models import Step
from .base_rule import BaseRule, make_step
from .rule_exceptions import UnsupportedExpressionError
from .constant_derivative_rule import ConstantDerivativeRule
from .power_rule import PowerRule
from .sum_rule import SumRule
from .product_rule import ProductRule
from .quotient_rule import QuotientRule


class ChainRule(BaseRule):
    """Evaluate ``d/dx f(g(x)) = f'(g(x)) * g'(x)`` for a composition.

    Consumes the derivative structure metadata, treats the power base as the
    inner function, differentiates the outer function against a placeholder and
    the inner function through the existing rules, and returns the combined
    result together with a single chain-rule step.
    """

    def can_apply(self, structure) -> bool:
        """Return whether the expression is a supported composition.

        The expression is a candidate when it is a :class:`sympy.Pow` whose base
        is not just the differentiation variable and whose base (the inner
        function) can be differentiated by the existing rules.

        Parameters
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        bool
            ``True`` when the expression is a supported composition.
        """
        try:
            expression = structure["expression"]
            variable = structure["variable"]
        except (KeyError, TypeError):
            return False
        if not isinstance(expression, Pow) or expression.base == variable:
            return False
        return ChainRule._differentiable(expression.base, variable)

    def apply(self, structure) -> tuple[object, Step]:
        """Return the chain-rule derivative result.

        Parameters
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        tuple[object, Step]
            The combined derivative ``(outer'(inner) * inner', step)``. The step
            is titled "Apply the chain rule" and carries kind ``chain_rule``.

        Raises
        ------
        UnsupportedExpressionError
            If the expression is not a supported composition.
        """
        self._ensure_applicable(structure)
        expression = structure["expression"]
        variable = structure["variable"]

        outer = expression.base
        inner = expression.base
        outer_prime = ChainRule._outer_derivative(
            expression.exp, inner, variable
        )
        inner_prime = ChainRule._differentiate(inner, variable)

        result = Mul(outer_prime, inner_prime, evaluate=False)
        step = make_step(
            "Apply the chain rule",
            "Apply the chain rule.",
            latex(result),
            "chain_rule",
        )
        step.metadata["outer"] = expression
        step.metadata["inner"] = inner
        step.metadata["outer_derivative"] = outer_prime
        step.metadata["inner_derivative"] = inner_prime
        step.metadata["result"] = result
        return result, step

    @staticmethod
    def _outer_derivative(exponent, inner, variable):
        """Differentiate ``inner**exponent`` treating ``inner`` as a variable.

        The outer function is ``u**exponent`` with ``u`` a fresh placeholder.
        It is differentiated with the power rule (``exponent * u**(exponent-1)``)
        and the placeholder is then replaced by the inner function. The result is
        built unevaluated so the inner function stays visible, e.g.
        ``2*(x+1)**1`` for ``(x+1)**2`` and ``3*(x**2)**2`` for ``(x**2)**3``.
        """
        placeholder = Symbol("_outer_")
        structure = {
            "expression": Pow(placeholder, exponent),
            "variable": placeholder,
        }
        if not PowerRule().can_apply(structure):
            raise UnsupportedExpressionError(
                "ChainRule cannot differentiate the outer function "
                f"u**{exponent}."
            )
        return Mul(
            exponent,
            Pow(inner, exponent - 1, evaluate=False),
            evaluate=False,
        )

    @staticmethod
    def _differentiable(expression, variable) -> bool:
        """Return whether an inner function can be differentiated by the rules."""
        structure = {"expression": expression, "variable": variable}
        return (
            ConstantDerivativeRule().can_apply(structure)
            or PowerRule().can_apply(structure)
            or SumRule().can_apply(structure)
            or ProductRule().can_apply(structure)
            or QuotientRule().can_apply(structure)
        )

    @staticmethod
    def _differentiate(expression, variable):
        """Differentiate an inner function through the existing rule pipeline.

        Each inner function is routed through the same rules the solver uses:
        the constant rule, the power rule, the sum rule, the product rule and
        the quotient rule.
        """
        structure = {"expression": expression, "variable": variable}
        if ConstantDerivativeRule().can_apply(structure):
            result, _ = ConstantDerivativeRule().apply(structure)
            return result
        if PowerRule().can_apply(structure):
            result, _ = PowerRule().apply(structure)
            return result
        if SumRule().can_apply(structure):
            result, _ = SumRule().apply(structure)
            return result
        if ProductRule().can_apply(structure):
            result, _ = ProductRule().apply(structure)
            return result
        if QuotientRule().can_apply(structure):
            result, _ = QuotientRule().apply(structure)
            return result
        raise UnsupportedExpressionError(
            f"ChainRule cannot differentiate the inner function {expression!r}."
        )


__all__ = ["ChainRule"]