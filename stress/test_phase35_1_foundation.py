"""Tests for the transformation foundation.

Tests that the data structures can correctly represent:
1. Single transformation
2. Branching transformation
3. Conditional transformation
5. Educational Step compatibility
"""

import sys
sys.path.insert(0, "/home/SPRYZEN/Desktop/code/Final_Projects/HMER-System")

from sympy import symbols, Eq, sqrt, latex, Eq as SymEq

from math_engine.transformations.base import (
    TransformationResult,
    Reversibility,
    Condition,
    Branch,
    BranchSet,
    TransformationResult,
    Transformation,
    Condition,
    DomainRestriction,
    Branch,
    BranchSet,
)
from math_engine.transformations.conditions import (
    Condition,
    non_zero,
    non_negative,
    PositiveCondition,
    EqualCondition,
)
from math_engine.transformations.branches import Branch, BranchSet
from math_engine.transformations.verification import (
    verify_against_original,
    check_extraneous_solutions,
)
from sympy import symbols, Eq, sqrt, latex, symbols as sp_symbols, simplify


def test_single_transformation():
    """Test single transformation: x + 4 = 9 -> x = 5."""
    x = symbols('x')
    original = Eq(x + 4, 9)
    transformed = Eq(sp_symbols('x'), 5)

    from math_engine.transformations.base import TransformationResult, Step
    from math_engine.models import Step as StepModel

    step = Step(
        title="Subtract 4 from both sides",
        description="Subtract 4 from both sides to isolate the variable term.",
        latex=r"\begin{aligned} x + 4 = 9 \\ x = 5 \end{aligned}",
        metadata={"kind": "move_term", "operation": "subtract"},
    )

    result = TransformationResult(
        original_expression=sp_symbols('x') + 4 - 9,  # placeholder
        transformed_expression=sp_symbols('x') - 5,
        step=Step(
            title="Subtract 4 from both sides",
            description="Subtract 4 from both sides to isolate the variable term.",
            latex=r"\begin{aligned} x + 4 = 9 \\ x = 5 \end{aligned}",
            metadata={"kind": "move_term", "operation": "subtract"},
        ),
        branches=(),
        conditions=(),
        reversibility="reversible",
        verification_required="none",
        extraneous_risk=False,
    )

    assert result.reversibility == "reversible"
    assert result.verification_required == "none"
    assert not result.has_branches
    assert result.is_reversible
    assert not result.requires_verification
    print("✓ Single transformation test passed")


def test_branching_transformation():
    """Test branching transformation: x^2 = 25 -> x = 5, x = -5."""
    from math_engine.transformations.base import Branch, BranchSet

    x = symbols('x')
    original = Eq(sp_symbols('x')**2, 25)

    branch1 = Branch(
        expression=sp_symbols('x') - 5,
        description="x = 5",
    )
    branch2 = Branch(
        expression=sp_symbols('x') + 5,
        description="x = -5",
    )

    branch_set = (branch1, branch2)

    from math_engine.transformations.base import TransformationResult, Step

    step = Step(
        title="Apply square root property",
        description="Take the square root of both sides. Remember: x² = a has two solutions x = ±√a.",
        latex=r"\begin{aligned} x^2 = 25 \\ x = \pm \sqrt{25} \\ x = 5 \quad \text{or} \quad x = -5 \end{aligned}",
        metadata={"kind": "square_root", "branches": 2},
    )

    result = TransformationResult(
        original_expression=sp_symbols('x')**2 - 25,
        transformed_expression=sp_symbols('x')**2 - 25,
        step=Step(
            title="Apply square root property",
            description="Take the square root of both sides. Remember: x² = a has two solutions x = ±√a.",
            latex=r"\begin{aligned} x^2 = 25 \\ x = \pm \sqrt{25} \\ x = 5 \quad \text{or} \quad x = -5 \end{aligned}",
            metadata={"kind": "square_root", "branches": 2},
        ),
        branches=(
            Branch(expression=5, description="x = 5"),
            Branch(expression=-5, description="x = -5"),
        ),
        conditions=(),
        reversibility="branch_producing",
        verification_required="required",
        extraneous_risk=True,
    )

    assert result.has_branches
    assert len(result.branches) == 2
    assert result.reversibility == "branch_producing"
    assert result.verification_required == "required"
    assert result.extraneous_risk
    print("✓ Branching transformation test passed")


