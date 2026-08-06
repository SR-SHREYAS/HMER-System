"""Rule that extracts the coefficients of a quadratic equation.

:class:`ExtractQuadraticCoefficientsRule` reads an already-normalized quadratic
equation of the form ``ax**2 + bx + c = 0`` and extracts the coefficients
``a``, ``b`` and ``c`` through SymPy's :class:`Poly` machinery. It never
manually parses terms, never computes a discriminant, never classifies roots
and never solves the equation. The coefficients are returned as structured
metadata on the accompanying reasoning step so that later pipeline phases can
consume them without relying on global state.
"""

from __future__ import annotations

from sympy import Eq, Poly, latex
from sympy.polys.polyerrors import PolynomialError

from ...models import Step
from .base_rule import BaseRule, make_step
from .rule_exceptions import UnsupportedExpressionError


class ExtractQuadraticCoefficientsRule(BaseRule):
    """Extract the ``a``, ``b`` and ``c`` coefficients of a quadratic.

    The rule assumes its input is already normalized. Given an equality it
    reduces the left side (with the right side subtracted) to a
    :class:`Poly`, verifies it is quadratic in one variable, and reads the
    coefficients directly from the polynomial.
    """

    def can_apply(self, expression: Eq) -> bool:
        """Return whether the expression is a single-variable quadratic.

        The rule applies to an equality in a single variable whose left-minus-
        right expression is a quadratic polynomial.

        Parameters
        ----------
        expression :
            The already-normalized equation to inspect.

        Returns
        -------
        bool
            ``True`` when the expression is a one-variable quadratic equality.
        """
        if not isinstance(expression, Eq) or len(expression.free_symbols) != 1:
            return False
        variable = next(iter(expression.free_symbols))
        try:
            polynomial = Poly(expression.lhs - expression.rhs, variable)
        except Exception:  # noqa: BLE001 - a non-polynomial body is not a quadratic
            return False
        return polynomial.degree() == 2 and not polynomial.is_zero

    def apply(self, expression: Eq) -> tuple[Eq, Step]:
        """Extract and expose the quadratic coefficients ``a``, ``b``, ``c``.

        Reduces the equation to a :class:`Poly` in its single variable and
        reads the coefficients matching the ``ax**2 + bx + c`` form. The
        original (already-normalized) expression is returned unchanged alongside
        a reasoning step whose metadata carries the coefficients.

        Parameters
        ----------
        expression :
            The already-normalized quadratic equation ``ax**2 + bx + c = 0``.

        Returns
        -------
        tuple[Eq, Step]
            The unchanged normalized equation and the coefficient-extraction
            reasoning step. The step's ``metadata['coefficients']`` is a
            structured ``(a, b, c)`` tuple and ``metadata['variable']`` names
            the unknown.

        Raises
        ------
        UnsupportedExpressionError
            If the expression is not a single-variable quadratic equation.
        """
        self._ensure_applicable(expression)
        variable = next(iter(expression.free_symbols))

        try:
            polynomial = Poly(expression.lhs - expression.rhs, variable)
        except Exception as exc:  # noqa: BLE001 - any non-polynomial body
            raise UnsupportedExpressionError(
                "The equation could not be reduced to a polynomial in a "
                "single variable."
            ) from exc
        if polynomial.degree() != 2:
            raise UnsupportedExpressionError(
                "ExtractQuadraticCoefficientsRule expects a quadratic "
                f"equation; got a polynomial of degree {polynomial.degree()}."
            )

        a = polynomial.coeff_monomial(variable**2)
        b = polynomial.coeff_monomial(variable)
        c = polynomial.coeff_monomial(variable**0)

        step = make_step(
            "Identify the quadratic coefficients",
            "Identify the quadratic coefficients.",
            latex(expression),
            "extract_coefficients",
        )
        step.metadata["coefficients"] = (a, b, c)
        step.metadata["variable"] = variable
        return expression, step


__all__ = ["ExtractQuadraticCoefficientsRule"]