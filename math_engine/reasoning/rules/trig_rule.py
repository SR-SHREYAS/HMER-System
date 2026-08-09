"""Rule that applies the trigonometric differentiation rules.

:class:`TrigRule` implements the derivatives of ``sin``, ``cos``, ``tan``,
``sec``, ``cot``, ``csc``, ``asin``, ``acos``, ``atan``, ``sinh``, ``cosh``
and ``tanh``:

.. math::

    \\frac{d}{dx} \\sin(u) = \\cos(u) \\cdot u'
    \\qquad
    \\frac{d}{dx} \\cos(u) = -\\sin(u) \\cdot u'
    \\qquad
    \\frac{d}{dx} \\tan(u) = \\sec(u)^2 \\cdot u'

    \\frac{d}{dx} \\sec(u) = \\sec(u) \\cdot \\tan(u) \\cdot u'
    \\qquad
    \\frac{d}{dx} \\cot(u) = -\\csc(u)^2 \\cdot u'
    \\qquad
    \\frac{d}{dx} \\csc(u) = -\\csc(u) \\cdot \\cot(u) \\cdot u'

    \\frac{d}{dx} \\arcsin(u) = \\frac{1}{\\sqrt{1 - u^2}} \\cdot u'
    \\qquad
    \\frac{d}{dx} \\arccos(u) = -\\frac{1}{\\sqrt{1 - u^2}} \\cdot u'
    \\qquad
    \\frac{d}{dx} \\arctan(u) = \\frac{1}{1 + u^2} \\cdot u'

    \\frac{d}{dx} \\sinh(u) = \\cosh(u) \\cdot u'
    \\qquad
    \\frac{d}{dx} \\cosh(u) = \\sinh(u) \\cdot u'
    \\qquad
    \\frac{d}{dx} \\tanh(u) = \\sech(u)^2 \\cdot u'

It reads the expression and variable from the structured metadata produced by
:class:`ExtractDerivativeStructureRule`. When the expression is ``sin(inner)``,
``cos(inner)``, ``tan(inner)``, ``sec(inner)``, ``cot(inner)``, ``csc(inner)``,
``asin(inner)``, ``acos(inner)``, ``atan(inner)``, ``sinh(inner)``,
``cosh(inner)`` or ``tanh(inner)`` the rule computes ``inner'`` by routing the
argument through the full rule pipeline the solver uses (implicit, constant,
power, sum, product, quotient, chain, trigonometric and exp/log rules) -- the
inner is never differentiated by hand and nested arguments are differentiated
recursively. The result ``trig'(inner) * inner'`` is returned raw: nothing is
simplified. The rule only applies when the inner can be differentiated by the
full pipeline; otherwise it leaves the expression unchanged.
"""

from __future__ import annotations

from sympy import Integer, Mul, acos, asin, atan, cos, cosh, cot, csc, latex, sec, sech, sin, sinh, sqrt, tan, tanh

from ...models import Step
from .base_rule import BaseRule, make_step
from .rule_exceptions import UnsupportedExpressionError


