"""Rule that applies the exponential and logarithmic differentiation rules.

:class:`ExpLogRule` implements the derivatives of ``exp`` and ``log``:

.. math::

    \\frac{d}{dx} \\exp(u) = \\exp(u) \\cdot u'
    \\qquad
    \\frac{d}{dx} \\log(u) = \\frac{1}{u} \\cdot u'

It reads the expression and variable from the structured metadata produced by
:class:`ExtractDerivativeStructureRule`. When the expression is ``exp(inner)``
or ``log(inner)`` the rule computes ``inner'`` by routing the argument through
the existing rule pipeline (:class:`ConstantDerivativeRule`,
:class:`PowerRule`, :class:`SumRule`, :class:`ProductRule`,
:class:`QuotientRule`, :class:`ChainRule`, :class:`TrigRule`) -- the inner is
never differentiated by hand. The result ``outer'(inner) * inner'`` is returned
raw: nothing is simplified. The rule only applies when the inner can be
differentiated by the existing pipeline; otherwise it leaves the expression
unchanged.
"""

from __future__ import annotations

from sympy import Integer, Mul, Pow, exp, latex, log

from ...models import Step
from .base_rule import BaseRule, make_step
from .rule_exceptions import UnsupportedExpressionError
from .constant_derivative_rule import ConstantDerivativeRule
from .power_rule import PowerRule
from .sum_rule import SumRule
from .product_rule import ProductRule
from .quotient_rule import QuotientRule
from .chain_rule import ChainRule
from .trig_rule import TrigRule


class ExpLogRule(BaseRule):
    """Evaluate ``d/dx exp(u) = exp(u)*u'`` and ``d/dx log(u) = (1/u)*u'``.

    Consumes the derivative structure metadata, differentiates the
    exp/log argument through the existing rules and returns the combined
    result together with a single exponential/logarithmic-rule step.
    """

    def can_apply(self, structure) -> bool:
        """Return whether the expression is a supported exp/log function.

        The expression is a candidate when it is exactly ``exp(inner)`` or
        ``log(inner)`` whose inner can be differentiated by the existing rules.

        Parameters
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        bool
            ``True`` when the expression is a supported exp/log function.
        """
        try:
            expression = structure["expression"]
            variable = structure["variable"]
        except (KeyError, TypeError):
            return False
        inner = ExpLogRule._inner(expression)
        if inner is None:
            return False
        return ExpLogRule._differentiable(inner, variable)

    def apply(self, structure) -> tuple[object, Step]:
        """Return the exp/log derivative result.

        Parameters
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        tuple[object, Step]
            The combined derivative ``(outer'(inner) * inner', step)``. The step
            is titled "Differentiate using exponential/logarithmic rule" and
            carries kind ``exp_log_rule``.

        Raises
        ------
        UnsupportedExpressionError
            If the expression is not a supported exp/log function.
        """
        self._ensure_applicable(structure)
        expression = structure["expression"]
        variable = structure["variable"]

        inner = ExpLogRule._inner(expression)
        inner_prime = ExpLogRule._differentiate(inner, variable)
        if expression.func is exp:
            outer_prime = exp(inner)
        elif expression.func is log:
            outer_prime = Pow(inner, Integer(-1), evaluate=False)
        else:
            raise UnsupportedExpressionError(
                "ExpLogRule only supports exp and log."
            )

        result = Mul(outer_prime, inner_prime, evaluate=False)
        step = make_step(
            "Differentiate using exponential/logarithmic rule",
            "Differentiate using exponential/logarithmic rule.",
            latex(result),
            "exp_log_rule",
        )
        step.metadata["inner"] = inner
        step.metadata["inner_derivative"] = inner_prime
        step.metadata["result"] = result
        return result, step

    @staticmethod
    def _inner(expression):
        """Return the argument of ``exp``/``log`` or ``None`` otherwise."""
        if expression.func is exp and len(expression.args) == 1:
            return expression.args[0]
        if expression.func is log and len(expression.args) == 2:
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
            or TrigRule().can_apply(structure)
        )

    @staticmethod
    def _differentiate(expression, variable):
        """Differentiate an inner through the existing rule pipeline.

        Each inner is routed through the same rules the solver uses: the
        constant rule, the power rule, the sum rule, the product rule, the
        quotient rule, the chain rule and the trig rule.
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
        if TrigRule().can_apply(structure):
            result, _ = TrigRule().apply(structure)
            return result
        raise UnsupportedExpressionError(
            f"ExpLogRule cannot differentiate the inner {expression!r}."
        )


__all__ = ["ExpLogRule"]