"""Rule that applies the trigonometric differentiation rules.

:class:`TrigRule` implements the derivatives of ``sin`` and ``cos``:

.. math::

    \\frac{d}{dx} \\sin(u) = \\cos(u) \\cdot u'
    \\qquad
    \\frac{d}{dx} \\cos(u) = -\\sin(u) \\cdot u'

It reads the expression and variable from the structured metadata produced by
:class:`ExtractDerivativeStructureRule`. When the expression is ``sin(inner)``
or ``cos(inner)`` the rule computes ``inner'`` by routing the argument through
the existing rule pipeline (:class:`ConstantDerivativeRule`,
:class:`PowerRule`, :class:`SumRule`, :class:`ProductRule`,
:class:`QuotientRule`, :class:`ChainRule`) -- the inner is never
differentiated by hand. The result ``trig'(inner) * inner'`` is returned raw:
nothing is simplified. The rule only applies when the inner can be
differentiated by the existing pipeline; otherwise it leaves the expression
unchanged.
"""

from __future__ import annotations

from sympy import Integer, Mul, cos, latex, sin

from ...models import Step
from .base_rule import BaseRule, make_step
from .rule_exceptions import UnsupportedExpressionError
from .constant_derivative_rule import ConstantDerivativeRule
from .power_rule import PowerRule
from .sum_rule import SumRule
from .product_rule import ProductRule
from .quotient_rule import QuotientRule
from .chain_rule import ChainRule


class TrigRule(BaseRule):
    """Evaluate ``d/dx sin(u) = cos(u)*u'`` and ``d/dx cos(u) = -sin(u)*u'``.

    Consumes the derivative structure metadata, differentiates the trig
    argument through the existing rules and returns the combined result
    together with a single trigonometric-rule step.
    """

    def can_apply(self, structure) -> bool:
        """Return whether the expression is a supported trig function.

        The expression is a candidate when it is exactly ``sin(inner)`` or
        ``cos(inner)`` whose inner can be differentiated by the existing rules.

        Parameters
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        bool
            ``True`` when the expression is a supported trig function.
        """
        try:
            expression = structure["expression"]
            variable = structure["variable"]
        except (KeyError, TypeError):
            return False
        inner = TrigRule._inner(expression)
        if inner is None:
            return False
        return TrigRule._differentiable(inner, variable)

    def apply(self, structure) -> tuple[object, Step]:
        """Return the trigonometric derivative result.

        Parameters
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        tuple[object, Step]
            The combined derivative ``(trig'(inner) * inner', step)``. The step
            is titled "Differentiate using trigonometric rule" and carries kind
            ``trigonometric_rule``.

        Raises
        ------
        UnsupportedExpressionError
            If the expression is not a supported trig function.
        """
        self._ensure_applicable(structure)
        expression = structure["expression"]
        variable = structure["variable"]

        inner = TrigRule._inner(expression)
        inner_prime = TrigRule._differentiate(inner, variable)
        if expression.func is sin:
            outer_prime = cos(inner)
        elif expression.func is cos:
            outer_prime = Mul(Integer(-1), sin(inner), evaluate=False)
        else:
            raise UnsupportedExpressionError(
                "TrigRule only supports sin and cos."
            )

        result = Mul(outer_prime, inner_prime, evaluate=False)
        step = make_step(
            "Differentiate using trigonometric rule",
            "Differentiate using trigonometric rule.",
            latex(result),
            "trigonometric_rule",
        )
        step.metadata["inner"] = inner
        step.metadata["inner_derivative"] = inner_prime
        step.metadata["result"] = result
        return result, step

    @staticmethod
    def _inner(expression):
        """Return the argument of ``sin``/``cos`` or ``None`` otherwise."""
        if expression.func is sin and len(expression.args) == 1:
            return expression.args[0]
        if expression.func is cos and len(expression.args) == 1:
            return expression.args[0]
        return None

    @staticmethod
    def _differentiable(expression, variable) -> bool:
        """Return whether an inner can be differentiated by the existing rules."""
        structure = {"expression": expression, "variable": variable}
        return (
            ConstantDerivativeRule().can_apply(structure)
            or PowerRule().can_apply(structure)
            or SumRule().can_apply(structure)
            or ProductRule().can_apply(structure)
            or QuotientRule().can_apply(structure)
            or ChainRule().can_apply(structure)
        )

    @staticmethod
    def _differentiate(expression, variable):
        """Differentiate an inner through the existing rule pipeline.

        Each inner is routed through the same rules the solver uses: the
        constant rule, the power rule, the sum rule, the product rule, the
        quotient rule and the chain rule.
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
        if ChainRule().can_apply(structure):
            result, _ = ChainRule().apply(structure)
            return result
        raise UnsupportedExpressionError(
            f"TrigRule cannot differentiate the inner function {expression!r}."
        )


__all__ = ["TrigRule"]