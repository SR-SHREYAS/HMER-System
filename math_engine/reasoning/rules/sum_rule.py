"""Rule that applies the sum rule of differentiation.

:class:`SumRule` implements the sum rule of differentiation:

.. math::

    \\frac{d}{dx} (f + g) = f' + g'

It reads the expression and variable from the structured metadata produced by
:class:`ExtractDerivativeStructureRule`. When the expression is a top-level
:class:`sympy.Add`, every term is differentiated by routing it through the same
existing rule pipeline (:class:`ConstantDerivativeRule`, :class:`PowerRule`,
and recursively :class:`SumRule` for nested additions) -- no term is
differentiated by hand. The per-term results are then recombined with addition.
The rule only applies when it can differentiate every term; otherwise it leaves
the expression unchanged.
"""

from __future__ import annotations

from sympy import Add, latex

from ...models import Step
from .base_rule import BaseRule, make_step
from .rule_exceptions import UnsupportedExpressionError
from .constant_derivative_rule import ConstantDerivativeRule
from .power_rule import PowerRule


class SumRule(BaseRule):
    """Evaluate ``d/dx (f + g) = f' + g'`` for a top-level addition.

    Consumes the derivative structure metadata, differentiates each term through
    the existing rules and returns the combined result together with a single
    sum-rule step.
    """

    def can_apply(self, structure) -> bool:
        """Return whether the expression is a fully-supported addition.

        The expression is a candidate when it is a top-level
        :class:`sympy.Add` whose every term can be differentiated by the
        existing rules (constant, power, or a nested supported addition).

        Parameters
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        bool
            ``True`` when the expression is a supported top-level addition.
        """
        try:
            expression = structure["expression"]
            variable = structure["variable"]
        except (KeyError, TypeError):
            return False
        return isinstance(expression, Add) and all(
            SumRule._supported(term, variable) for term in expression.args
        )

    def apply(self, structure) -> tuple[Add, Step]:
        """Return the sum-rule derivative result.

        Parameters
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        tuple[Add, Step]
            The combined derivative ``(f' + g', step)``. The step is titled
            "Apply the sum rule" and carries kind ``sum_rule``.

        Raises
        ------
        UnsupportedExpressionError
            If the expression is not a supported addition.
        """
        self._ensure_applicable(structure)
        expression = structure["expression"]
        variable = structure["variable"]

        terms = [
            SumRule._differentiate(term, variable) for term in expression.args
        ]
        result = Add(*terms, evaluate=False)
        step = make_step(
            "Apply the sum rule",
            "Apply the sum rule.",
            latex(result),
            "sum_rule",
        )
        step.metadata["terms"] = terms
        step.metadata["result"] = result
        return result, step

    @staticmethod
    def _supported(expression, variable) -> bool:
        """Return whether a term can be differentiated by the existing rules."""
        if isinstance(expression, Add):
            return all(
                SumRule._supported(term, variable) for term in expression.args
            )
        structure = {"expression": expression, "variable": variable}
        return ConstantDerivativeRule().can_apply(
            structure
        ) or PowerRule().can_apply(structure)

    @staticmethod
    def _differentiate(expression, variable):
        """Differentiate a single term through the existing rule pipeline.

        Each term is routed through the same rules the solver uses: the
        constant rule, the power rule, and (for nested additions) the sum rule
        itself.
        """
        if isinstance(expression, Add):
            terms = [
                SumRule._differentiate(term, variable)
                for term in expression.args
            ]
            return Add(*terms, evaluate=False)

        structure = {"expression": expression, "variable": variable}
        if ConstantDerivativeRule().can_apply(structure):
            result, _ = ConstantDerivativeRule().apply(structure)
            return result
        if PowerRule().can_apply(structure):
            result, _ = PowerRule().apply(structure)
            return result
        raise UnsupportedExpressionError(
            f"SumRule cannot differentiate the term {expression!r}."
        )


__all__ = ["SumRule"]