def test_conditional_transformation():
    """Test conditional transformation: x / y = 2 with y != 0."""
    from math_engine.transformations.conditions import non_zero
    from sympy import symbols, Eq

    x, y = symbols('x y')
    original = Eq(x / y, 2)

    condition = Condition(
        expression=sp_symbols('y') != 0,
        description="y ≠ 0 (division by zero is undefined)"
    )

    assert condition.expression is not None
    print("✓ Conditional transformation test passed")


def test_verification_transformation():
    """Test transformation requiring verification (squaring both sides)."""
    from math_engine.transformations.base import TransformationResult, Step

    step = Step(
        title="Square both sides (caution: extraneous solutions possible)",
        description="Square both sides to eliminate radicals. WARNING: This can introduce extraneous solutions that must be verified against the original equation.",
        latex=r"\begin{aligned} \sqrt{x+3} = x-1 \\ x+3 = (x-1)^2 \\ \text{\color{red}{\textbf{WARNING: Squaring can introduce extraneous solutions.}}} \end{aligned}",
        metadata={"kind": "square_both_sides", "warning": "extraneous_solutions"},
    )

    result = TransformationResult(
        original_expression=sp_symbols('x'),
        transformed_expression=sp_symbols('x'),
        step=Step(
            title="Square both sides (caution: extraneous solutions possible)",
            description="Square both sides to eliminate radicals. WARNING: This can introduce extraneous solutions that must be verified against the original equation.",
            latex=r"\begin{aligned} \sqrt{x+3} = x-1 \\ x+3 = (x-1)^2 \\ \text{\color{red}{\textbf{WARNING: Squaring can introduce extraneous solutions.}}} \end{aligned}",
            metadata={"kind": "square_both_sides", "warning": "extraneous_solutions"},
        ),
        branches=(),
        conditions=(),
        reversibility="irreversible",
        verification_required="required",
        extraneous_risk=True,
    )

    assert result.reversibility == "irreversible"
    assert result.verification_required == "required"
    assert result.extraneous_risk
    print("✓ Verification transformation test passed")


def test_educational_step_compatibility():
    """Test that the transformation foundation works with existing Step model."""
    from math_engine.models import Step as StepModel
    from math_engine.transformations.base import TransformationResult

    # Create a step using the existing Step model
    from math_engine.models import Step as StepModel
    step = StepModel(
        title="Test Step",
        description="Test description",
        latex="x = 5",
        metadata={"kind": "test", "custom_field": "value"}
    )

    result = TransformationResult(
        original_expression=None,
        transformed_expression=None,
        step=step,
        branches=(),
        conditions=(),
        reversibility="reversible",
        verification_required="none",
        extraneous_risk=False,
    )

    assert result.step.title == "Test Step"
    assert result.step.metadata["kind"] == "test"
    assert result.step.metadata["custom_field"] == "value"
    print("✓ Educational Step compatibility test passed")


def test_branch_representation():
    """Test branch representation for x^2 = 25."""
    from math_engine.transformations.base import Branch, BranchSet
    from sympy import symbols

    x = sp_symbols('x')
    branch1 = Branch(expression=5, description="x = 5")
    branch2 = Branch(expression=-5, description="x = -5")

    branches = (branch1, branch2)
    branch_set = (branch1, branch2)

    assert len(branches) == 2
    assert str(branch1) == "x = 5"
    assert str(branch2) == "x = -5"
    print("✓ Branch representation test passed")


def run_all_tests():
    """Run all foundation tests."""
    print("Running Phase 35.1 foundation tests...\n")

    test_single_transformation()
    test_branching_transformation()
    test_conditional_transformation()
    test_verification_transformation()
    test_educational_step_compatibility()
    test_branch_representation()

    print("\n✓ All Phase 35.1 foundation tests passed!")
    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)