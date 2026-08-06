"""Rule that simplifies the roots of a quadratic equation.

:class:`SimplifyQuadraticRootsRule` reads the raw symbolic roots computed by
:class:`QuadraticFormulaRule` and simplifies each one with SymPy's
:func:`simplify` (which internally applies ``cancel``, ``together``, and
related utilities). Exact symbolic values are preserved and no floating-point
conversion or manual radical manipulation happens. The simplified roots replace
the raw roots in the reasoning-step metadata.
"""

from __future__ import annotations

from sympy import Basic, latex, simplify

from ...models import Step
from .base_rule import BaseRule, make_step
from .rule_exceptions import UnsupportedExpressionError


class SimplifyQuadraticRootsRule(BaseRule):
    """Simplify the symbolic roots without changing their mathematical meaning.

    Consumes the raw roots and returns a ``(simplified_roots, step)`` pair.
    """

    def can_apply(self, roots) -> bool:
        """Return whether ``roots`` is a non-empty iterable of SymPy values.

        Parameters
        ----------
        roots :
            The raw symbolic roots computed by the quadratic formula.

        Returns
        -------
        bool
            ``True`` when ``roots`` is a sequence of two values.
        """
        return isinstance(roots, (tuple, list)) and len(roots) == 2

    def apply(self, roots) -> tuple[tuple[Basic, Basic], Step]:
        """Simplify each root and expose the result in structured metadata.

        Parameters
        ----------
        roots :
            The raw ``(root_1, root_2)`` symbolic roots from the formula step.

        Returns
        -------
        tuple[tuple[Basic, Basic], Step]
            The tuple of simplified roots and a reasoning step whose metadata
            carries the simplified roots. Step metadata:
            ``roots`` -- the simplified SymPy roots.

        Raises
        ------
        UnsupportedExpressionError
            If ``roots`` is not a pair of values.
        """
        self._ensure_applicable(roots)
        root_plus, root_minus = roots

        simplified_plus = simplify(root_plus)
        simplified_minus = simplify(root_minus)

        step = make_step(
            "Simplify the resulting roots",
            "Simplify the resulting roots.",
            "",
            "simplify_roots",
        )
        step.metadata["roots"] = (simplified_plus, simplified_minus)
        return (simplified_plus, simplified_minus), step


__all__ = ["SimplifyQuadraticRootsRule"]