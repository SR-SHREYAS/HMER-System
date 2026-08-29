"""Rule that computes the discriminant of a quadratic equation.

:class:`ComputeDiscriminantRule` consumes the quadratic coefficients ``a``,
``b`` and ``c`` extracted by :class:`ExtractQuadraticCoefficientsRule` and
computes the discriminant ``Delta = b**2 - 4*a*c`` with SymPy. It never
classifies the roots, never applies the quadratic formula and never solves or
simplifies the equation. The discriminant is returned as structured metadata on
the accompanying reasoning step so that later pipeline phases can consume it.
"""

from __future__ import annotations

from sympy import Eq, latex

from ...models import Step
from .base_rule import BaseRule, make_step
from .rule_exceptions import UnsupportedExpressionError


class ComputeDiscriminantRule(BaseRule):
    """Compute ``b**2 - 4*a*c`` from the quadratic coefficients.

    The rule is driven purely by the structured coefficients metadata produced
    during the previous phase; it does not recompute coefficients from the
    equation.
    """

    def can_apply(self, coefficients) -> bool:
        """Return whether the given coefficient tuple yields a discriminant.

        The rule applies to any length-three coefficient tuple ``(a, b, c)``
        whose leading coefficient ``a`` is not zero (a genuine quadratic).

        Parameters
        ----------
        coefficients :
            The ``(a, b, c)`` coefficients extracted previously.

        Returns
        -------
        bool
            ``True`` when ``(a, b, c)`` is a valid quadratic coefficient set.
        """
        if not isinstance(coefficients, (tuple, list)) or len(coefficients) != 3:
            return False
        a = coefficients[0]
        return not (isinstance(a, (int, float)) and a == 0)

    def apply(self, coefficients) -> tuple[object, Step]:
        """Compute and return the quadratic discriminant.

        Calculates ``Delta = b**2 - 4*a*c`` via SymPy arithmetic. The original
        coefficients are returned unchanged alongside a reasoning step whose
        metadata carries the symbolic calculation and the result.

        Parameters
        ----------
        coefficients :
            The ``(a, b, c)`` quadratic coefficients extracted previously.

        Returns
        -------
        tuple[object, Step]
            The discriminant expression and its single reasoning step. The
            step's ``metadata['discriminant']`` holds the result and
            ``metadata['calculation']`` holds the symbolic form
            ``b**2 - 4*a*c``.

        Raises
        ------
        UnsupportedExpressionError
            If the coefficient set is not a valid quadratic ``(a, b, c)``.
        """
        self._ensure_applicable(coefficients)
        a, b, c = coefficients

        calculation = b**2 - 4 * a * c
        discriminant = calculation

        formula = "D &= b^{2} - 4ac"
        substitution = (
            f"D &= \\left({latex(b)}\\right)^{{2}} "
            f"- 4\\left({latex(a)}\\right)\\left({latex(c)}\\right)"
        )
        result = f"D &= {latex(discriminant)}"
        step = make_step(
            "Compute the discriminant",
            "Compute the discriminant using D = b\u00b2 - 4ac.",
            "\\begin{aligned}\n"
            + " \\\\\n".join((formula, substitution, result))
            + "\n\\end{aligned}",
            "compute_discriminant",
        )
        step.metadata["discriminant"] = discriminant
        step.metadata["calculation"] = latex(calculation)
        step.metadata["formula"] = formula.replace("&= ", "= ")
        step.metadata["substitution"] = substitution.replace("&= ", "= ")
        return discriminant, step


__all__ = ["ComputeDiscriminantRule"]