"""Universal algebraic primitives.

This module provides stateless mathematical functions that perform universal
algebraic operations. They are designed to be composable and reusable across
different solvers (linear, quadratic, calculus, etc.).

Each primitive is a pure function: it takes SymPy objects and returns a
TransformationResult containing the mathematical result and safety metadata.
"""

from __future__ import annotations

from typing import Any

from sympy import Eq, Mul, Add, Pow, sqrt, simplify, latex, symbols, Basic, solve, Ne, Ge

from .results import (
    TransformationResult,
    Reversibility,
    VerificationRequirement,
)
from .conditions import Condition, non_zero, non_negative
from .branches import Branch, make_branch


def add_subtract_both_sides(equation: Eq, term: Basic) -> TransformationResult:
    """Add or subtract the same quantity from both sides of an equation.

    A = B  ->  A ± term = B ± term

    This operation is always reversible and never introduces extraneous
    solutions. It carries no domain conditions.
    """
    if not isinstance(equation, Eq):
        raise ValueError("add_subtract_both_sides requires an Eq object")

    # Determine operation direction by checking which side contains the term
    # In both cases, we subtract the term from both sides to "move" it to the other side
    if equation.lhs.has(term):
        # Term is on LHS, move to RHS by subtracting from both sides
        new_lhs = simplify(equation.lhs - term)
        new_rhs = simplify(equation.rhs - term)
        operation = "subtract"
    elif equation.rhs.has(term):
        # Term is on RHS, move to LHS by subtracting from both sides
        new_lhs = simplify(equation.lhs - term)
        new_rhs = simplify(equation.rhs - term)
        operation = "subtract"
    else:
        raise ValueError(f"Term {term} not found in either side of equation")

    transformed = Eq(new_lhs, new_rhs)

    # Build presentation hints
    if operation == "subtract":
        op_latex = f"- {latex(term)}"
        desc = f"Subtract {latex(term)} from both sides"
    else:
        op_latex = f"+ {latex(term)}"
        desc = f"Add {latex(term)} to both sides"

    step_latex = (
        "\\begin{aligned}\n"
        f"{latex(equation)} \\\\\n"
        f"{op_latex} \\\\\n"
        f"{latex(transformed)}\n"
        "\\end{aligned}"
    )

    return TransformationResult(
        transformed_expression=transformed,
        branches=(),
        conditions=(),
        domain_restrictions=(),
        reversibility=Reversibility.REVERSIBLE,
        verification_required=VerificationRequirement.NONE,
        extraneous_risk=False,
        suggested_kind="add_subtract_both_sides",
        suggested_title="Move term to other side",
        suggested_description=desc,
        suggested_latex=step_latex,
        suggested_metadata={"operation": operation},
    )


def multiply_divide_both_sides(equation: Eq, factor: Basic) -> TransformationResult:
    """Multiply or divide both sides of an equation by a non-zero factor.

    A = B  ->  A × factor = B × factor

    This operation is conditionally reversible: it requires factor ≠ 0.
    Verification is recommended to catch cases where factor might evaluate to zero.
    """
    if not isinstance(equation, Eq):
        raise ValueError("multiply_divide_both_sides requires an Eq object")

    if factor == 0:
        raise ValueError("Cannot multiply or divide by zero")

    new_lhs = simplify(equation.lhs * factor)
    new_rhs = simplify(equation.rhs * factor)
    transformed = Eq(new_lhs, new_rhs)

    if factor == 1:
        raise ValueError("Multiplying by 1 has no effect")

    # Build presentation hints
    factor_latex = latex(factor)
    step_latex = (
        "\\begin{aligned}\n"
        f"{latex(equation)} \\\\\n"
        f"\\times {factor_latex} \\\\\n"
        f"{latex(transformed)}\n"
        "\\end{aligned}"
    )

    return TransformationResult(
        transformed_expression=transformed,
        branches=(),
        conditions=(Condition(
            expression=Ne(factor, 0),
            description=f"{factor} ≠ 0",
        ),),
        domain_restrictions=(),
        reversibility=Reversibility.CONDITIONAL,
        verification_required=VerificationRequirement.RECOMMENDED,
        extraneous_risk=False,
        suggested_kind="multiply_divide_both_sides",
        suggested_title="Multiply both sides",
        suggested_description=f"Multiply both sides by {factor_latex} to eliminate fractions.",
        suggested_latex=step_latex,
        suggested_metadata={"factor": factor},
    )


