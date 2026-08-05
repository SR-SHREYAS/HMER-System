"""Concrete reasoner for linear equations.

:class:`EquationReasoner` is now a pure orchestrator: it validates that it
received an equality expression, drives a :class:`RuleEngine` over it, and
wraps the produced steps with the opening "present the equation" and closing
"final answer" steps. All mathematical transformations live inside the rules in
:mod:`math_engine.reasoning.rules`.

Each :class:`Step` is generated deterministically with SymPy — no LLM text and
no free-form prose. Only simple linear equations in one variable are supported;
anything else is rejected with :class:`ReasoningGenerationError`.
"""

from __future__ import annotations

from sympy import Eq, Equality, latex

from ..models import Expression, Solution, Step, TaskType
from .base_reasoner import BaseReasoner
from .reasoning_exceptions import ReasoningGenerationError
from .reasoning_factory import default_reasoner_factory
from .rules.base_rule import _single_symbol, make_step
from .rules.divide_coefficient_rule import DivideCoefficientRule
from .rules.expand_rule import ExpandRule
from .rules.move_constant_rule import MoveConstantRule
from .rules.move_variable_rule import MoveVariableRule
from .rules.rule_engine import RuleEngine
from .rules.rule_exceptions import RuleError


@default_reasoner_factory.register
class EquationReasoner(BaseReasoner):
    """Reasoner that explains solutions to linear equations.

    The reasoner owns the reasoning workflow but not the mathematics: it
    registers the two initial rules with a :class:`RuleEngine` and executes
    them over the equation, then bookends the resulting steps with the opening
    and final answer.

    By default this reasoner registers itself against the process-wide
    :data:`default_reasoner_factory` when the module is imported.
    """

    task_type = TaskType.EQUATION

    def generate(self, solution: Solution) -> tuple[Step, ...]:
        """Generate reasoning steps for a solved linear equation.

        Parameters
        ----------
        solution :
            A completed solution whose expression is a classified equation.

        Returns
        -------
        tuple[Step, ...]
            The ordered reasoning steps for the equation.

        Raises
        ------
        ReasoningGenerationError
            If the expression is not a supported linear equation.
        """
        equation = self._extract_equation(solution.expression)
        return self._generate_steps(equation, solution.expression)

    def _extract_equation(self, expression: Expression) -> Equality:
        """Return the SymPy equality from an expression.

        Parameters
        ----------
        expression :
            The expression whose SymPy form should be an equality.

        Returns
        -------
        Equality
            The underlying symmetric equality.

        Raises
        ------
        ReasoningGenerationError
            If the expression is not an equality.
        """
        expr = expression.sympy_expression
        if not isinstance(expr, Equality):
            raise ReasoningGenerationError(
                "EquationReasoner expects an equality expression, "
                f"got {type(expr).__name__}."
            )
        return expr

    def _generate_steps(
        self, equation: Equality, expression: Expression
    ) -> tuple[Step, ...]:
        """Drive the rule engine and wrap the generated steps.

        Parameters
        ----------
        equation :
            The equality to explain.
        expression :
            The original expression, used for the opening step.

        Returns
        -------
        tuple[Step, ...]
            The opening step, the steps produced by the rule engine, and the
            final answer step.

        Raises
        ------
        ReasoningGenerationError
            If the rule engine cannot reason about the equation.
        """
        engine = RuleEngine(
            [
                ExpandRule(),
                MoveVariableRule(),
                MoveConstantRule(),
                DivideCoefficientRule(),
            ]
        )
        try:
            generated = engine.run(equation)
        except RuleError as exc:
            raise ReasoningGenerationError(str(exc)) from exc

        original_latex = expression.raw_latex or latex(equation)
        steps: list[Step] = [
            make_step(
                "Present the equation",
                f"Solve the linear equation {original_latex}.",
                latex(equation),
                "present",
            )
        ]
        steps.extend(generated)

        symbol = _single_symbol(engine.final_expression)
        final_latex = latex(Eq(symbol, engine.final_expression.rhs))
        steps.append(
            make_step(
                "Final answer",
                f"The solution of the equation is {final_latex}.",
                final_latex,
                "answer",
            )
        )
        return tuple(steps)