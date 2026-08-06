"""Concrete solver for quadratic equations.

:class:`QuadraticSolver` solves quadratic equations by applying the
:class:`NormalizeQuadraticRule` to rearrange the equation into the standard
quadratic form ``ax**2 + bx + c = 0``. The normalization is the extent of the
current phase: coefficients are not extracted and the equation is not solved
yet. The solver registers against the process-wide factory under the
:class:`TaskType.QUADRATIC_EQUATION` task.
"""

from __future__ import annotations

from sympy import Basic, latex

from ..models import Expression, Solution, TaskType
from ..reasoning.rules import NormalizeQuadraticRule
from .base_solver import BaseSolver
from .solver_factory import default_factory


@default_factory.register
class QuadraticSolver(BaseSolver):
    """Solver for quadratic equations.

    Given a classified ``QUADRATIC_EQUATION`` expression, normalizes the
    equation into the standard form ``ax**2 + bx + c = 0`` via SymPy and
    returns a :class:`Solution` carrying the accompanying reasoning step and
    the normalized equation as its current answer.
    """

    task_type = TaskType.QUADRATIC_EQUATION

    def solve(self, problem: Expression) -> Solution:
        """Normalize a quadratic equation expression.

        Parameters
        ----------
        problem :
            The classified quadratic equation expression to solve.

        Returns
        -------
        Solution
            A solution whose single step explains the normalization and whose
            ``final_answer`` holds the normalized equation.

        Raises
        ------
        SolverError
            If the equation cannot be reduced to a polynomial in one variable.
        """
        expr = self._extract_expression(problem)
        normalized, step = NormalizeQuadraticRule().apply(expr)
        return Solution(
            expression=problem,
            steps=(step,),
            final_answer=self._render(normalized),
            metadata={"normalized": normalized},
        )

    def _extract_expression(self, problem: Expression) -> Basic:
        """Return the SymPy expression from the model."""
        return problem.sympy_expression

    @staticmethod
    def _render(equation) -> str:
        """Render a normalized equation as a human-readable string."""
        return latex(equation)
