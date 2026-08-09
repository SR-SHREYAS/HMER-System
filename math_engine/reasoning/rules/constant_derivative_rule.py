"""Rule that applies the constant differentiation rule.

:class:`ConstantDerivativeRule` implements the constant rule of
differentiation: the derivative of a constant with respect to any variable is
zero. It reads the expression and the variable of differentiation from the
structured metadata produced by :class:`ExtractDerivativeStructureRule` and, if
the expression contains no free occurrence of the variable, evaluates the
derivative to :data:`sympy.S.Zero`. The rule never applies to non-constant
expressions, never simplifies anything and never combines with other rules.
"""

from __future__ import annotations

from sympy import Integer

from ...models import Step
from .base_rule import BaseRule, make_step
from .rule_exceptions import UnsupportedExpressionError


class ConstantDerivativeRule(BaseRule):
    """Evaluate ``d/dx (c) = 0`` for a constant expression ``c``.

    Consumes the derivative structure metadata and, when applicable, returns
    the differentiation result ``0`` together with the constant-rule step.
    """

    def can_apply(self, structure) -> bool:
        """Return whether the expression is constant in the variable.

        The expression is constant when the variable of differentiation does
        not occur in the expression's free symbols.

        Parameters
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        bool
            ``True`` when the variable is absent from the expression.
        """
        try:
            expression = structure["expression"]
            variable = structure["variable"]
        except (KeyError, TypeError):
            return False
        return variable not in expression.free_symbols

    def apply(self, structure) -> tuple[Integer, Step]:
        """Return the constant derivative result ``0``.

        Parameters
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        tuple[Integer, Step]
            ``(Integer(0), step)`` for a constant expression. The step is titled
            "Differentiate the constant" and carries kind ``constant_rule``.

        Raises
        ------
        UnsupportedExpressionError
            If the metadata is incomplete or the expression is not constant.
        """
        self._ensure_applicable(structure)
        expression = structure["expression"]
        variable = structure["variable"]

        result = Integer(0)
        step = make_step(
            "The derivative of a constant is zero",
            "The derivative of a constant is zero.",
            "0",
            "constant_rule",
        )
        step.metadata["result"] = result
        step.metadata["expression"] = expression
        step.metadata["variable"] = variable
        return result, step


__all__ = ["ConstantDerivativeRule"]