"""Concrete solver for quadratic equations.

:class:`QuadraticSolver` solves quadratic equations in two stages. It first
applies the :class:`NormalizeQuadraticRule` to rearrange the equation into the
standard quadratic form ``ax**2 + bx + c = 0``, then applies the
:class:`ExtractQuadraticCoefficientsRule` to read the coefficients ``a``, ``b``
and ``c`` off the normalized form. Extraction is the extent of the current
phase: the discriminant is not computed, roots are not classified and the
equation is not solved yet. The solver registers against the process-wide
factory under the :class:`TaskType.QUADRATIC_EQUATION` task.
"""

from __future__ import annotations

from sympy import Basic, latex

from ..models import Expression, Solution, TaskType
from ..reasoning.rules import (
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
    the quadratic coefficients from that form, and returns a :class:`Solution`
    carrying the accompanying reasoning steps and the normalized equation as
    its current answer. The extracted coefficients are stored in the solution
    metadata for the pipeline phases that follow.
    """

    task_type = TaskType.QUADRATIC_EQUATION

    def solve(self, problem: Expression) -> Solution:
        """Normalize and extract coefficients of a quadratic expression.

        Parameters
        ----------
        problem :
            The classified quadratic equation expression to solve.

        Returns
        -------
        Solution
            A solution whose steps explain the normalization and the
            coefficient extraction, whose ``final_answer`` holds the
            normalized equation, and whose metadata carries the extracted
            coefficients for subsequent phases.

        Raises
        ------
        SolverError
            If the equation cannot be reduced to a polynomial in one variable.
        """
        expr = self._extract_expression(problem)
        normalized, normalize_step = NormalizeQuadraticRule().apply(expr)
        _, extract_step = ExtractQuadraticCoefficientsRule().apply(normalized)
        return Solution(
            expression=problem,
            steps=(normalize_step, extract_step),
            final_answer=self._render(normalized),
            metadata={
                "normalized": normalized,
                "coefficients": extract_step.metadata["coefficients"],
                "variable": extract_step.metadata["variable"],
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