def distributive_law(expression: Basic) -> TransformationResult:
    """Apply the distributive law to expand products over sums.

    a(b + c) -> ab + ac

    This operates on any Mul containing an Add. The result is an expanded
    expression (not an Eq). The operation is conditionally reversible
    (factoring is the inverse but not always possible).
    """
    if not isinstance(expression, Mul):
        raise ValueError("distributive_law requires a Mul expression")

    # Check if any factor is an Add (sum)
    has_add = any(isinstance(arg, Add) for arg in expression.args)
    if not has_add:
        raise ValueError("No expandable sum found in product")

    expanded = simplify(expression.expand())

    if expanded == expression:
        raise ValueError("Expression is already expanded")

    step_latex = (
        "\\begin{aligned}\n"
        f"{latex(expression)} \\\\\n"
        f"{latex(expanded)}\n"
        "\\end{aligned}"
    )

    return TransformationResult(
        transformed_expression=expanded,
        branches=(),
        conditions=(),
        domain_restrictions=(),
        reversibility=Reversibility.CONDITIONAL,
        verification_required=VerificationRequirement.NONE,
        extraneous_risk=False,
        suggested_kind="distributive_law",
        suggested_title="Expand brackets",
        suggested_description="Distribute the multiplier across each term inside the parentheses using the distributive law: a(b + c) = ab + ac.",
        suggested_latex=step_latex,
        suggested_metadata={"rule": "distributive_law"},
    )


def square_root_both_sides(equation: Eq) -> TransformationResult:
    """Apply the square root property to solve equations of the form A² = B.

    A² = B  ->  A = +sqrt(B)  OR  A = -sqrt(B)

    This produces TWO branches preserving both ± roots. For B = 0, the
    two branches collapse to a single branch (duplicate ±0 eliminated).
    Negative radicands are not fabricated into real roots - the domain
    condition B ≥ 0 for real roots is recorded.

    This transformation is branch-producing and requires verification
    against the original equation.
    """
    if not isinstance(equation, Eq):
        raise ValueError("square_root_both_sides requires an Eq object")

    # Detect form: lhs² = rhs or rhs² = lhs
    lhs, rhs = equation.lhs, equation.rhs

    # Find the squared term
    squared_expr = None
    value_expr = None
    variable = None

    if isinstance(lhs, Pow) and lhs.exp == 2:
        squared_expr = lhs
        value_expr = rhs
        variable = lhs.base
    elif isinstance(rhs, Pow) and rhs.exp == 2:
        squared_expr = rhs
        value_expr = lhs
        variable = rhs.base
    else:
        raise ValueError("Equation must be of the form A² = B or B = A²")

    if not variable.is_Symbol:
        raise ValueError("Squared base must be a symbol")

    # Create the two branches: ±sqrt(value)
    pos_root = sqrt(value_expr)
    neg_root = -sqrt(value_expr)

    branch1 = Eq(variable, pos_root)
    branch2 = Eq(variable, neg_root)

    # Handle the special case where value is 0 (duplicate branches)
    branches = []
    if value_expr == 0:
        # Both branches are the same, keep only one
        branches.append(make_branch(
            branch1,
            description=f"{variable} = 0",
        ))
    else:
        branches.append(make_branch(
            branch1,
            description=f"{variable} = {latex(pos_root)}",
        ))
        branches.append(make_branch(
            branch2,
            description=f"{variable} = {latex(neg_root)}",
        ))

    # Build presentation hints
    step_latex = (
        "\\begin{aligned}\n"
        f"{latex(equation)} \\\\\n"
        f"{latex(variable)} = \\pm \\sqrt{{{latex(value_expr)}}} \\\\\n"
    )
    if value_expr == 0:
        step_latex += f"{latex(variable)} = 0"
    else:
        step_latex += f"{latex(variable)} = {latex(pos_root)} \\quad \\text{{or}} \\quad {latex(variable)} = {latex(neg_root)}"
    step_latex += "\n\\end{aligned}"

    return TransformationResult(
        transformed_expression=equation,  # Original kept; branches carry results
        branches=tuple(branches),
        conditions=(Condition(
            expression=Ge(value_expr, 0),
            description=f"{value_expr} ≥ 0 for real roots",
        ),),
        domain_restrictions=(),
        reversibility=Reversibility.BRANCH_PRODUCING,
        verification_required=VerificationRequirement.REQUIRED,
        extraneous_risk=True,
        suggested_kind="square_root",
        suggested_title="Apply square root property",
        suggested_description="Take the square root of both sides. Remember: A² = B has two solutions A = ±√B.",
        suggested_latex=step_latex,
        suggested_metadata={"branches": len(branches)},
    )


