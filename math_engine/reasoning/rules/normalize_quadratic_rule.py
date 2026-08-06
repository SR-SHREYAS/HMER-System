"""Rule that normalizes a quadratic equation into standard form.

:class:`NormalizeQuadraticRule` rearranges any quadratic equation into the
standard form ``ax**2 + bx + c = 0``. Every term is moved to the left-hand
side, SymPy expands and simplifies the result, and a normalized equality is
returned together with a single reasoning step. The rule owns exactly one
responsibility: it never extracts coefficients, computes a discriminant, or
solves the equation.
"""

from __future__ import annotations

from sympy import Add, Eq, Equality, Poly, expand, latex

from ...models import Step
from .base_rule import BaseRule, make_step
from .rule_exceptions import UnsupportedExpressionError


class NormalizeQuadraticRule(BaseRule):
    """Rearrange a quadratic equation into the standard quadratic form."""

    def can_apply(self, expression: Equality) -> bool:
        """Return whether the expression is a single-variable equation.

        The rule applies to any equality in a single variable; the quadratic
        nature is guaranteed by the solver that drives this rule.

        Parameters
        ----------
        expression :
            The equation to inspect.

        Returns
        -------
        bool
            ``True`` when the expression is a one-variable equality.
        """
        return isinstance(expression, Equality) and len(expression.free_symbols) == 1

    def apply(self, expression: Equality) -> tuple[Equality, Step]:
        """Rearrange the equation into standard quadratic form.

        Moves every term to the left-hand side, expands and simplifies the
        difference, and returns the normalized equality ``ax**2 + bx + c = 0``
        together with the reasoning step explaining the transformation.

        Parameters
        ----------
        expression :
            The equation to normalize.

        Returns
        -------
        tuple[Equality, Step]
            The normalized equation and its single reasoning step.

        Raises
        ------
        UnsupportedExpressionError
            If the equation cannot be reduced to a polynomial in one variable.
        """
        self._ensure_applicable(expression)
        variable = next(iter(expression.free_symbols))

        difference = expand(self._flatten(expression.lhs - expression.rhs))
        try:
            polynomial = Poly(difference, variable)
        except Exception as exc:  # noqa: BLE001 - any non-polynomial body
            raise UnsupportedExpressionError(
                "The equation could not be reduced to a polynomial in a "
                "single variable."
            ) from exc
        if polynomial.degree() != 2:
            raise UnsupportedExpressionError(
                "NormalizeQuadraticRule expects a quadratic equation; "
                f"got a polynomial of degree {polynomial.degree()}."
            )
        if polynomial.LC() < 0:
            polynomial = -polynomial

        normalized = Eq(polynomial.as_expr(), 0)
        step = make_step(
            "Rearrange into standard form",
            "Rearrange the equation into the standard quadratic form.",
            latex(normalized),
            "normalize_quadratic",
        )
        return normalized, step

    @staticmethod
    def _flatten(expression) -> object:
        """Re-evaluate nested additions from the LaTeX parser.

        The parser produces unevaluated, nested :class:`Add` nodes that plain
        :func:`expand` does not re-evaluate; rebuilding the additions lets
        SymPy's polynomial machinery see the full expression.
        """
        if isinstance(expression, Add):
            return Add(*(NormalizeQuadraticRule._flatten(arg) for arg in expression.args))
        return expression