class TrigRule(BaseRule):
    """Evaluate the trigonometric, inverse trigonometric and hyperbolic
    derivatives ``(sin'(u)*u', cos'(u)*u', tan'(u)*u', sec'(u)*u', cot'(u)*u',
    csc'(u)*u', asin'(u)*u', acos'(u)*u', atan'(u)*u', sinh'(u)*u',
    cosh'(u)*u', tanh'(u)*u')``.

    Consumes the derivative structure metadata, differentiates the trig
    argument through the existing rules and returns the combined result
    together with a single trigonometric-rule step.

    Examples
    --------
    >>> from sympy import symbols, tan, sec, cot, csc, asin, acos, atan, sinh, cosh, tanh
    >>> from math_engine.reasoning.rules import TrigRule
    >>> x = symbols('x')
    >>> rule = TrigRule()
    >>> result, step = rule.apply({"expression": tan(x), "variable": x})
    >>> step.metadata["kind"]
    'trigonometric_rule'
    >>> step.metadata["function"]
    'tan'
    >>> result
    sec(x)**2*1
    >>> step.metadata["inner_derivative"]
    1
    >>> result, step = rule.apply({"expression": tan(x**2), "variable": x})
    >>> result
    (2*x)*sec(x**2)**2
    >>> result, step = rule.apply({"expression": tan(x + 1), "variable": x})
    >>> result
    (0 + 1)*sec(x + 1)**2
    >>> result, step = rule.apply({"expression": sec(x), "variable": x})
    >>> result
    (tan(x)*sec(x))*1
    >>> result, step = rule.apply({"expression": cot(x), "variable": x})
    >>> result
    -csc(x)**2*1
    >>> result, step = rule.apply({"expression": csc(x), "variable": x})
    >>> result
    -cot(x)*csc(x)*1
    >>> result, step = rule.apply({"expression": sec(x**2), "variable": x})
    >>> result
    (2*x)*(tan(x**2)*sec(x**2))
    >>> result, step = rule.apply({"expression": cot(x + 1), "variable": x})
    >>> result
    (0 + 1)*(-csc(x + 1)**2)
    >>> result, step = rule.apply({"expression": asin(x), "variable": x})
    >>> result
    1/sqrt(1 - x**2)
    >>> result, step = rule.apply({"expression": acos(x), "variable": x})
    >>> result
    -1/sqrt(1 - x**2)*1
    >>> result, step = rule.apply({"expression": atan(x), "variable": x})
    >>> result
    1/(x**2 + 1)
    >>> result, step = rule.apply({"expression": asin(x**2), "variable": x})
    >>> result
    (2*x)/sqrt(1 - x**4)
    >>> result, step = rule.apply({"expression": atan(x + 1), "variable": x})
    >>> result
    (0 + 1)/((x + 1)**2 + 1)
    >>> result, step = rule.apply({"expression": sinh(x), "variable": x})
    >>> result
    cosh(x)*1
    >>> result, step = rule.apply({"expression": cosh(x), "variable": x})
    >>> result
    sinh(x)*1
    >>> result, step = rule.apply({"expression": tanh(x), "variable": x})
    >>> result
    sech(x)**2*1
    >>> result, step = rule.apply({"expression": sinh(x**2), "variable": x})
    >>> result
    (2*x)*cosh(x**2)
    >>> result, step = rule.apply({"expression": tanh(x + 1), "variable": x})
    >>> result
    (0 + 1)*sech(x + 1)**2
    """

    def can_apply(self, structure) -> bool:
        """Return whether the expression is a supported trig function.

        The expression is a candidate when it is exactly ``sin(inner)``,
        ``cos(inner)``, ``tan(inner)``, ``sec(inner)``, ``cot(inner)``,
        ``csc(inner)``, ``asin(inner)``, ``acos(inner)``, ``atan(inner)``,
        ``sinh(inner)``, ``cosh(inner)`` or ``tanh(inner)`` whose inner can
        be differentiated by the existing rules.

        Parameters
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        bool
            ``True`` when the expression is a supported trig function.
        """
        try:
            expression = structure["expression"]
            variable = structure["variable"]
        except (KeyError, TypeError):
            return False
        inner = TrigRule._inner(expression)
        if inner is None:
            return False
        return TrigRule._differentiable(inner, variable)

    def apply(self, structure) -> tuple[object, Step]:
        """Return the trigonometric derivative result.

        Parameters
        ----------
        structure :
            The metadata mapping with ``expression`` and ``variable`` keys.

        Returns
        -------
        tuple[object, Step]
            The combined derivative ``(trig'(inner) * inner', step)``. The step
            is titled "Differentiate using trigonometric rule" and carries kind
            ``trigonometric_rule``.

        Raises
        ------
        UnsupportedExpressionError
            If the expression is not a supported trig function.
        """
        self._ensure_applicable(structure)
        expression = structure["expression"]
        variable = structure["variable"]

        inner = TrigRule._inner(expression)
        inner_prime = TrigRule._differentiate(inner, variable)
        function = expression.func
        if function is sin:
            outer_prime = cos(inner)
        elif function is cos:
            outer_prime = Mul(Integer(-1), sin(inner), evaluate=False)
        elif function is tan:
            outer_prime = sec(inner) ** 2
        elif function is sec:
            outer_prime = Mul(sec(inner), tan(inner), evaluate=False)
        elif function is cot:
            outer_prime = Mul(Integer(-1), csc(inner) ** 2, evaluate=False)
        elif function is csc:
            outer_prime = Mul(
                Integer(-1),
                Mul(csc(inner), cot(inner), evaluate=False),
                evaluate=False,
            )
        elif function is asin:
            outer_prime = 1 / sqrt(1 - inner**2)
        elif function is acos:
            outer_prime = Mul(Integer(-1), 1 / sqrt(1 - inner**2), evaluate=False)
        elif function is atan:
            outer_prime = 1 / (1 + inner**2)
        elif function is sinh:
            outer_prime = cosh(inner)
        elif function is cosh:
            outer_prime = sinh(inner)
        elif function is tanh:
            outer_prime = sech(inner) ** 2
        else:
            raise UnsupportedExpressionError(
                "TrigRule only supports sin, cos, tan, sec, cot, csc, "
                "asin, acos, atan, sinh, cosh and tanh."
            )

        result = Mul(outer_prime, inner_prime, evaluate=False)
        if function in (tan, asin, acos, atan, sinh, cosh, tanh):
            description = "Apply trigonometric differentiation rule."
        else:
            description = "Differentiate using trigonometric rule."
        step = make_step(
            "Differentiate using trigonometric rule",
            description,
            latex(result),
            "trigonometric_rule",
        )
        step.metadata["function"] = function.__name__
        step.metadata["inner"] = inner
        step.metadata["inner_derivative"] = inner_prime
        step.metadata["result"] = result
        return result, step

    @staticmethod
    def _inner(expression):
        """Return the argument of a supported trig function or ``None``."""
        if expression.func is sin and len(expression.args) == 1:
            return expression.args[0]
        if expression.func is cos and len(expression.args) == 1:
            return expression.args[0]
        if expression.func is tan and len(expression.args) == 1:
            return expression.args[0]
        if expression.func is sec and len(expression.args) == 1:
            return expression.args[0]
        if expression.func is cot and len(expression.args) == 1:
            return expression.args[0]
        if expression.func is csc and len(expression.args) == 1:
            return expression.args[0]
        if expression.func is asin and len(expression.args) == 1:
            return expression.args[0]
        if expression.func is acos and len(expression.args) == 1:
            return expression.args[0]
        if expression.func is atan and len(expression.args) == 1:
            return expression.args[0]
        if expression.func is sinh and len(expression.args) == 1:
            return expression.args[0]
        if expression.func is cosh and len(expression.args) == 1:
            return expression.args[0]
        if expression.func is tanh and len(expression.args) == 1:
            return expression.args[0]
        return None

    @staticmethod
    def _differentiable(expression, variable) -> bool:
        """Return whether an inner can be differentiated by the full pipeline."""
        from ...solver.derivative_solver import DerivativeSolver

        result, _ = DerivativeSolver._solve_single(expression, variable)
        return result is not None

    @staticmethod
    def _differentiate(expression, variable):
        """Differentiate an inner through the full rule pipeline.

        The argument is routed through the same ordered chain the solver
        uses -- implicit, constant, power, sum, product, quotient, chain,
        trigonometric and exp/log -- so nested arguments of any composition
        are differentiated recursively, not by hand.
        """
        from ...solver.derivative_solver import DerivativeSolver

        result, _ = DerivativeSolver._solve_single(expression, variable)
        if result is None:
            raise UnsupportedExpressionError(
                f"TrigRule cannot differentiate the inner function "
                f"{expression!r}."
            )
        return result


__all__ = ["TrigRule"]