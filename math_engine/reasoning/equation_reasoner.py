"""Concrete reasoner for linear equations.

Implements the first concrete reasoning module: :class:`EquationReasoner`
turns a solved equation into an educational, step-by-step explanation. Each
:class:`Step` represents one mathematical transformation, generated
deterministically with SymPy — no LLM text and no free-form prose.

Only simple linear equations in one variable are supported; anything else is
rejected with :class:`ReasoningGenerationError`.
"""

from __future__ import annotations

from sympy import Eq, Equality, Poly, Symbol, latex, simplify

from ..models import Expression, Solution, Step, TaskType
from .base_reasoner import BaseReasoner
from .reasoning_exceptions import ReasoningGenerationError
from .reasoning_factory import default_reasoner_factory


@default_reasoner_factory.register
class EquationReasoner(BaseReasoner):
    """Reasoner that explains solutions to linear equations.

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
        return tuple(self._generate_linear_steps(equation, solution.expression))

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

    def _generate_linear_steps(
        self, equation: Equality, expression: Expression
    ) -> list[Step]:
        """Build reasoning steps for a univariate linear equation.

        Parameters
        ----------
        equation :
            The equality to explain.
        expression :
            The original expression, used for the opening step.

        Returns
        -------
        list[Step]
            The generated reasoning steps.

        Raises
        ------
        ReasoningGenerationError
            If the equality is not a single-variable linear equation.
        """
        symbol = self._free_symbol(equation)
        coefficient, constant = self._linear_components(equation, symbol)
        lhs_constant = simplify(equation.lhs - coefficient * symbol)
        rhs = simplify(-constant)
        value = simplify(rhs / coefficient)

        original_latex = expression.raw_latex or latex(equation)
        steps: list[Step] = []
        steps.append(
            self._create_step(
                "Present the equation",
                f"Solve the linear equation {original_latex}.",
                latex(equation),
                "present",
            )
        )
        if lhs_constant != 0:
            steps.append(
                self._create_step(
                    "Isolate the variable term",
                    f"Move the constant term {latex(lhs_constant)} to the "
                    "right-hand side, applying the opposite operation to "
                    "both sides.",
                    latex(Eq(coefficient * symbol, rhs)),
                    "isolate",
                )
            )
        if coefficient != 1:
            steps.append(
                self._create_step(
                    "Simplify the coefficient",
                    "Divide both sides by the coefficient of the variable "
                    "to leave the variable alone on the left.",
                    latex(Eq(symbol, value)),
                    "divide",
                )
            )
        final_latex = latex(Eq(symbol, value))
        steps.append(
            self._create_step(
                "Final answer",
                f"The solution of the equation is {final_latex}.",
                final_latex,
                "answer",
            )
        )
        return steps

    def _free_symbol(self, equation: Equality) -> Symbol:
        """Return the single free symbol of the equation.

        Parameters
        ----------
        equation :
            The equality to inspect.

        Returns
        -------
        Symbol
            The equation's only free symbol.

        Raises
        ------
        ReasoningGenerationError
            If the equation has not exactly one free symbol.
        """
        free_symbols = equation.free_symbols
        if len(free_symbols) != 1:
            raise ReasoningGenerationError(
                "EquationReasoner only supports a single variable; "
                f"found {len(free_symbols)}."
            )
        return next(iter(free_symbols))

    def _linear_components(
        self, equation: Equality, symbol: Symbol
    ) -> tuple[object, object]:
        """Decompose an equality into ``(coefficient, constant)`` form.

        Expresses ``lhs - rhs`` as ``coefficient * symbol + constant`` using a
        SymPy polynomial and returns the two components.

        Parameters
        ----------
        equation :
            The equality to decompose.
        symbol :
            The variable to solve for.

        Returns
        -------
        tuple[object, object]
            The coefficient of the variable and the constant remainder.

        Raises
        ------
        ReasoningGenerationError
            If the equation is constant or has degree greater than one.
        """
        polynomial = Poly(equation.lhs - equation.rhs, symbol)
        if polynomial.is_zero or polynomial.degree() > 1:
            raise ReasoningGenerationError(
                "EquationReasoner only supports linear equations; "
                f"got polynomial of degree {polynomial.degree()}."
            )
        coefficient = polynomial.coeff_monomial(symbol)
        constant = polynomial.coeff_monomial(1)
        if coefficient == 0:
            raise ReasoningGenerationError(
                "EquationReasoner only supports equations with a nonzero "
                "variable coefficient."
            )
        return coefficient, constant

    def _create_step(
        self, title: str, description: str, step_latex: str, kind: str
    ) -> Step:
        """Build a reasoning step with explanatory metadata.

        Parameters
        ----------
        title :
            A short heading for the step.
        description :
            A human-readable explanation of the transformation.
        step_latex :
            The LaTeX rendered result of the step.
        kind :
            A machine-readable label identifying the step's purpose.

        Returns
        -------
        Step
            The constructed reasoning step.
        """
        return Step(
            title=title,
            description=description,
            latex=step_latex,
            metadata={"kind": kind},
        )