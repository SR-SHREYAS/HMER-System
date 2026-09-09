"""Rule that applies the sum rule of differentiation.

:class:`SumRule` implements the sum rule of differentiation:

.. math::

    \\frac{d}{dx} (f + g) = f' + g'

It reads the expression and variable from the structured metadata produced by
:class:`ExtractDerivativeStructureRule`. When the expression is a top-level
:class:`sympy.Add`, every term is differentiated by routing it through the full
rule pipeline the solver uses (implicit, constant, power, sum, product,
quotient, chain, trigonometric and exp/log rules) -- no term is differentiated
by hand and nested arguments are differentiated recursively. The per-term
results are then recombined with addition. The rule only applies when it can
differentiate every term; otherwise it leaves the expression unchanged.
"""

from __future__ import annotations

from sympy import Add, latex

from ...models import Step
from .base_rule import BaseRule, make_step
from .rule_exceptions import UnsupportedExpressionError


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

        # Educational content: show sum rule formula and term-by-term breakdown
        formula = "\\frac{d}{dx} (f + g) = \\frac{df}{dx} + \\frac{dg}{dx}"
        terms_latex = " + ".join(latex(term) for term in expression.args)
        derivatives_latex = " + ".join(latex(term) for term in terms)
        substitution = (
            f"\\frac{{d}}{{d{latex(variable)}}} ({terms_latex}) = {derivatives_latex}"
        )
        evaluation = f"= {latex(result)}"

        step = make_step(
            "Apply the sum rule",
            f"The derivative of a sum is the sum of the derivatives. "
            f"Differentiate each term: {terms_latex}.",
            "\\begin{aligned}\n"
            f"{formula} \\\\\n"
            f"{substitution} \\\\\n"
            f"{evaluation}\n"
            "\\end{aligned}",
            "sum_rule",
        )
        step.metadata["terms"] = terms
        step.metadata["result"] = result
        return result, step

    @staticmethod
    def _supported(expression, variable) -> bool:
        """Return whether a term can be differentiated by the full pipeline."""
        from ...solver.derivative_solver import DerivativeSolver

        result, _ = DerivativeSolver._solve_single(expression, variable)
        return result is not None

    @staticmethod
    def _differentiate(expression, variable):
        """Differentiate a single term through the full rule pipeline.

        Each term is routed through the same ordered chain the solver uses
        -- implicit, constant, power, sum, product, quotient, chain,
        trigonometric and exp/log.
        """
        from ...solver.derivative_solver import DerivativeSolver

        result, _ = DerivativeSolver._solve_single(expression, variable)
        if result is None:
            raise UnsupportedExpressionError(
                f"SumRule cannot differentiate the term {expression!r}."
            )
        return result


__all__ = ["SumRule"]