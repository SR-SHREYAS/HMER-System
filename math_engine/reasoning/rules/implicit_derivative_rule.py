"""Rule that applies implicit differentiation to an equation.

:class:`ImplicitDerivativeRule` differentiates an equality that relates two
symbols (``x`` and ``y``) with respect to ``x``, treating ``y`` as a function
of ``x``. It moves everything to one side, differentiates with SymPy, solves
the resulting expression for ``Derivative(y, x)`` and returns the explicit
``dy/dx``.

The rule only applies when the expression is an :class:`~sympy.Eq` quoting both
the differentiation variable ``x`` and a further symbol ``y``. The result is
returned raw: nothing is simplified, and the equation itself is never modified.
"""

from __future__ import annotations

from sympy import Derivative, Eq, Function, Symbol, diff, latex, solve

from ...models import Step
from .base_rule import BaseRule, make_step
from .rule_exceptions import UnsupportedExpressionError


class ImplicitDerivativeRule(BaseRule):
    """Differentiate an equation implicitly with respect to its variable.

    Applies when the expression is an equality in ``x`` and ``y``. The rule
    forms ``lhs - rhs``, differentiates it w.r.t. ``x`` while treating ``y``
    as a function of ``x`` (so SymPy emits ``Derivative(y(x), x)``), solves
    the resulting equation for that derivative and returns the explicit
    ``dy/dx`` expression. The step it produces carries kind
    ``implicit_derivative``.

    Examples
    --------
    >>> from sympy import symbols, Eq
    >>> from math_engine.reasoning.rules import ImplicitDerivativeRule
    >>> x, y = symbols('x y')
    >>> rule = ImplicitDerivativeRule()
    >>> result, step = rule.apply({"expression": Eq(x**2 + y**2, 1), "variable": x})
    >>> step.metadata["kind"]
    'implicit_derivative'
    >>> result
    -x/y
    >>> step.metadata["equation"]
    Eq(x**2 + y**2, 1)
    >>> result, step = rule.apply({"expression": Eq(x * y, 1), "variable": x})
    >>> result
    -y/x
    >>> result, step = rule.apply(
    ...     {"expression": Eq(x**2 + x * y + y**2, 0), "variable": x}
    ... )
    >>> result
    (-2*x - y)/(x + 2*y)
    """

    def can_apply(self, structure) -> bool:
        """Return ``True`` when the expression is an equality between ``x`` and
        ``y``.
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        bool
            ``True`` when the expression is an equality between ``x`` and
            ``y``.
        """
        try:
            expression = structure["expression"]
            variable = structure["variable"]
        except (KeyError, TypeError):
            return False
        if not isinstance(expression, Eq):
            return False
        symbols = expression.free_symbols
        y_symbol = Symbol("y")
        return variable == Symbol("x") and y_symbol in symbols

    def apply(self, structure) -> tuple[object, Step]:
        """Return the implicit ``dy/dx`` alongside a reasoning step.

        Parameters
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        tuple[object, Step]
            The computed ``dy/dx`` and the ``implicit_derivative`` step.

        Raises
        ------
        UnsupportedExpressionError
            If the expression is not a two-variable equality or the implicit
            derivative cannot be isolated.
        """
        self._ensure_applicable(structure)
        equation = structure["expression"]
        variable = structure["variable"]
        y_symbol = Symbol("y")
        y_function = Function("y")(variable)

        expression = equation.lhs - equation.rhs
        expression = expression.xreplace({y_symbol: y_function})
        try:
            differentiated = diff(expression, variable)
            solution = solve(differentiated, Derivative(y_function, variable))
        except Exception as exc:  # noqa: BLE001 - propagate any diff/solve failure
            raise UnsupportedExpressionError(
                f"ImplicitDerivativeRule could not differentiate "
                f"{equation!r}: {exc}"
            ) from exc
        if not solution:
            raise UnsupportedExpressionError(
                f"ImplicitDerivativeRule could not isolate dy/dx from "
                f"{equation!r}."
            )
        result = solution[0]
        result = result.xreplace({y_function: y_symbol})

        # Educational content: show implicit differentiation process
        formula = "\\frac{dy}{dx} = -\\frac{\\partial F/\\partial x}{\\partial F/\\partial y} \\text{ where } F(x,y) = 0"
        
        # Show the differentiated equation
        differentiated_latex = latex(differentiated)
        equation_latex = latex(equation)
        
        substitution = (
            f"\\frac{{d}}{{d{latex(variable)}}} \\left({latex(equation.lhs)} - {latex(equation.rhs)}\\right) = 0 \\\\\n"
            f"{differentiated_latex} = 0 \\\\\n"
            f"\\frac{{dy}}{{dx}} = {latex(result)}"
        )
        evaluation = f"= {latex(result)}"

        step = make_step(
            "Apply implicit differentiation",
            f"Differentiate both sides of {latex(equation)} with respect to {latex(variable)}, "
            f"treating y as a function of x. Then solve for dy/dx.",
            "\\begin{aligned}\n"
            f"{formula} \\\\\n"
            f"{substitution} \\\\\n"
            f"{evaluation}\n"
            "\\end{aligned}",
            "implicit_derivative",
        )
        step.metadata["result"] = result
        step.metadata["equation"] = equation
        step.metadata["differentiated"] = differentiated
        return result, step


__all__ = ["ImplicitDerivativeRule"]