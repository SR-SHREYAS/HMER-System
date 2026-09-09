"""Phase 35.1 Foundation Tests.

Tests that the universal transformation foundation correctly represents:
1. Mathematical correctness of each primitive
2. Branch preservation (including x²=25 -> ±5)
3. Condition metadata
4. Safety metadata (reversibility, verification, extraneous risk)
5. Exact symbolic verification
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sympy import Eq, symbols, sqrt, simplify, Mul, Add, Pow, Basic, Ne, Ge

from math_engine.transformations import (
    # Results
    TransformationResult,
    Reversibility,
    VerificationRequirement,
    # Conditions
    Condition,
    non_zero,
    non_negative,
    # Branches
    Branch,
    make_branch,
    # Primitives
    add_subtract_both_sides,
    multiply_divide_both_sides,
    distributive_law,
    square_root_both_sides,
    square_both_sides,
    zero_product_property,
    # Verification
    VerificationStatus,
    VerificationMethod,
    verify_against_original,
    check_extraneous_solutions,
)


def test_add_subtract_both_sides():
    """Test add/subtract both sides: x + 4 = 9 -> x = 5."""
    x = symbols('x')
    eq = Eq(x + 4, 9)
    result = add_subtract_both_sides(eq, 4)

    assert isinstance(result, TransformationResult)
    assert result.transformed_expression == Eq(x, 5)
    assert result.reversibility == Reversibility.REVERSIBLE
    assert result.verification_required == VerificationRequirement.NONE
    assert not result.extraneous_risk
    assert not result.has_branches
    assert result.conditions == ()
    assert result.suggested_kind == "add_subtract_both_sides"
    print("✓ add_subtract_both_sides basic")


def test_add_subtract_move_from_rhs():
    """Test moving term from RHS: x = y + 3 -> x - 3 = y."""
    x, y = symbols('x y')
    eq = Eq(x, y + 3)
    result = add_subtract_both_sides(eq, 3)

    assert result.transformed_expression == Eq(x - 3, y)
    print("✓ add_subtract_both_sides RHS -> LHS")


def test_multiply_divide_both_sides():
    """Test multiply/divide both sides: x/3 = 2 -> x = 6."""
    x = symbols('x')
    eq = Eq(x / 3, 2)
    result = multiply_divide_both_sides(eq, 3)

    assert result.transformed_expression == Eq(x, 6)
    assert result.reversibility == Reversibility.CONDITIONAL
    assert result.verification_required == VerificationRequirement.RECOMMENDED
    assert not result.extraneous_risk
    assert len(result.conditions) == 1
    # Ne(3, 0) simplifies to True since 3 is a non-zero constant
    assert result.conditions[0].expression == True
    assert result.suggested_kind == "multiply_divide_both_sides"
    print("✓ multiply_divide_both_sides basic")


def test_multiply_divide_by_zero_raises():
    """Test that dividing by zero raises ValueError."""
    x = symbols('x')
    eq = Eq(x, 5)
    try:
        multiply_divide_both_sides(eq, 0)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "zero" in str(e).lower()
    print("✓ multiply_divide_both_sides zero rejection")


def test_distributive_law():
    """Test distributive law: 2*(x + 3) -> 2*x + 6."""
    from sympy import Mul
    x = symbols('x')
    expr = Mul(2, x + 3, evaluate=False)
    result = distributive_law(expr)

    assert isinstance(result.transformed_expression, Add)
    assert result.transformed_expression == 2*x + 6
    assert result.reversibility == Reversibility.CONDITIONAL
    assert not result.has_branches
    assert result.suggested_kind == "distributive_law"
    print("✓ distributive_law basic")


def test_distributive_law_non_mul_raises():
    """Test that non-Mul raises ValueError."""
    x = symbols('x')
    try:
        distributive_law(x + 3)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    print("✓ distributive_law non-Mul rejection")


def test_square_root_both_sides_basic():
    """Test square root: x^2 = 25 -> x = 5 OR x = -5."""
    x = symbols('x')
    eq = Eq(x**2, 25)
    result = square_root_both_sides(eq)

    assert result.has_branches
    assert len(result.branches) == 2
    assert result.reversibility == Reversibility.BRANCH_PRODUCING
    assert result.verification_required == VerificationRequirement.REQUIRED
    assert result.extraneous_risk

    # Check branch content - should be Eq(x, 5) and Eq(x, -5)
    branch_exprs = [b.expression for b in result.branches]
    assert Eq(x, 5) in branch_exprs
    assert Eq(x, -5) in branch_exprs
    assert result.suggested_kind == "square_root"
    print("✓ square_root_both_sides x^2 = 25 -> two branches")


def test_square_root_both_sides_zero():
    """Test square root with zero: x^2 = 0 -> x = 0 (single branch)."""
    x = symbols('x')
    eq = Eq(x**2, 0)
    result = square_root_both_sides(eq)

    assert result.has_branches
    assert len(result.branches) == 1  # Duplicate ±0 collapsed
    assert result.branches[0].expression == Eq(x, 0)
    print("✓ square_root_both_sides x^2 = 0 -> single branch")


def test_square_root_both_sides_symbolic():
    """Test square root with symbolic radicand: x^2 = a."""
    x, a = symbols('x a')
    eq = Eq(x**2, a)
    result = square_root_both_sides(eq)

    assert result.has_branches
    assert len(result.branches) == 2
    # Should have domain condition a >= 0
    assert len(result.conditions) == 1
    print("✓ square_root_both_sides symbolic radicand")


def test_square_root_alternate_variable():
    """Test square root with different variable name: y^2 = 16."""
    y = symbols('y')
    eq = Eq(y**2, 16)
    result = square_root_both_sides(eq)

    assert result.has_branches
    assert len(result.branches) == 2
    branch_exprs = [b.expression for b in result.branches]
    assert Eq(y, 4) in branch_exprs
    assert Eq(y, -4) in branch_exprs
    print("✓ square_root_both_sides y^2 = 16")


def test_square_root_non_squared_raises():
    """Test that non-squared equation raises ValueError."""
    x = symbols('x')
    eq = Eq(x, 5)
    try:
        square_root_both_sides(eq)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    print("✓ square_root_both_sides non-squared rejection")


def test_square_both_sides():
    """Test square both sides: sqrt(x) = 3 -> x = 9."""
    x = symbols('x')
    from sympy import sqrt
    eq = Eq(sqrt(x), 3)
    result = square_both_sides(eq)

    assert result.transformed_expression == Eq(x, 9)
    assert result.reversibility == Reversibility.IRREVERSIBLE
    assert result.verification_required == VerificationRequirement.REQUIRED
    assert result.extraneous_risk
    assert result.suggested_kind == "square_both_sides"
    assert "warning" in result.suggested_metadata
    print("✓ square_both_sides safety metadata")


def test_zero_product_property():
    """Test zero product: x*(x-2) = 0 -> x = 0 OR x = 2."""
    x = symbols('x')
    eq = Eq(x * (x - 2), 0)
    result = zero_product_property(eq)

    assert result.has_branches
    assert len(result.branches) == 2
    assert result.reversibility == Reversibility.BRANCH_PRODUCING
    assert result.verification_required == VerificationRequirement.NONE
    assert not result.extraneous_risk

    branch_exprs = [b.expression for b in result.branches]
    assert Eq(x, 0) in branch_exprs
    assert Eq(x - 2, 0) in branch_exprs
    assert result.suggested_kind == "zero_product"
    print("✓ zero_product_property two factors")


def test_zero_product_three_factors():
    """Test zero product with 3 factors: x*(x-1)*(x+1) = 0."""
    x = symbols('x')
    eq = Eq(x * (x - 1) * (x + 1), 0)
    result = zero_product_property(eq)

    assert len(result.branches) == 3
    branch_exprs = [b.expression for b in result.branches]
    assert Eq(x, 0) in branch_exprs
    assert Eq(x - 1, 0) in branch_exprs
    assert Eq(x + 1, 0) in branch_exprs
    print("✓ zero_product_property three factors")


def test_zero_product_repeated_factor():
    """Test zero product with squared factor: x^2*(x-1) = 0."""
    x = symbols('x')
    eq = Eq(x**2 * (x - 1), 0)
    result = zero_product_property(eq)

    # x^2 is a Pow, not a Mul factor, so it's treated as one factor
    # The factors are x^2 and (x-1), so 2 branches
    assert len(result.branches) == 2
    branch_exprs = [b.expression for b in result.branches]
    assert Eq(x**2, 0) in branch_exprs
    assert Eq(x - 1, 0) in branch_exprs
    print("✓ zero_product_property repeated factor")


def test_zero_product_non_mul_raises():
    """Test that non-Mul LHS raises ValueError."""
    x = symbols('x')
    eq = Eq(x, 0)
    try:
        zero_product_property(eq)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    print("✓ zero_product_property non-Mul rejection")


def test_zero_product_non_zero_rhs_raises():
    """Test that non-zero RHS raises ValueError."""
    x = symbols('x')
    eq = Eq(x * (x - 2), 5)
    try:
        zero_product_property(eq)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    print("✓ zero_product_property non-zero RHS rejection")


def test_conditions():
    """Test condition factory functions."""
    x = symbols('x')
    nz = non_zero(x)
    assert isinstance(nz, Condition)
    assert str(nz.expression) == "Ne(x, 0)"

    nn = non_negative(x)
    assert str(nn.expression) == "x >= 0"
    print("✓ condition factories")


def test_branch_creation():
    """Test branch factory."""
    x = symbols('x')
    branch = make_branch(Eq(x, 5), description="x = 5")
    assert branch.expression == Eq(x, 5)
    assert branch.description == "x = 5"
    print("✓ branch factory")


def test_verification_basic():
    """Test exact symbolic verification: x = 5 satisfies x - 5 = 0."""
    x = symbols('x')
    candidate = 5
    original = Eq(x - 5, 0)
    result = verify_against_original(candidate, original, x)

    assert result.status == VerificationStatus.VALID
    assert result.method == VerificationMethod.SYMBOLIC
    print("✓ verification VALID")


def test_verification_invalid():
    """Test that x = 1 fails x - 5 = 0."""
    x = symbols('x')
    candidate = 1
    original = Eq(x - 5, 0)
    result = verify_against_original(candidate, original, x)

    assert result.status == VerificationStatus.INVALID
    print("✓ verification INVALID")


def test_verification_with_eq_candidate():
    """Test verification with Eq candidate: Eq(x, 5)."""
    x = symbols('x')
    candidate = Eq(x, 5)
    original = Eq(x - 5, 0)
    result = verify_against_original(candidate, original, x)

    assert result.status == VerificationStatus.VALID
    print("✓ verification with Eq candidate")


def test_verification_indeterminate():
    """Test indeterminate case: symbolic complexity."""
    x = symbols('x')
    candidate = symbols('a')
    original = Eq(x - 5, 0)
    result = verify_against_original(candidate, original, x)

    assert result.status == VerificationStatus.INDETERMINATE
    print("✓ verification INDETERMINATE")


def test_check_extraneous():
    """Test extraneous solution filtering: sqrt(x) = x - 2 -> x = 4 (valid), x = 1 (extraneous)."""
    x = symbols('x')
    original = Eq(sqrt(x), x - 2)
    # Candidates from squaring: x = 4 (valid), x = 1 (extraneous)
    candidates = (4, 1)
    verified, rejected = check_extraneous_solutions(candidates, original, x)

    assert 4 in verified
    assert 1 in rejected
    print("✓ check_extraneous_solutions")


def test_check_extraneous_multivariable():
    """Test extraneous check with multiple variables."""
    x, y = symbols('x y')
    original = Eq(x + y, 10)
    # Only one variable specified
    candidates = (5, 3)
    verified, rejected = check_extraneous_solutions(candidates, original, x)

    # Only x is substituted, y remains symbolic
    # x=5: 5+y=10 -> y=5 (indeterminate without y value)
    # x=3: 3+y=10 -> y=7 (indeterminate without y value)
    # Both should be indeterminate
    assert len(verified) == 2
    assert len(rejected) == 0
    print("✓ check_extraneous_solutions multivariable")


def test_transformation_result_properties():
    """Test TransformationResult computed properties."""
    x = symbols('x')
    eq = Eq(x**2, 25)
    result = square_root_both_sides(eq)

    assert result.has_branches
    assert not result.is_reversible
    assert result.requires_verification
    print("✓ TransformationResult properties")


def test_transformation_result_reversible():
    """Test reversible transformation properties."""
    x = symbols('x')
    eq = Eq(x + 4, 9)
    result = add_subtract_both_sides(eq, 4)

    assert not result.has_branches
    assert result.is_reversible
    assert not result.requires_verification
    print("✓ reversible transformation properties")


def run_all_tests():
    """Run all foundation tests."""
    print("Running Phase 35.1 foundation tests...\n")

    test_add_subtract_both_sides()
    test_add_subtract_move_from_rhs()
    test_multiply_divide_both_sides()
    test_multiply_divide_by_zero_raises()
    test_distributive_law()
    test_distributive_law_non_mul_raises()
    test_square_root_both_sides_basic()
    test_square_root_both_sides_zero()
    test_square_root_both_sides_symbolic()
    test_square_root_alternate_variable()
    test_square_root_non_squared_raises()
    test_square_both_sides()
    test_zero_product_property()
    test_zero_product_three_factors()
    test_zero_product_repeated_factor()
    test_zero_product_non_mul_raises()
    test_zero_product_non_zero_rhs_raises()
    test_conditions()
    test_branch_creation()
    test_verification_basic()
    test_verification_invalid()
    test_verification_with_eq_candidate()
    test_verification_indeterminate()
    test_check_extraneous()
    test_check_extraneous_multivariable()
    test_transformation_result_properties()
    test_transformation_result_reversible()

    print("\n✓ All Phase 35.1 foundation tests passed!")
    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)