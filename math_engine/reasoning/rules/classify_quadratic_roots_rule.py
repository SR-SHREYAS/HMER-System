"""Rule that classifies the roots of a quadratic equation.

:class:`ClassifyQuadraticRootsRule` reads the discriminant ``Delta`` computed
by :class:`ComputeDiscriminantRule` and determines how the roots of the
equation behave:

* ``Delta > 0`` -- two distinct real roots,
* ``Delta == 0`` -- one repeated real root,
* ``Delta < 0`` -- two complex roots.

It never solves the equation, never applies the quadratic formula and never
generates answers. The classification is returned as structured metadata on the
accompanying reasoning step.
"""

from __future__ import annotations

from sympy import latex

from ...models import Step
from .base_rule import BaseRule, make_step
from .rule_exceptions import UnsupportedExpressionError


class ClassifyQuadraticRootsRule(BaseRule):
    """Classify roots based on the sign of the discriminant.

    The rule consumes the computed discriminant through its ``apply`` argument
    and never recomputes it.
    """

    def can_apply(self, discriminant) -> bool:
        """Return whether the given discriminant is a scalar that can be compared.

        Parameters
        ----------
        discriminant :
            The already-computed discriminant value.

        Returns
        -------
        bool
            ``True`` when the discriminant is a real scalar.
        """
        try:
            return discriminant == discriminant  # reject non-comparable (reflexive)
        except Exception:  # noqa: BLE001 - non-comparable input
            return False

    def apply(self, discriminant) -> tuple[object, Step]:
        """Return the discriminant unchanged with a root-classification step.

        Parameters
        ----------
        discriminant :
            The already-computed discriminant value.

        Returns
        ------
        tuple[object, Step]
            The unchanged discriminant and a reasoning step whose metadata
            carries the classification.

        Raises
        ------
        UnsupportedExpressionError
            If the discriminant is not a comparable real scalar.
        """
        self._ensure_applicable(discriminant)

        if discriminant > 0:
            count = "exactly two distinct real roots"
            tag = "two_distinct_real"
            preposition = "positive"
            relation = f"D = {latex(discriminant)} > 0"
        elif discriminant == 0:
            count = "exactly one repeated real root"
            tag = "one_repeated_real"
            preposition = "zero"
            relation = "D = 0"
        else:
            count = "exactly two complex (non-real) roots"
            tag = "two_complex"
            preposition = "negative"
            relation = f"D = {latex(discriminant)} < 0"

        cases_latex = (
            "D > 0 \\Rightarrow \\text{two distinct real roots}\\\\\n"
            "D = 0 \\Rightarrow \\text{one repeated real root}\\\\\n"
            "D < 0 \\Rightarrow \\text{two complex roots}"
        )
        connection_latex = f"{relation} \\Rightarrow \\text{{{count}}}"
        description = (
            "The discriminant classifies the roots: "
            "D > 0 \u2192 two distinct real roots; "
            "D = 0 \u2192 one repeated real root; "
            "D < 0 \u2192 two complex (non-real) roots. "
            f"Here {relation}, therefore the equation has {count}."
        )
        step = make_step(
            "Classify the roots",
            description,
            "\\begin{gathered}\n"
            + cases_latex
            + " \\\\\n"
            + connection_latex
            + "\n\\end{gathered}",
            "classify_roots",
        )
        step.metadata["classification"] = tag
        step.metadata["root_count"] = count
        step.metadata["relation"] = relation
        return discriminant, step


__all__ = ["ClassifyQuadraticRootsRule"]