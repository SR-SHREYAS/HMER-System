"""Universal algebraic transformations.

This module provides universal algebraic transformations that can be applied
across different mathematical domains (linear, quadratic, calculus, etc.).

These transformations implement universal algebraic principles that are
valid across different mathematical domains. They are designed to be
composable and reusable across different solvers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from sympy import (
    Add, Mul, Pow, Eq, Ne, Ge, Gt, Le, Lt,
    expand, simplify, solve, latex, symbols, Symbol, Eq as SymEq
)

from math_engine.models import Step
from .base import (
    Transformation,
    TransformationResult,
    Branch,
    BranchSet,
    Condition,
    Reversibility,
    VerificationRequirement,
    TransformationError,
    Condition,
    DomainRestriction,
    Branch,
    BranchSet,
)

# Re-export commonly used types
__all__ = [
    "AddSubtractBothSides",
    "MultiplyDivideBothSides",
    "DistributiveLaw",
    "SquareRootTransformation",
    "SquareBothSides",
    "ZeroProductProperty",
    "AlgebraicTransformation",
]


class AlgebraicTransformation(Transformation):
    """Base class for algebraic transformations.

    Algebraic transformations are universal algebraic operations that can be
    applied across different mathematical domains.
    """

    def can_apply(self, expression) -> bool:
        """Check if this transformation can be applied to the given expression.

        Args:
            expression: The expression to check (typically a SymPy Eq).

        Returns:
            True if this transformation can be applied, False otherwise.
        """
        from sympy import Eq
        return isinstance(expression, Eq)


def _has_minus_sign(expr) -> bool:
    """Return True when ``expr`` has a syntactic leading minus sign.

    Unlike ``expr.is_negative`` (which is ``None``/undecidable for symbolic
    quantities), this inspects the structure to detect an explicit leading
    negative factor (e.g. ``-2*x``, ``-1/2``, ``-4``).
    """
    if expr.is_number:
        return bool(expr < 0)
    try:
        return bool(expr.could_extract_minus_sign())
    except Exception:  # noqa: BLE001 - fall back to unevaluated sign check
        coeff, _ = expr.as_coeff_Mul()
        return coeff.is_negative is True


class AddSubtractBothSides(Transformation):
    """Add a signed quantity to both sides of an equation: ``A = B  ⇒  A + q = B + q``.

    This is the single universal primitive underlying "move a term to the other
    side": to eliminate a term ``t`` one adds ``-t`` to both sides. ``q`` may be
    any symbolic expression; a negative ``q`` corresponds to subtraction. This
    operation is fully reversible (an injective/equivalence-preserving step) and
    requires no verification.
    """

    name = "add_subtract_both_sides"
    description = "Add a signed quantity q to both sides: A = B ==> A + q = B + q"
    reversibility = "reversible"
    verification_required = "none"
    extraneous_risk = False

    def can_apply(self, expression) -> bool:
        from sympy import Eq
        return isinstance(expression, Eq)

    def apply(self, expression, amount=0) -> "TransformationResult":
        """Add ``amount`` to both sides of ``expression``.

        Args:
            expression: The equation (SymPy ``Eq``).
            amount: The quantity to add to both sides (may be negative).

        Returns:
            TransformationResult with the transformed equation and step.
        """
        from sympy import Eq, latex, sympify

        if not self.can_apply(expression):
            raise TransformationError("Expression must be an equation")

        # Accept plain Python numbers (int/float) as well as SymPy objects.
        amount = sympify(amount)

        if simplify(amount) == 0:
            raise TransformationError("Adding zero has no effect")

        new_lhs = simplify(expression.lhs + amount)
        new_rhs = simplify(expression.rhs + amount)
        transformed = Eq(new_lhs, new_rhs)

        # Educational description reflects the actual (signed) operation. We
        # detect the leading minus sign syntactically (rather than via
        # ``.is_negative``, which is undecidable for symbolic amounts) so the
        # rendered step shows ``- |amount|`` instead of a confusing ``+ - ...``.
        if _has_minus_sign(amount):
            op_latex = f"- {latex(-amount)}"
            desc = f"Subtract {latex(-amount)} from both sides"
            operation = "subtract"
        else:
            op_latex = f"+ {latex(amount)}"
            desc = f"Add {latex(amount)} to both sides"
            operation = "add"

        step_latex = (
            "\\begin{aligned}\n"
            f"{latex(expression)} \\\\\n"
            f"{op_latex} \\\\\n"
            f"{latex(transformed)}\n"
            "\\end{aligned}"
        )

        step = Step(
            title="Add or subtract the same quantity from both sides",
            description=f"{desc} to preserve equality.",
            latex=step_latex,
            metadata={"kind": "add_subtract_both_sides", "operation": operation,
                      "amount": amount},
        )

        return TransformationResult(
            original_expression=expression,
            transformed_expression=transformed,
            step=step,
            branches=(),
            conditions=(),
            domain_restrictions=(),
            reversibility=Reversibility.REVERSIBLE.value,
            verification_required=VerificationRequirement.NONE.value,
            extraneous_risk=False,
            metadata={"amount": amount, "operation": operation},
        )


class MultiplyDivideBothSides(Transformation):
    """Multiply or divide both sides of an equation by a non-zero expression.

    This transformation clears fractions by multiplying both sides by the
    least common denominator, or divides both sides by a non-zero coefficient.
    """

    name = "multiply_divide_both_sides"
    description = "Multiply or divide both sides by the same non-zero quantity"
    reversibility = "conditional"
    verification_required = "recommended"
    extraneous_risk = False

    def can_apply(self, expression) -> bool:
        from sympy import Eq
        return isinstance(expression, Eq)

    def apply(self, expression, factor) -> "TransformationResult":
        from sympy import Eq, Mul, latex, simplify

        if not self.can_apply(expression):
            raise TransformationError("Expression must be an equation")

        if factor == 0:
            raise TransformationError("Cannot multiply or divide by zero")

        new_lhs = simplify(expression.lhs * factor)
        new_rhs = simplify(expression.rhs * factor)
        transformed = Eq(new_lhs, new_rhs)

        if factor == 1:
            raise TransformationError("Multiplying by 1 has no effect")

        op_symbol = "\\times" if factor != 1 else "\\div"
        factor_latex = latex(factor)

        step_latex = (
            "\\begin{aligned}\n"
            f"{latex(expression)} \\\\\n"
            f"\\times {factor_latex} \\\\\n"
            f"{latex(Eq(new_lhs, new_rhs))}\n"
            "\\end{aligned}"
        )

        step = Step(
            title="Multiply both sides",
            description=f"Multiply both sides by {factor_latex} to eliminate fractions.",
            latex=step_latex,
            metadata={"kind": "multiply_both_sides", "factor": factor},
        )

        return TransformationResult(
            original_expression=expression,
            transformed_expression=transformed,
            step=step,
            branches=(),
            conditions=(Condition(expression=Ne(factor, 0), description=f"{factor} ≠ 0"),),
            reversibility="conditional",
            verification_required="recommended",
            extraneous_risk=False,
        )


class DistributiveLaw(Transformation):
    """Apply the distributive law to expand products over sums.

    This transformation expands expressions of the form a(b + c) into
    ab + ac, removing parentheses.
    """

    name = "distributive_law"
    description = "Apply the distributive law to expand parentheses"
    reversibility = "conditional"
    verification_required = "none"
    extraneous_risk = False

    def can_apply(self, expression) -> bool:
        from sympy import Mul, Add
        return isinstance(expression, Mul) and any(isinstance(arg, Add) for arg in expression.args)

    def apply(self, expression) -> "TransformationResult":
        from sympy import expand, latex

        expanded = expand(expression)

        if expanded == expression:
            raise TransformationError("Expression is already expanded")

        step_latex = (
            "\\begin{aligned}\n"
            f"{latex(expression)} \\\\\n"
            f"{latex(expanded)}\n"
            "\\end{aligned}"
        )

        step = Step(
            title="Expand brackets",
            description="Distribute the multiplier across each term inside the parentheses using the distributive law: a(b + c) = ab + ac.",
            latex=step_latex,
            metadata={"kind": "expand", "rule": "distributive_law"},
        )

        return TransformationResult(
            original_expression=expression,
            transformed_expression=expanded,
            step=Step(
                title="Expand brackets",
                description="Distribute the multiplier across each term inside the parentheses using the distributive law: a(b + c) = ab + ac.",
                latex=step_latex,
                metadata={"kind": "expand", "rule": "distributive_law"},
            ),
            branches=(),
            conditions=(),
            reversibility="conditional",
            verification_required="none",
            extraneous_risk=False,
        )


def _squared_side(eq):
    """Return ``(base, value)`` where one side is ``base**2`` and the other is ``value``.

    Handles both orientations: ``f(x)**2 = g(x)`` and ``g(x) = f(x)**2``.
    Returns ``(None, None)`` when neither side is a square.
    """
    lhs, rhs = eq.lhs, eq.rhs
    if isinstance(lhs, Pow) and lhs.exp == 2:
        return lhs.base, rhs
    if isinstance(rhs, Pow) and rhs.exp == 2:
        return rhs.base, lhs
    return None, None


class SquareRootTransformation(Transformation):
    """Apply the square-root property: ``f(x)² = g(x)  ⇒  f(x) = ±√g(x)``.

    This transformation produces two branches and must never collapse them into
    a single result. The base being squared may be any expression ``f(x)`` (not
    only a bare symbol); the radicand may be symbolic.

    The transformation exposes ``branches`` via the Phase 35.1 ``Branch`` model
    and is marked ``branch_producing`` with ``verification_required="required"``.
    """

    name = "square_root_property"
    description = "Apply the square root property: f(x)^2 = g(x) -> f(x) = ±sqrt(g(x))"
    reversibility = "branch_producing"
    verification_required = "required"
    extraneous_risk = True

    def can_apply(self, expression) -> bool:
        if not isinstance(expression, Eq):
            return False
        base, value = _squared_side(expression)
        if base is None:
            return False
        # The non-squared side must not itself contain the squared base
        # (avoids e.g. x^2 = x^2 which is not a meaningful square-root step).
        return not value.has(base)

    def apply(self, expression) -> "TransformationResult":
        from sympy import Eq, sqrt, latex, Ge, Integer

        if not self.can_apply(expression):
            raise TransformationError(
                "SquareRootTransformation requires an equation "
                "f(x)^2 = g(x) (one side an exact square)."
            )

        base, value = _squared_side(expression)

        pos_root = sqrt(value)
        neg_root = -sqrt(value)

        # Branch count: x^2 = 0 collapses ±0 to a single branch.
        if simplify(value) == 0:
            branch_equations = (Eq(base, Integer(0)),)
        else:
            branch_equations = (Eq(base, pos_root), Eq(base, neg_root))

        branches = tuple(
            Branch(expression=eq, description=latex(eq))
            for eq in branch_equations
        )

        sign_latex = latex(base)
        sqrt_latex = latex(sqrt(value))
        step_latex = (
            "\\begin{aligned}\n"
            f"{latex(expression)} \\\\\n"
            f"{sign_latex} = \\pm \\sqrt{{{latex(value)}}} \\\\\n"
            f"{sign_latex} = {sqrt_latex} \\quad \\text{{or}} \\quad "
            f"{sign_latex} = -{sqrt_latex}\n"
            "\\end{aligned}"
        )

        step = Step(
            title="Apply the square-root property",
            description=(
                f"Take the square root of both sides of {latex(expression)}. "
                f"Since squaring is not injective, {latex(base)} may be either "
                f"{latex(pos_root)} or {latex(neg_root)}."
            ),
            latex=step_latex,
            metadata={"kind": "square_root", "branches": len(branches)},
        )

        # A real-valued domain restriction is attached only when the radicand
        # is a negative number *and* we intend to restrict to real solutions.
        # Since this transformation keeps the (±) branch structure and lets
        # SymPy yield complex values for negative radicands (e.g. x² = -1
        # → x = ±i), we do NOT fabricate a real-root condition here. The
        # branches themselves already carry the mathematically correct result.
        conditions = ()

        return TransformationResult(
            original_expression=expression,
            transformed_expression=Eq(base, pos_root),
            step=step,
            branches=branches,
            conditions=conditions,
            domain_restrictions=(),
            reversibility=Reversibility.BRANCH_PRODUCING.value,
            verification_required=VerificationRequirement.REQUIRED.value,
            extraneous_risk=True,
            metadata={"radicand": value, "base": base},
        )


class ZeroProductProperty(Transformation):
    """Apply the zero-product property: ``A·B = 0  ⇒  A = 0 or B = 0``.

    This transformation is inherently branch-producing: one branch per factor
    of the product on the left-hand side. It operates on the mathematical
    structure (a top-level ``Mul`` equal to zero) and does not assume the
    factors are linear or the variable is named ``x``.
    """

    name = "zero_product_property"
    description = "Apply the zero-product property: A*B = 0 -> A = 0 or B = 0"
    reversibility = "branch_producing"
    verification_required = "none"
    extraneous_risk = False

    def can_apply(self, expression) -> bool:
        if not isinstance(expression, Eq):
            return False
        return isinstance(expression.lhs, Mul) and expression.rhs == 0

    def apply(self, expression) -> "TransformationResult":
        from sympy import Eq, Mul, latex

        if not self.can_apply(expression):
            raise TransformationError(
                "ZeroProductProperty requires an equation of the form "
                "A * B = 0 (a product equal to zero)."
            )

        factors = expression.lhs.args

        branches = tuple(
            Branch(expression=Eq(factor, 0), description=f"{latex(factor)} = 0")
            for factor in factors
        )

        factor_latex = r"\quad\text{or}\quad".join(
            f"{latex(f)} = 0" for f in factors
        )
        step_latex = (
            "\\begin{aligned}\n"
            f"{latex(expression)} \\\\\n"
            f"{factor_latex}\n"
            "\\end{aligned}"
        )

        step = Step(
            title="Apply the zero-product property",
            description=(
                f"If the product equals zero, at least one factor must be zero: "
                f"{factor_latex}."
            ),
            latex=step_latex,
            metadata={"kind": "zero_product", "branches": len(branches)},
        )

        return TransformationResult(
            original_expression=expression,
            transformed_expression=expression,
            step=step,
            branches=branches,
            conditions=(),
            domain_restrictions=(),
            reversibility=Reversibility.BRANCH_PRODUCING.value,
            verification_required=VerificationRequirement.NONE.value,
            extraneous_risk=False,
            metadata={"factors": factors},
        )


class SquareBothSides(Transformation):
    """Square both sides of an equation: ``A = B  ⇒  A² = B²``.

    Squaring is not an injective operation, so the resulting equation may admit
    solutions that do not satisfy the original equation (extraneous roots).
    This transformation therefore:

    * does NOT produce branches,
    * is marked ``irreversible``,
    * sets ``verification_required="required"``,
    * sets ``extraneous_risk=True``,

    so downstream solvers know to verify each candidate against the original
    equation before accepting it.
    """

    name = "square_both_sides"
    description = "Square both sides of an equation (may introduce extraneous solutions)"
    reversibility = "irreversible"
    verification_required = "required"
    extraneous_risk = True

    def can_apply(self, expression) -> bool:
        return isinstance(expression, Eq)

    def apply(self, expression) -> "TransformationResult":
        from sympy import Eq, Pow, latex

        if not self.can_apply(expression):
            raise TransformationError(
                "SquareBothSides requires an equation A = B."
            )

        lhs_squared = Pow(expression.lhs, 2)
        rhs_squared = Pow(expression.rhs, 2)
        transformed = Eq(lhs_squared, rhs_squared)

        step_latex = (
            "\\begin{aligned}\n"
            f"{latex(expression)} \\\\\n"
            f"{latex(lhs_squared)} = {latex(rhs_squared)} \\\\\n"
            "\\text{Squaring may introduce extraneous solutions; verify "
            "candidates against the original equation.}\n"
            "\\end{aligned}"
        )

        step = Step(
            title="Square both sides",
            description=(
                f"Square both sides of {latex(expression)} to obtain "
                f"{latex(transformed)}. This step is not reversible and may "
                f"introduce extraneous solutions, so every candidate must be "
                f"verified against the original equation."
            ),
            latex=step_latex,
            metadata={"kind": "square_both_sides", "warning": "extraneous_solutions"},
        )

        return TransformationResult(
            original_expression=expression,
            transformed_expression=transformed,
            step=step,
            branches=(),
            conditions=(),
            domain_restrictions=(),
            reversibility=Reversibility.IRREVERSIBLE.value,
            verification_required=VerificationRequirement.REQUIRED.value,
            extraneous_risk=True,
            metadata={"lhs": expression.lhs, "rhs": expression.rhs},
        )


# Convenience functions for common transformations


def add_subtract_both_sides(equation, term):
    """Move a term from one side to the other by adding/subtracting."""
    return AddSubtractBothSides().apply(expression=equation, term_to_move=term)


def multiply_divide_both_sides(equation, factor):
    """Multiply or divide both sides by a factor."""
    return MultiplyDivideBothSides().apply(expression=equation, factor=factor)


def expand_brackets(expression):
    """Apply the distributive law to expand brackets."""
    return DistributiveLaw().apply(expression)


def apply_square_root(equation):
    """Apply the square root property to x² = a type equations."""
    return SquareRootTransformation().apply(equation)


def apply_zero_product(equation):
    """Apply the zero product property to factored equations."""
    return ZeroProductProperty().apply(equation)


def square_both_sides(equation):
    """Square both sides of an equation (with extraneous solution warning)."""
    return SquareBothSides().apply(equation)