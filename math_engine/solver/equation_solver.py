"""Concrete solver for equations.

:class:`EquationSolver` recognizes equality expressions and returns their
solution set using SymPy. For simple linear equations in one variable it also
runs the shared rule pipeline (expand, multiply-through, move variable terms,
move constants, divide the coefficient) so the canonical ``/solve`` path
produces step-by-step reasoning exactly like the quadratic and derivative
solvers do. The authoritative ``final_answer`` still comes from SymPy's
``solve``; the rules only add the explanatory steps.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from sympy import Add, Basic, Eq, Poly, expand, latex, solve
from sympy.polys.polyerrors import PolynomialError

from ..models import Expression, Solution, Step, TaskType
from ..reasoning.rules import (
    DivideCoefficientRule,
    ExpandRule,
    MoveConstantRule,
    MoveVariableRule,
    MultiplyBothSidesRule,
    RuleEngine,
    UnsupportedExpressionError,
)
from ..reasoning.rules.base_rule import _single_symbol, make_step
from ..reasoning.rules.rule_exceptions import RuleError
from .base_solver import BaseSolver
from .solver_exceptions import SolverError
from .solver_factory import default_factory


@default_factory.register
class EquationSolver(BaseSolver):
    """Solver for equations.

    Given a classified ``EQUATION`` expression, extracts the embedded SymPy
    equality, solves it symbolically, and returns a :class:`Solution` whose
    ``final_answer`` holds the rendered solution set. Linear equations are
    additionally explained step by step through the shared rule pipeline.

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
            A solution with the solved answer in ``final_answer``, the raw
            SymPy result in ``metadata``, and step-by-step reasoning for
            supported linear equations.

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
            steps=self._linear_steps(problem, expr),
            final_answer=self._render_result(result),
            metadata={"solutions": result},
        )

    def _linear_steps(self, problem: Expression, expr: Basic) -> tuple[Step, ...]:
        """Build step-by-step reasoning for a supported linear equation.

        Runs the same ordered rule pipeline the reasoning layer uses for
        linear equations and bookends the produced steps with the opening
        "present the equation" step and the closing "final answer" step.

        Equations that are not a simple single-variable linear equation return
        an empty tuple, preserving the historical no-steps behaviour.

        Parameters
        ----------
        problem :
            The expression being solved, used for the opening step.
        expr :
            The SymPy equality to explain.

        Returns
        -------
        tuple[Step, ...]
            The ordered reasoning steps, or an empty tuple when the equation
            is outside the linear rule pipeline's scope.
        """
        engine = RuleEngine(
            [
                ExpandRule(),
                MultiplyBothSidesRule(),
                MoveVariableRule(),
                MoveConstantRule(),
                DivideCoefficientRule(),
            ]
        )
        try:
            generated = engine.run(expr)
        except RuleError:
            return ()

        original_latex = problem.raw_latex or latex(expr)
        steps: list[Step] = [
            make_step(
                "Present the equation",
                f"Solve the linear equation {original_latex}.",
                latex(expr),
                "present",
            )
        ]
        steps.extend(generated)

        try:
            symbol = _single_symbol(engine.final_expression)
            final_latex = latex(Eq(symbol, engine.final_expression.rhs))
        except (UnsupportedExpressionError, AttributeError):
            return tuple(steps)
        steps.append(
            make_step(
                "Final answer",
                f"The solution of the equation is {final_latex}.",
                final_latex,
                "answer",
            )
        )
        return tuple(steps)

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