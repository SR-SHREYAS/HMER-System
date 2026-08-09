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

from sympy import Derivative, Integer, diff, latex, simplify

from ..models import Expression, Solution, TaskType
from ..reasoning.rules import (
    ChainRule,
    ConstantDerivativeRule,
    ExtractDerivativeStructureRule,
    PowerRule,
    ProductRule,
    QuotientRule,
    SumRule,
    make_step,
)
from ..reasoning.simplifier import Simplifier
from .base_solver import BaseSolver
from .solver_factory import default_factory


@default_factory.register
class DerivativeSolver(BaseSolver):
    """Solver for derivative expressions.

    Given a classified ``DERIVATIVE`` expression, extracts the structure of the
    SymPy derivative (expression, variable, order) and applies the constant rule
    when the expression is constant, the power rule when the expression is a
    power of the variable, the sum rule when the expression is a supported
    top-level addition, and the product rule when the expression is a supported
    top-level product. The returned :class:`Solution` carries the reasoning
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
            applicable, the constant, power, sum and/or product rules.
            ``final_answer`` holds the result when a rule applied and is empty
            otherwise. Metadata carries the structure and the result.

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
        result = None
        if ConstantDerivativeRule().can_apply(structure):
            result, constant_step = ConstantDerivativeRule().apply(structure)
            steps.append(constant_step)
        elif PowerRule().can_apply(structure):
            result, power_step = PowerRule().apply(structure)
            steps.append(power_step)
        elif SumRule().can_apply(structure):
            result, sum_step = SumRule().apply(structure)
            steps.append(sum_step)
        elif ProductRule().can_apply(structure):
            result, product_step = ProductRule().apply(structure)
            steps.append(product_step)
        elif QuotientRule().can_apply(structure):
            result, quotient_step = QuotientRule().apply(structure)
            steps.append(quotient_step)
        elif ChainRule().can_apply(structure):
            result, chain_step = ChainRule().apply(structure)
            steps.append(chain_step)
        simplified_result = self._simplify(result) if result is not None else None
        if simplified_result is not None:
            final_step = make_step(
                "Simplify the result",
                "Simplify the result.",
                latex(simplified_result),
                "final_simplification",
            )
            final_step.metadata["before"] = result
            final_step.metadata["after"] = simplified_result
            steps.append(final_step)
        final_answer = self._render(simplified_result) if simplified_result is not None else ""
        verification = self._verify(
            structure["expression"], structure["variables"], simplified_result
        )
        return Solution(
            expression=problem,
            steps=tuple(steps),
            final_answer=final_answer,
            metadata={
                **structure,
                "result": result,
                "simplified_result": simplified_result,
                "verification": verification,
            },
        )

    def _extract_expression(self, problem: Expression) -> Derivative:
        """Return the SymPy derivative from the model."""
        return problem.sympy_expression

    @staticmethod
    def _simplify(value):
        """Compute a clean human-readable form of a result value.

        Only the minimal, predictable rewrites of :class:`Simplifier` are
        applied, and only after all reasoning steps have been produced, so the
        steps themselves stay untouched.
        """
        return Simplifier().simplify(value)

    @staticmethod
    def _verify(expression, variables, result) -> dict:
        """Check a computed derivative against SymPy's ``diff``.

        The expected derivative is ``sympy.diff(expression, *variables)`` and
        the result passes when ``simplify(result - expected) == 0``. This is a
        pure bookkeeping step: it neither modifies the final answer nor touches
        any reasoning step.

        Parameters
        ----------
        expression :
            The sub-expression being differentiated.
        variables :
            The differentiation variables (includes repeats for higher order).
        result :
            The computed (simplified) derivative, or ``None`` when no rule
            applied.

        Returns
        -------
        dict
            A ``{"passed": bool, "expected": object}`` mapping.
        """
        expected = diff(expression, *variables)
        if result is None:
            passed = False
        else:
            passed = simplify(result - expected) == 0
        return {"passed": bool(passed), "expected": expected}

    @staticmethod
    def _render(value) -> str:
        """Render a result value as a human-readable string."""
        return latex(value)


__all__ = ["DerivativeSolver"]