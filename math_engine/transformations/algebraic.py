"""Universal algebraic transformations.

This module provides universal algebraic transformations that can be applied
across different mathematical domains (linear, quadratic, calculus, etc.).

These transformations implement universal algebraic principles that are
valid across different mathematical domains. They are designed to be
composable and reusable across different solvers.
"""

from __future__ import annotations

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from sympy import (
    Add, Mul, Pow, Eq, Ne, Ge, Gt, Le, Lt,
    expand, simplify, solve, latex, symbols, Symbol, Eq as SymEq
)

from ..models import Step
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
from ..models import Step
from ...models import Step as StepModel

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


class AddSubtractBothSides(Transformation):
    """Add or subtract the same quantity from both sides of an equation.

    This transformation moves terms from one side of an equation to the other
    by adding or subtracting the same quantity from both sides.
    """

    name = "add_subtract_both_sides"
    description = "Add or subtract the same quantity from both sides of an equation"
    reversibility = "reversible"
    verification_required = "none"
    extraneous_risk = False

    def can_apply(self, expression) -> bool:
        from sympy import Eq
        return isinstance(expression, Eq)

    def apply(self, expression, term_to_move) -> "TransformationResult":
        """Move a term from one side of the equation to the other.

        Args:
            expression: The equation (SymPy Eq).
            term_to_move: The term to move from one side to the other.

        Returns:
            TransformationResult with the transformed equation and step.
        """
        from sympy import Eq, Add, latex

        if not self.can_apply(expression):
            raise TransformationError("Expression must be an equation")

        # Determine which side the term is on
        if expression.lhs.has(term_to_move):
            # Term is on LHS, move to RHS by subtracting from both sides
            new_lhs = simplify(expression.lhs - term_to_move)
            new_rhs = simplify(expression.rhs - term_to_move)
            operation = "subtract"
        elif expression.rhs.has(term_to_move):
            # Term is on RHS, move to LHS by adding to both sides
            new_lhs = simplify(expression.lhs + term_to_move)
            new_rhs = simplify(expression.rhs + term_to_move)
            operation = "add"
        else:
            raise TransformationError(f"Term {term_to_move} not found in equation")

        transformed = Eq(new_lhs, new_rhs)

        # Build the step latex
        if operation == "subtract":
            op_latex = f"- {latex(term_to_move)}"
            desc = f"Subtract {term_to_move} from both sides"
        else:
            op_latex = f"+ {latex(term_to_move)}"
            desc = f"Add {term_to_move} to both sides"

        step_latex = (
            "\\begin{aligned}\n"
            f"{latex(expression)} \\\\\n"
            f"{op_latex} \\\\\n"
            f"{latex(Eq(new_lhs, new_rhs))}\n"
            "\\end{aligned}"
        )

        step = Step(
            title="Move term to other side",
            description=f"{desc} to isolate the variable term.",
            latex=step_latex,
            metadata={"kind": "move_term", "operation": operation},
        )

        return TransformationResult(
            original_expression=expression,
            transformed_expression=Eq(new_lhs, new_rhs),
            step=Step(
                title="Move term to other side",
                description=desc,
                latex=step_latex,
                metadata={"kind": "move_term", "operation": operation},
            ),
            branches=(),
            conditions=(),
            reversibility="reversible",
            verification_required="none",
            extraneous_risk=False,
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


class SquareRootTransformation(Transformation):
    """Apply the square root property to solve equations of the form x² = a.

    This transformation produces two branches: x = √a and x = -√a.
    """

    name = "square_root_property"
    description = "Apply the square root property to solve x² = a"
    reversibility = "branch_producing"
    verification_required = "required"
    extraneous_risk = True

    def can_apply(self, expression) -> bool:
        from sympy import Eq, Pow
        if not isinstance(expression, Eq):
            return False
        # Check if it's of the form x^2 = a or a = x^2
        lhs, rhs = expression.lhs, expression.rhs
        return (
            (lhs.is_Pow and lhs.exp == 2 and lhs.base.is_Symbol and not rhs.has(lhs.base)) or
            (rhs.is_Pow and rhs.exp == 2 and rhs.base.is_Symbol and not lhs.has(rhs.base))
        )

    def apply(self, expression) -> "TransformationResult":
        from sympy import Eq, sqrt, latex, symbols, solve

        if not self.can_apply(expression):
            raise TransformationError("Expression must be of the form x² = a")

        # Determine which side has the square
        lhs, rhs = expression.lhs, expression.rhs
        if lhs.is_Pow and lhs.exp == 2:
            variable = lhs.base
            value = rhs
        else:
            variable = rhs.base
            value = lhs

        # Create the two branches
        pos_root = sqrt(value)
        neg_root = -sqrt(value)

        branch1 = Eq(expression.lhs if expression.lhs.is_Pow else expression.rhs, pos_root)
        branch2 = Eq(expression.lhs if expression.lhs.is_Pow else expression.rhs, neg_root)

        # For the step latex, show both branches
        step_latex = (
            "\\begin{aligned}\n"
            f"{latex(expression)} \\\\\n"
            f"{latex(variable)} = \\pm \\sqrt{{{latex(solve(expression.lhs - expression.rhs, expression.free_symbols.pop())[0])}}} \\\\\n"
            f"{latex(variable)} = {latex(pos_root)} \\quad \\text{{or}} \\quad {latex(variable)} = {latex(neg_root)}\n"
            "\\end{aligned}"
        )

        step = Step(
            title="Apply square root property",
            description=f"Take the square root of both sides. Remember: x² = a has two solutions x = ±√a.",
            latex=step_latex,
            metadata={"kind": "square_root", "branches": 2},
        )

        return TransformationResult(
            original_expression=expression,
            transformed_expression=Eq(pos_root, neg_root),  # Represent both branches
            step=Step(
                title="Apply square root property",
                description="Take the square root of both sides. Remember: x² = a has two solutions x = ±√a.",
                latex=step_latex,
                metadata={"kind": "square_root", "branches": 2},
            ),
            branches=(
                Branch(expression=branch1, description=f"{variable} = {pos_root}"),
                Branch(expression=branch2, description=f"{variable} = {neg_root}"),
            ),
            conditions=(Condition(expression=Ge(value, 0), description=f"{value} ≥ 0 for real roots"),),
            reversibility="branch_producing",
            verification_required="required",
            extraneous_risk=True,
        )


class ZeroProductProperty(Transformation):
    """Apply the zero product property: if a·b = 0, then a = 0 or b = 0."""

    name = "zero_product_property"
    description = "Apply the zero product property: if a·b = 0, then a = 0 or b = 0"
    reversibility = "branch_producing"
    verification_required = "none"
    extraneous_risk = False

    def can_apply(self, expression) -> bool:
        from sympy import Eq, Mul
        if not isinstance(expression, Eq):
            return False
        return isinstance(expression.lhs, Mul) and expression.rhs == 0

    def apply(self, expression) -> "TransformationResult":
        from sympy import Eq, Mul, latex, solve

        factors = expression.lhs.args
        branches = []

        for i, factor in enumerate(factors):
            branch_eq = Eq(factor, 0)
            branch = Eq(factor, 0)
            branches.append(
                Branch(
                    expression=branch_eq,
                    description=f"Set factor {i+1} to zero: {latex(factor)} = 0",
                )
            )

        step_latex = (
            "\\begin{aligned}\n"
            f"{latex(expression)} \\\\\n"
            " + ".join(f"{latex(f)} = 0" for f in factors) + " \\\\\n"
            "\\end{aligned}"
        )

        step = Step(
            title="Apply zero product property",
            description="If a product equals zero, at least one factor must be zero.",
            latex=step_latex,
            metadata={"kind": "zero_product", "branches": len(factors)},
        )

        return TransformationResult(
            original_expression=expression,
            transformed_expression=expression,
            step=step,
            branches=tuple(branches),
            conditions=(),
            reversibility="branch_producing",
            verification_required="none",
            extraneous_risk=False,
        )


class SquareBothSides(Transformation):
    """Square both sides of an equation.

    WARNING: This transformation can introduce extraneous solutions.
    Verification against the original equation is REQUIRED.
    """

    name = "square_both_sides"
    description = "Square both sides of an equation (may introduce extraneous solutions)"
    reversibility = "irreversible"
    verification_required = "required"
    extraneous_risk = True

    def can_apply(self, expression) -> bool:
        from sympy import Eq
        return isinstance(expression, Eq)

    def apply(self, expression) -> "TransformationResult":
        from sympy import Eq, Pow, latex, simplify

        lhs_squared = Pow(expression.lhs, 2)
        rhs_squared = Pow(expression.rhs, 2)
        transformed = Eq(lhs_squared, rhs_squared)

        step_latex = (
            "\\begin{aligned}\n"
            f"{latex(expression)} \\\\\n"
            f"{latex(lhs_squared)} = {latex(rhs_squared)} \\\\\n"
            "\\text{\\color{red}{\\textbf{WARNING: Squaring can introduce extraneous solutions.}}} \\\\\n"
            "\\end{aligned}"
        )

        step = Step(
            title="Square both sides (caution: extraneous solutions possible)",
            description="Square both sides to eliminate radicals. WARNING: This can introduce extraneous solutions that must be verified against the original equation.",
            latex=step_latex,
            metadata={"kind": "square_both_sides", "warning": "extraneous_solutions"},
        )

        return TransformationResult(
            original_expression=expression,
            transformed_expression=transformed,
            step=step,
            branches=(),
            conditions=(),
            reversibility="irreversible",
            verification_required="required",
            extraneous_risk=True,
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