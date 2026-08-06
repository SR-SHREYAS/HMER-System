"""Concrete solver for quadratic equations.

:class:`QuadraticSolver` solves quadratic equations in two stages. It first
applies the :class:`NormalizeQuadraticRule` to rearrange the equation into the
standard quadratic form ``ax**2 + bx + c = 0``, then applies the
:class:`ExtractQuadraticCoefficientsRule` to read the coefficients ``a``, ``b``
and ``c`` off the normalized form, then applies the
:class:`ComputeDiscriminantRule` to calculate ``Delta = b**2 - 4*a*c``.
Discriminant calculation is the extent of the current phase: roots are not
classified and the equation is not solved yet. The solver registers against the
process-wide factory under the :class:`TaskType.QUADRATIC_EQUATION` task.
"""

from __future__ import annotations

from sympy import Basic, latex

from ..models import Expression, Solution, TaskType
from ..reasoning.rules import (
    ComputeDiscriminantRule,
    ExtractQuadraticCoefficientsRule,
    NormalizeQuadraticRule,
)
from .base_solver import BaseSolver
from .solver_factory import default_factory


@default_factory.register
class QuadraticSolver(BaseSolver):
    """Solver for quadratic equations.

    Given a classified ``QUADRATIC_EQUATION`` expression, normalizes the
    equation into the standard form ``ax**2 + bx + c = 0`` via SymPy, extracts
    the quadratic coefficients from that form, computes the discriminant
    ``Delta = b**2 - 4*a*c``, and returns a :class:`Solution` carrying the
    accompanying reasoning steps and the normalized equation as its current
    answer. The extracted coefficients and the computed discriminant are stored
    in the solution metadata for the pipeline phases that follow.
    """

    task_type = TaskType.QUADRATIC_EQUATION

    def solve(self, problem: Expression) -> Solution:
        """Normalize, extract coefficients and compute the discriminant.

        Parameters
        ----------
        problem :
            The classified quadratic equation expression to solve.

        Returns
        -------
        Solution
            A solution whose steps explain the normalization, the coefficient
            extraction and the discriminant calculation, whose ``final_answer``
            holds the normalized equation, and whose metadata carries the
            extracted coefficients and the computed discriminant for subsequent
            phases.

        Raises
        ------
        SolverError
            If the equation cannot be reduced to a polynomial in one variable.
        """
        expr = self._extract_expression(problem)
        normalized, normalize_step = NormalizeQuadraticRule().apply(expr)
        _, extract_step = ExtractQuadraticCoefficientsRule().apply(normalized)
        coefficients = extract_step.metadata["coefficients"]
        _, discriminant_step = ComputeDiscriminantRule().apply(coefficients)
        return Solution(
            expression=problem,
            steps=(normalize_step, extract_step, discriminant_step),
            final_answer=self._render(normalized),
            metadata={
                "normalized": normalized,
                "coefficients": coefficients,
                "variable": extract_step.metadata["variable"],
                "discriminant": discriminant_step.metadata["discriminant"],
            },
        )

    def _extract_expression(self, problem: Expression) -> Basic:
        """Return the SymPy expression from the model."""
        return problem.sympy_expression

    @staticmethod
    def _render(equation) -> str:
        """Render a normalized equation as a human-readable string."""
        return latex(equation)


__all__ = ["QuadraticSolver"]