def square_both_sides(equation: Eq) -> TransformationResult:
    """Square both sides of an equation.

    A = B  ->  A² = B²

    WARNING: This transformation is irreversible and can introduce
    extraneous solutions. Verification against the original equation
    is REQUIRED.
    """
    if not isinstance(equation, Eq):
        raise ValueError("square_both_sides requires an Eq object")

    lhs_squared = Pow(equation.lhs, 2)
    rhs_squared = Pow(equation.rhs, 2)
    transformed = Eq(lhs_squared, rhs_squared)

    step_latex = (
        "\\begin{aligned}\n"
        f"{latex(equation)} \\\\\n"
        f"{latex(lhs_squared)} = {latex(rhs_squared)} \\\\\n"
        "\\text{\\color{red}{\\textbf{WARNING: Squaring can introduce extraneous solutions.}}} \\\\\n"
        "\\end{aligned}"
    )

    return TransformationResult(
        transformed_expression=transformed,
        branches=(),
        conditions=(),
        domain_restrictions=(),
        reversibility=Reversibility.IRREVERSIBLE,
        verification_required=VerificationRequirement.REQUIRED,
        extraneous_risk=True,
        suggested_kind="square_both_sides",
        suggested_title="Square both sides (caution: extraneous solutions possible)",
        suggested_description="Square both sides to eliminate radicals. WARNING: This can introduce extraneous solutions that must be verified against the original equation.",
        suggested_latex=step_latex,
        suggested_metadata={"warning": "extraneous_solutions"},
    )


def zero_product_property(equation: Eq) -> TransformationResult:
    """Apply the zero product property: if A × B × ... = 0, then A = 0 OR B = 0 OR ...

    This produces one branch per factor. No domain restrictions are introduced.
    """
    if not isinstance(equation, Eq):
        raise ValueError("zero_product_property requires an Eq object")

    if equation.rhs != 0:
        raise ValueError("zero_product_property requires equation of the form expr = 0")

    if not isinstance(equation.lhs, Mul):
        raise ValueError("LHS must be a product (Mul) for zero product property")

    factors = equation.lhs.args
    if len(factors) < 2:
        raise ValueError("zero_product_property requires at least two factors")

    branches = []
    for i, factor in enumerate(factors):
        branch_eq = Eq(factor, 0)
        branches.append(make_branch(
            branch_eq,
            description=f"Set factor {i+1} to zero: {latex(factor)} = 0",
            metadata={"factor_index": i},
        ))

    step_latex = (
        "\\begin{aligned}\n"
        f"{latex(equation)} \\\\\n"
        " + ".join(f"{latex(f)} = 0" for f in factors) + " \\\\\n"
        "\\end{aligned}"
    )

    return TransformationResult(
        transformed_expression=equation,
        branches=tuple(branches),
        conditions=(),
        domain_restrictions=(),
        reversibility=Reversibility.BRANCH_PRODUCING,
        verification_required=VerificationRequirement.NONE,
        extraneous_risk=False,
        suggested_kind="zero_product",
        suggested_title="Apply zero product property",
        suggested_description="If a product equals zero, at least one factor must be zero.",
        suggested_latex=step_latex,
        suggested_metadata={"branches": len(branches)},
    )


__all__ = [
    "add_subtract_both_sides",
    "multiply_divide_both_sides",
    "distributive_law",
    "square_root_both_sides",
    "square_both_sides",
    "zero_product_property",
]