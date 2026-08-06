"""Concrete solver for quadratic equations.

:class:`QuadraticSolver` is the placeholder for the quadratic-equation phase of
the equation capability. It declares the :class:`TaskType` it will eventually
handle and registers against the process-wide factory, but it does not yet
implement any quadratic mathematics: calling :meth:`QuadraticSolver.solve`
raises the solver layer's standard "not implemented" exception.
"""

from __future__ import annotations

from ..models import Expression, Solution, TaskType
from .base_solver import BaseSolver
from .solver_exceptions import SolverNotImplementedError
from .solver_factory import default_factory


@default_factory.register
class QuadraticSolver(BaseSolver):
    """Placeholder solver for quadratic equations.

    Quadratic equations are routed here by :class:`EquationSolver` once their
    polynomial degree has been detected as two. The solving mathematics is not
    implemented in this phase, so :meth:`solve` raises
    :class:`SolverNotImplementedError`.
    """

    task_type = TaskType.QUADRATIC_EQUATION

    def solve(self, problem: Expression) -> Solution:
        """Solve a quadratic equation expression.

        Parameters
        ----------
        problem :
            The classified quadratic equation expression to solve.

        Returns
        -------
        Solution
            The complete solution produced by the solver.

        Raises
        ------
        SolverNotImplementedError
            Always; quadratic solving is not implemented yet.
        """
        raise SolverNotImplementedError(
            "Solving quadratic equations is not implemented yet."
        )
