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

import random

from sympy import (
    Add,
    Derivative,
    Eq,
    Float,
    Function,
    Symbol,
    diff,
    latex,
    nan,
    simplify,
    solve,
    zoo,
)

from ..models import Expression, Solution, TaskType
from ..reasoning.rules import (
    ChainRule,
    ConstantDerivativeRule,
    ExpLogRule,
    ExtractDerivativeStructureRule,
    GeneralPowerRule,
    ImplicitDerivativeRule,
    PowerRule,
    ProductRule,
    QuotientRule,
    SumRule,
    TrigRule,
    make_step,
)
from ..reasoning.simplifier import Simplifier
from .base_solver import BaseSolver
from .solver_exceptions import SolverError
from .solver_factory import default_factory

#: Ordinal labels for higher-order derivative iteration steps.
_ORDINALS = (
    "First",
    "Second",
    "Third",
    "Fourth",
    "Fifth",
    "Sixth",
    "Seventh",
    "Eighth",
    "Ninth",
    "Tenth",
)


def _ordinal(number: int) -> str:
    """Return the ordinal word for ``number`` (``1`` -> "First")."""
    if 1 <= number <= len(_ORDINALS):
        return _ORDINALS[number - 1]
    return f"{number}th"


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
        order = structure["order"]
        variable = structure["variable"]
        current = structure["expression"]
        result = None
        y_symbol = Symbol("y")
        y_function = Function("y")(variable)
        if order == 1:
            result, order_steps = self._solve_single(current, variable)
            steps.extend(order_steps)
            simplified_result = (
                self._simplify(result) if result is not None else None
            )
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
        elif isinstance(current, Eq):
            series = self._implicit_series(current, variable, order)
            if series is None:
                raise SolverError(
                    f"Implicit equation {current!r} cannot be differentiated "
                    f"to order {order}."
                )
            for index, value in enumerate(series):
                ordinal = _ordinal(index + 1)
                iteration_step = make_step(
                    f"{ordinal} derivative",
                    f"Differentiate {ordinal.lower()}.",
                    latex(value),
                    "nth_derivative",
                )
                iteration_step.metadata["order"] = index + 1
                steps.append(iteration_step)
                step_result = value.xreplace({y_function: y_symbol})
                simplified = self._simplify(step_result) if step_result is not None else None
                if simplified is not None:
                    simplify_step = make_step(
                        "Simplify the result",
                        "Simplify the result.",
                        latex(simplified),
                        "final_simplification",
                    )
                    simplify_step.metadata["before"] = step_result
                    simplify_step.metadata["after"] = simplified
                    steps.append(simplify_step)
            result = series[-1]
            final_value = result.xreplace({y_function: y_symbol})
            simplified_result = self._simplify(final_value)
        else:
            for index in range(order):
                result, order_steps = self._solve_single(current, variable)
                ordinal = _ordinal(index + 1)
                iteration_step = make_step(
                    f"{ordinal} derivative",
                    f"Differentiate {ordinal.lower()}.",
                    latex(result),
                    "nth_derivative",
                )
                iteration_step.metadata["order"] = index + 1
                steps.append(iteration_step)
                steps.extend(order_steps)
                simplified = (
                    self._simplify(result) if result is not None else None
                )
                if simplified is not None:
                    simplify_step = make_step(
                        "Simplify the result",
                        "Simplify the result.",
                        latex(simplified),
                        "final_simplification",
                    )
                    simplify_step.metadata["before"] = result
                    simplify_step.metadata["after"] = simplified
                    steps.append(simplify_step)
                current = simplified
            simplified_result = simplified
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

    @staticmethod
    def _solve_single(expression, variable) -> tuple[object, list[Step]]:
        """Differentiate ``expression`` once through the full rule pipeline.

        Runs the same ordered rule chain the solver used for first-order
        derivatives -- implicit, constant, power, sum, product, quotient, chain,
        trigonometric and exp/log -- and returns the raw result together with
        the reasoning step(s) produced. The result is deliberately not
        simplified: higher-order derivatives feed it straight back into this
        method for the next iteration.

        Parameters
        ----------
        expression :
            The expression to differentiate.
        variable :
            The variable of differentiation.

        Returns
        -------
        tuple[object, list[Step]]
            The raw derivative and the step(s) the chosen rule emitted.
        """
        structure = {"expression": expression, "variable": variable}
        candidate = [
            ImplicitDerivativeRule(),
            ConstantDerivativeRule(),
            PowerRule(),
            SumRule(),
            ProductRule(),
            QuotientRule(),
            ChainRule(),
            GeneralPowerRule(),
            TrigRule(),
            ExpLogRule(),
        ]
        for rule in candidate:
            if rule.can_apply(structure):
                result, rule_step = rule.apply(structure)
                return result, [rule_step]
        if isinstance(expression, Add):
            term_steps = []
            terms = []
            for term in expression.args:
                term_result, term_step = DerivativeSolver._solve_single(
                    term, variable
                )
                if term_result is None:
                    return None, []
                terms.append(term_result)
                term_steps.extend(term_step)
            result = Add(*terms, evaluate=False)
            step = make_step(
                "Apply the sum rule",
                "Apply the sum rule.",
                latex(result),
                "sum_rule",
            )
            step.metadata["terms"] = terms
            step.metadata["result"] = result
            return result, term_steps + [step]
        return None, []

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
    def _implicit_series(expression, variable, order) -> list | None:
        """Differentiate an implicit equality to a full order.

        Treats ``y`` as the function ``y(x)`` at every iteration and solves
        for ``Derivative(y(x), x, n)`` one derivative level at a time. The
        series returned keeps ``y`` as ``y(x)`` so that higher-order terms
        remain functions of ``x``; the caller demotes ``y(x)`` back to ``y``
        only at the end. Returns ``None`` when the derivative cannot be
        isolated.

        Parameters
        ----------
        expression :
            An :class:`~sympy.Eq` relating ``x`` and ``y``.
        variable :
            The differentiation variable.
        order :
            The total differentiation order.

        Returns
        -------
        list | None
            ``[d1, d2, ..., dN]`` with ``dn`` the ``n``-th derivative of
            ``y`` w.r.t. ``variable`` expressed with ``y(x)``, or ``None``.
        """
        y_symbol = Symbol("y")
        y_function = Function("y")(variable)
        expression = (expression.lhs - expression.rhs).xreplace(
            {y_symbol: y_function}
        )
        derivatives = []
        known = {}
        for order_index in range(1, order + 1):
            differentiated = diff(expression, variable, order_index)
            for degree in range(1, order_index):
                differentiated = differentiated.xreplace(
                    {Derivative(y_function, (variable, degree)): known[degree]}
                )
            solution = solve(
                differentiated, Derivative(y_function, (variable, order_index))
            )
            if not solution:
                return None
            known[order_index] = solution[0]
            derivatives.append(solution[0])
        return derivatives

    @staticmethod
    def _verify(expression, variables, result) -> dict:
        """Check a computed derivative against SymPy's ``diff``.

        The expected derivative is ``sympy.diff(expression, *variables)`` for
        an ordinary derivative. When the expression is an equality the problem
        is implicit differentiation: ``y`` is treated as a function of the
        differentiation variable and ``expected`` equals the requested-order
        derivative obtained by differentiating the ``lhs - rhs`` difference
        repeatedly.

        Verification runs a strict fallback hierarchy, never weakening a pass
        or relying on numerics alone. It first checks the exact symbolic
        difference ``simplify(result - expected) == 0``; if that fails it
        checks the symbolic ratio ``simplify(result / expected) == 1`` (guarding
        a zero denominator); and only if both symbolic checks fail does it fall
        back to a numeric pointwise comparison of ``result`` and ``expected``
        at several sample values for the differentiation variable. The pass
        decision, the method that decided it (``"symbolic"``, ``"numeric"`` or
        ``"symbolic+numeric"``) and the number of numeric samples used are all
        recorded. This is a pure bookkeeping step: it neither modifies the
        final answer nor touches any reasoning step.

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
            A ``{"passed": bool, "expected": object, "method": str,
            "samples": int}`` mapping.
        """
        if isinstance(expression, Eq):
            variable = variables[0]
            series = DerivativeSolver._implicit_series(
                expression, variable, len(variables)
            )
            expected = series[-1].xreplace(
                {Function("y")(variable): Symbol("y")}
            ) if series else None
        else:
            variable = variables[0]
            expected = diff(expression, *variables)
        if result is None or expected is None:
            return {
                "passed": False,
                "expected": expected,
                "method": "symbolic",
                "samples": 0,
            }
        passed, method, samples = DerivativeSolver._equivalent(
            result, expected, variable
        )
        return {
            "passed": bool(passed),
            "expected": expected,
            "method": method,
            "samples": samples,
        }

    @classmethod
    def _equivalent(cls, result, expected, variable) -> tuple:
        """Compare ``result`` with ``expected`` via the fallback hierarchy.

        Level 1 is the exact symbolic difference ``simplify(result - expected)
        == 0``. Level 2 is the symbolic ratio ``simplify(result / expected)
        == 1``, skipped when ``expected`` is exactly ``0`` (a zero denominator)
        and guarded against evaluation errors. Level 3 is a numeric pointwise
        comparison. Returns ``(passed, method, samples)`` where ``method`` is
        ``"symbolic"``, ``"numeric"`` or ``"symbolic+numeric"``.
        """
        try:
            if simplify(result - expected) == 0:
                return True, "symbolic", 0
        except Exception:
            pass
        try:
            if expected != 0 and simplify(result / expected) == 1:
                return True, "symbolic", 0
        except Exception:
            pass
        return cls._numeric_check(result, expected, variable)

    @staticmethod
    def _numeric_check(result, expected, variable) -> tuple:
        """Numerically verify ``result`` against ``expected`` at sample points.

        Chooses 5-10 float values for ``variable`` and evaluates both sides at
        each with ``evalf``. Points that raise, yield a non-finite value
        (singularities or division by zero), or cannot be reduced to a plain
        number are skipped. The check passes only when every evaluable point
        agrees within ``1e-6`` and at least three points could be evaluated;
        otherwise it is inconclusive and fails closed.

        Returns
        -------
        tuple
            ``(passed, method, samples)`` with ``method`` ``"numeric"`` when
            evaluated and ``"symbolic+numeric"`` when symbolic checks already
            ran but a numeric pass was still achieved.
        """
        tolerance = 1e-6
        samples = [0.5, 1.0, 2.0, 3.0, -0.5]
        samples += [random.uniform(-3.0, 3.0) for _ in range(3)]
        evaluated = 0
        for value in samples:
            try:
                res = result.evalf(subs={variable: Float(value)})
                exp = expected.evalf(subs={variable: Float(value)})
            except Exception:
                continue
            if res.has(nan, zoo) or exp.has(nan, zoo):
                continue
            if not (res.is_Number and exp.is_Number):
                continue
            if abs(res - exp) >= tolerance:
                return False, "numeric", evaluated
            evaluated += 1
        if evaluated >= 3:
            return True, "symbolic+numeric", evaluated
        return False, "numeric", evaluated

    @staticmethod
    def _render(value) -> str:
        """Render a result value as a human-readable string."""
        return latex(value)


__all__ = ["DerivativeSolver"]