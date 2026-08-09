"""Concrete solver for derivative expressions.

:class:`DerivativeSolver` solves derivative expressions in stages. In the
current phase it applies the :class:`ExtractDerivativeStructureRule` to read
the structure of a SymPy :class:`~sympy.Derivative` object -- the sub-expression
being differentiated, the variable(s) of differentiation and the order -- and
returns a :class:`Solution` carrying the reasoning step and that structure in
its metadata. The derivative itself is not computed yet. The solver registers
against the process-wide factory under the :class:`TaskType.DERIVATIVE` task.
"""

from __future__ import annotations

from sympy import Derivative, Integer, latex

from ..models import Expression, Solution, TaskType
from ..reasoning.rules import (
    ConstantDerivativeRule,
    ExtractDerivativeStructureRule,
    PowerRule,
    SumRule,
)
from .base_solver import BaseSolver
from .solver_factory import default_factory


@default_factory.register
class DerivativeSolver(BaseSolver):
    """Solver for derivative expressions.

    Given a classified ``DERIVATIVE`` expression, extracts the structure of the
    SymPy derivative (expression, variable, order) and applies the constant rule
    when the expression is constant, the power rule when the expression is a
    power of the variable, and the sum rule when the expression is a supported
    top-level addition. The returned :class:`Solution` carries the reasoning
    steps and any result so far; other expression forms are not differentiated
    yet.
    """

    task_type = TaskType.DERIVATIVE

    def solve(self, problem: Expression) -> Solution:
        """Extract structure and apply the applicable differentiation rules.

        Parameters
        ----------
        problem :
            The classified derivative expression.

        Returns
        -------
        Solution
            A solution whose steps explain the structure extraction and, when
            applicable, the constant and/or power rules. ``final_answer`` holds
            the result when a rule applied and is empty otherwise. Metadata
            carries the structure and the result.

        Raises
        ------
        SolverError
            If the expression is not a SymPy derivative.
        """
        expr = self._extract_expression(problem)
        _, step = ExtractDerivativeStructureRule().apply(expr)
        structure = {
            "expression": step.metadata["expression"],
            "variables": step.metadata["variables"],
            "variable": step.metadata["variable"],
            "order": step.metadata["order"],
        }

        steps = [step]
        final_answer = ""
        result = None
        if ConstantDerivativeRule().can_apply(structure):
            result, constant_step = ConstantDerivativeRule().apply(structure)
            steps.append(constant_step)
            final_answer = self._render(result)
        elif PowerRule().can_apply(structure):
            result, power_step = PowerRule().apply(structure)
            steps.append(power_step)
            final_answer = self._render(result)
        elif SumRule().can_apply(structure):
            result, sum_step = SumRule().apply(structure)
            steps.append(sum_step)
            final_answer = self._render(result)
        return Solution(
            expression=problem,
            steps=tuple(steps),
            final_answer=final_answer,
            metadata={
                **structure,
                "result": result,
            },
        )

    def _extract_expression(self, problem: Expression) -> Derivative:
        """Return the SymPy derivative from the model."""
        return problem.sympy_expression

    @staticmethod
    def _render(value) -> str:
        """Render a result value as a human-readable string."""
        return latex(value)


__all__ = ["DerivativeSolver"]