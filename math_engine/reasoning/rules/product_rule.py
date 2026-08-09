"""Rule that applies the product rule of differentiation.

:class:`ProductRule` implements the product rule of differentiation:

.. math::

    \\frac{d}{dx} (f \\cdot g) = f' \\cdot g + f \\cdot g'

It reads the expression and variable from the structured metadata produced by
:class:`ExtractDerivativeStructureRule`. When the expression is a top-level
:class:`sympy.Mul`, the rule splits it into its factors and differentiates every
factor by routing it through the same existing rule pipeline
(:class:`ConstantDerivativeRule`, :class:`PowerRule`, :class:`SumRule`) -- no
factor is differentiated by hand. For two factors the result is ``f'*g + f*g'``;
for more than two factors the same sum of pairwise contributions is built over
all factors. The rule only applies when it can differentiate every factor;
otherwise it leaves the expression unchanged.
"""

from __future__ import annotations

from sympy import Add, Mul, latex

from ...models import Step
from .base_rule import BaseRule, make_step
from .rule_exceptions import UnsupportedExpressionError
from .constant_derivative_rule import ConstantDerivativeRule
from .power_rule import PowerRule
from .sum_rule import SumRule


class ProductRule(BaseRule):
    """Evaluate ``d/dx (f*g) = f'*g + f*g'`` for a top-level product.

    Consumes the derivative structure metadata, differentiates each factor
    through the existing rules and returns the combined result together with a
    single product-rule step.
    """

    def can_apply(self, structure) -> bool:
        """Return whether the expression is a fully-supported product.

        The expression is a candidate when it is a top-level :class:`sympy.Mul`
        whose every factor can be differentiated by the existing rules.

        Parameters
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        bool
            ``True`` when the expression is a supported top-level product.
        """
        try:
            expression = structure["expression"]
            variable = structure["variable"]
        except (KeyError, TypeError):
            return False
        return isinstance(expression, Mul) and all(
            ProductRule._differentiable(factor, variable)
            for factor in expression.args
        )

    def apply(self, structure) -> tuple[Mul, Step]:
        """Return the product-rule derivative result.

        Parameters
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        tuple[Mul, Step]
            The combined derivative ``(f'*g + f*g', step)`` built from the
            individual factor derivatives. The step is titled
            "Apply the product rule" and carries kind ``product_rule``.

        Raises
        ------
        UnsupportedExpressionError
            If the expression is not a supported product.
        """
        self._ensure_applicable(structure)
        expression = structure["expression"]
        variable = structure["variable"]

        factors = list(expression.args)
        terms = []
        for index, factor in enumerate(factors):
            factor_derivative = ProductRule._differentiate(factor, variable)
            others = Mul(*[
                other for other_index, other in enumerate(factors)
                if other_index != index
            ], evaluate=False)
            terms.append(
                Mul(factor_derivative, others, evaluate=False)
            )
        result = Add(*terms, evaluate=False)
        step = make_step(
            "Apply the product rule",
            "Apply the product rule.",
            latex(result),
            "product_rule",
        )
        step.metadata["factors"] = factors
        step.metadata["result"] = result
        return result, step

    @staticmethod
    def _differentiable(expression, variable) -> bool:
        """Return whether a factor can be differentiated by the existing rules."""
        structure = {"expression": expression, "variable": variable}
        return (
            ConstantDerivativeRule().can_apply(structure)
            or PowerRule().can_apply(structure)
            or SumRule().can_apply(structure)
        )

    @staticmethod
    def _differentiate(expression, variable):
        """Differentiate a single factor through the existing rule pipeline.

        Each factor is routed through the same rules the solver uses: the
        constant rule, the power rule, and the sum rule.
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
        raise UnsupportedExpressionError(
            f"ProductRule cannot differentiate the factor {expression!r}."
        )


__all__ = ["ProductRule"]