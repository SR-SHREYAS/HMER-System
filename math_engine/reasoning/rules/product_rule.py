"""Rule that applies the product rule of differentiation.

:class:`ProductRule` implements the product rule of differentiation:

.. math::

    \\frac{d}{dx} (f \\cdot g) = f' \\cdot g + f \\cdot g'

It reads the expression and variable from the structured metadata produced by
:class:`ExtractDerivativeStructureRule`. When the expression is a top-level
:class:`sympy.Mul`, the rule splits it into its factors and differentiates every
factor by routing it through the full rule pipeline the solver uses (implicit,
constant, power, sum, product, quotient, chain, trigonometric and exp/log
rules) -- no factor is differentiated by hand. For two factors the result is
``f'*g + f*g'``; for more than two factors the same sum of pairwise
contributions is built over all factors. The rule only applies when it can
differentiate every factor; otherwise it leaves the expression unchanged.
"""

from __future__ import annotations

from sympy import Add, Mul, Pow, latex

from ...models import Step
from .base_rule import BaseRule, make_step
from .rule_exceptions import UnsupportedExpressionError


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
        if not isinstance(expression, Mul):
            return False
        if any(
            isinstance(factor, Pow)
            and factor.exp.is_number
            and factor.exp < 0
            for factor in expression.args
        ):
            return False
        return all(
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
        factor_derivatives = []
        for index, factor in enumerate(factors):
            factor_derivative = ProductRule._differentiate(factor, variable)
            factor_derivatives.append(factor_derivative)
            others = Mul(*[
                other for other_index, other in enumerate(factors)
                if other_index != index
            ], evaluate=False)
            terms.append(
                Mul(factor_derivative, others, evaluate=False)
            )
        result = Add(*terms, evaluate=False)

        # Educational content: show product rule formula, factors, and derivatives
        formula = "\\frac{d}{dx} (f \\cdot g) = f' \\cdot g + f \\cdot g'"
        factors_latex = " \\cdot ".join(latex(f) for f in factors)
        
        # Show each term: f_i' * (product of other factors)
        term_explanations = []
        for i, (factor, f_prime) in enumerate(zip(factors, factor_derivatives)):
            others = [f for j, f in enumerate(factors) if j != i]
            if len(others) == 1:
                others_latex = latex(others[0])
            else:
                others_latex = " \\cdot ".join(latex(o) for o in others)
            # Wrap in parentheses if the other factors are more than one or it's a compound expression
            if len(others) > 1 or (len(others) == 1 and isinstance(others[0], (Add, Mul, Pow))):
                others_latex = f"\\left({others_latex}\\right)"
            term_explanations.append(f"{latex(f_prime)} \\cdot {others_latex}")
        
        substitution = (
            f"\\frac{{d}}{{d{latex(variable)}}} ({factors_latex}) = "
            + " + ".join(term_explanations)
        )
        evaluation = f"= {latex(result)}"

        step = make_step(
            "Apply the product rule",
            f"The derivative of a product f*g is f'*g + f*g'. "
            f"For {factors_latex}, differentiate each factor and multiply by the others.",
            "\\begin{aligned}\n"
            f"{formula} \\\\\n"
            f"{substitution} \\\\\n"
            f"{evaluation}\n"
            "\\end{aligned}",
            "product_rule",
        )
        step.metadata["factors"] = factors
        step.metadata["factor_derivatives"] = factor_derivatives
        step.metadata["result"] = result
        return result, step

    @staticmethod
    def _differentiable(expression, variable) -> bool:
        """Return whether a factor can be differentiated by the full pipeline."""
        from ...solver.derivative_solver import DerivativeSolver

        result, _ = DerivativeSolver._solve_single(expression, variable)
        return result is not None

    @staticmethod
    def _differentiate(expression, variable):
        """Differentiate a single factor through the full rule pipeline.

        Each factor is routed through the same ordered chain the solver
        uses -- implicit, constant, power, sum, product, quotient, chain,
        trigonometric and exp/log.
        """
        from ...solver.derivative_solver import DerivativeSolver

        result, _ = DerivativeSolver._solve_single(expression, variable)
        if result is None:
            raise UnsupportedExpressionError(
                f"ProductRule cannot differentiate the factor {expression!r}."
            )
        return result


__all__ = ["ProductRule"]