"""Concrete solver for equations.

Implements the first concrete mathematical solver: :class:`EquationSolver`
recognizes equality expressions and returns their solution set using SymPy.
It performs no step-by-step reasoning; intermediate steps are intentionally
left empty for future phases to fill.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from sympy import Add, Basic, Poly, expand, solve
from sympy.polys.polyerrors import PolynomialError

from ..models import Expression, Solution, TaskType
from .base_solver import BaseSolver
from .solver_exceptions import SolverError
from .solver_factory import default_factory


@default_factory.register
class EquationSolver(BaseSolver):
    """Solver for equations.

    Given a classified ``EQUATION`` expression, extracts the embedded SymPy
    equality, solves it symbolically, and returns a :class:`Solution` whose
    ``final_answer`` holds the rendered solution set.

    By default this solver registers itself against the process-wide
    :data:`default_factory` when the module is imported.
    """

    task_type = TaskType.EQUATION

    def solve(self, problem: Expression) -> Solution:
        """Solve an equation expression.

        Parameters
        ----------
        problem :
            The classified equation expression to solve.

        Returns
        -------
        Solution
            A solution with an empty ``steps`` tuple, the solved answer in
            ``final_answer``, and the raw SymPy result in ``metadata``.

        Raises
        ------
        SolverError
            If SymPy fails to solve the expression.
        """
        expr = self._extract_expression(problem)
        if self._polynomial_degree(expr) == 2:
            return self._route_quadratic(problem)
        result = self._solve_equation(expr)
        return Solution(
            expression=problem,
            steps=(),
            final_answer=self._render_result(result),
            metadata={"solutions": result},
        )

    def _extract_expression(self, problem: Expression) -> Basic:
        """Return the SymPy expression from the model.

        Parameters
        ----------
        problem :
            The expression container.

        Returns
        -------
        Basic
            The underlying SymPy object to solve.
        """
        return problem.sympy_expression

    def _polynomial_degree(self, expr: Basic) -> int | None:
        """Return the polynomial degree of the equation in its variable.

        The degree is computed with SymPy polynomial analysis by expanding
        ``lhs - rhs`` around the single free variable of the equation. Items
        that are not a single-variable polynomial (no variable, several
        variables, or a non-polynomial body) yield ``None``.

        Parameters
        ----------
        expr :
            The SymPy equality to inspect.

        Returns
        -------
        int | None
            The degree of the polynomial, or ``None`` when it is not a
            single-variable polynomial.
        """
        lhs = getattr(expr, "lhs", None)
        rhs = getattr(expr, "rhs", None)
        if lhs is None or rhs is None:
            return None

        symbols = expr.free_symbols
        if len(symbols) != 1:
            return None
        variable = next(iter(symbols))

        try:
            polynomial = Poly(self._flatten(expand(lhs - rhs)), variable)
        except (PolynomialError, ValueError, TypeError):
            return None
        return polynomial.degree()

    @staticmethod
    def _flatten(expr: Basic) -> Basic:
        """Canonicalize an expression by re-evaluating nested additions.

        The LaTeX parser produces unevaluated, nested :class:`Add` nodes that
        plain :func:`expand` does not re-evaluate; this rebuilds the additions
        so SymPy's polynomial machinery can analyse the equation.
        """
        if isinstance(expr, Add):
            return Add(*(EquationSolver._flatten(arg) for arg in expr.args))
        return expr

    def _route_quadratic(self, problem: Expression) -> Solution:
        """Route a quadratic equation to the registered quadratic solver.

        The quadratic solver is not implemented yet, so this raises
        :class:`SolverNotImplementedError` on its behalf.

        Parameters
        ----------
        problem :
            The expression to route.

        Returns
        -------
        Solution
            The solution produced by the quadratic solver.
        """
        quadratic = replace(problem, task=TaskType.QUADRATIC_EQUATION)
        solver = default_factory.build(quadratic)
        return solver.solve(quadratic)

    def _solve_equation(self, expr: Basic) -> Any:
        """Solve a SymPy equality symbolically.

        Parameters
        ----------
        expr :
            The SymPy object to solve.

        Returns
        -------
        Any
            SymPy's solution set (typically a list or a mapping).

        Raises
        ------
        SolverError
            If SymPy fails to solve the expression.
        """
        try:
            return solve(expr)
        except Exception as exc:  # noqa: BLE001 - propagate any solve failure
            raise SolverError(f"Failed to solve expression {expr!r}: {exc}") from exc

    def _render_result(self, result: Any) -> str:
        """Render a SymPy solution set as a human-readable string.

        Parameters
        ----------
        result :
            The raw solution value produced by SymPy.

        Returns
        -------
        str
            A compact, readable representation of the solutions.
        """
        if isinstance(result, dict):
            return ", ".join(
                f"{symbol} = {value}" for symbol, value in result.items()
            )
        if isinstance(result, (list, tuple)):
            return ", ".join(str(value) for value in result)
        return str(result)