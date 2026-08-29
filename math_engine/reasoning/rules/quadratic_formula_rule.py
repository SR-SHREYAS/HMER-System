"""Rule that applies the quadratic formula.

:class:`QuadraticFormulaRule` computes the symbolic roots of a quadratic
equation with the quadratic formula

.. math::

    x = \\frac{-b \\pm \\sqrt{\\Delta}}{2a}

using :func:`sympy.sqrt` for the discriminant ``Delta``. It reads the
coefficients ``a`` and ``b`` and the discriminant ``Delta`` from the structured
metadata produced by the earlier pipeline phases and never recomputes them.
The raw symbolic roots are stored in the step metadata. The rule does not
simplify radicals manually, does not classify roots, does not merge repeated
roots and does not decide presentation or produce a final formatted answer.
"""

from __future__ import annotations

from sympy import latex, sqrt

from ...models import Step
from .base_rule import BaseRule, make_step
from .rule_exceptions import UnsupportedExpressionError


class QuadraticFormulaRule(BaseRule):
    """Compute the symbolic roots ``(-b ± sqrt(Delta)) / (2a)``.

    Consumes ``a``, ``b`` and ``Delta`` provided through ``apply`` and returns
    the two raw symbolic roots as structured metadata.
    """

    def can_apply(self, values) -> bool:
        """Return whether the value bundle supplies a usable coefficient set.

        Parameters
        ----------
        values :
            A mapping carrying ``'a'``, ``'b'`` and ``'discriminant'``.

        Returns
        -------
        bool
            ``True`` when a usable ``(a, b, discriminant)`` is present.
        """
        try:
            a = self._read(values, "a")
            discriminant = self._read(values, "discriminant")
        except (KeyError, TypeError):
            return False
        try:
            return bool(a != 0 and discriminant == discriminant)
        except Exception:  # noqa: BLE001 - non-comparable inputs
            return False

    def apply(self, values) -> tuple[object, Step]:
        """Return the discriminant unchanged with a quadratic-formula step.

        Parameters
        ----------
        values :
            A mapping carrying ``'a'``, ``'b'`` and ``'discriminant'``.

        Returns
        -------
        tuple[object, Step]
            The input bundle unchanged, and a reasoning step whose metadata
            carries the two symbolic roots and the raw formula expression.

        Raises
        ------
        UnsupportedExpressionError
            If the coefficient set is not a valid quadratic (``a != 0``).
        """
        self._ensure_applicable(values)
        a = self._read(values, "a")
        b = self._read(values, "b")
        discriminant = self._read(values, "discriminant")

        root_plus = (-b + sqrt(discriminant)) / (2 * a)
        root_minus = (-b - sqrt(discriminant)) / (2 * a)

        formula = "x &= \\frac{-b \\pm \\sqrt{D}}{2a}"
        substitution = (
            f"x &= \\frac{{-\\left({latex(b)}\\right) "
            f"\\pm \\sqrt{{{latex(discriminant)}}}}}{{2\\left({latex(a)}\\right)}}"
        )
        evaluation = (
            f"x &= \\frac{{{latex(-b)} \\pm {latex(sqrt(discriminant))}}}"
            f"{{{latex(2 * a)}}}"
        )
        step = make_step(
            "Apply the quadratic formula",
            "Apply the quadratic formula.",
            "\\begin{aligned}\n"
            + " \\\\\n".join((formula, substitution, evaluation))
            + "\n\\end{aligned}",
            "quadratic_formula",
        )
        step.metadata["roots"] = (root_plus, root_minus)
        step.metadata["roots_latex"] = (latex(root_plus), latex(root_minus))
        step.metadata["formula"] = formula.replace("&= ", "= ")
        step.metadata["substitution"] = substitution.replace("&= ", "= ")
        step.metadata["evaluation"] = evaluation.replace("&= ", "= ")
        return discriminant, step

    @staticmethod
    def _read(values, key):
        """Extract a named coefficient from a mapping."""
        if isinstance(values, dict):
            return values[key]
        if isinstance(values, (tuple, list)) and len(values) == 3:
            order = {"a": 0, "b": 1, "c": 2}
            if key == "discriminant":
                raise KeyError("discriminant is not part of a coefficient tuple")
            return values[order[key]]
        raise KeyError(key)


__all__ = ["QuadraticFormulaRule"]