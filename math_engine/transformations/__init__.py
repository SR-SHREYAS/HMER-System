"""Universal mathematical transformations foundation.

This package provides stateless mathematical primitives and supporting
data structures for reusable algebraic operations across different
mathematical domains (linear, quadratic, calculus, etc.).

The transformation layer is strictly mathematical: it performs operations
and returns safety metadata. It does NOT decide when to apply operations,
does NOT own educational Steps, and does NOT import capability-specific code.
"""

from .results import (
    Reversibility,
    VerificationRequirement,
    TransformationResult,
)
from .conditions import (
    Condition,
    DomainRestriction,
    non_zero,
    non_negative,
    positive,
)
from .branches import (
    Branch,
    BranchSet,
    make_branch,
    branch_set,
)
from .primitives import (
    add_subtract_both_sides,
    multiply_divide_both_sides,
    distributive_law,
    square_root_both_sides,
    square_both_sides,
    zero_product_property,
)
from .verification import (
    VerificationStatus,
    VerificationMethod,
    VerificationResult,
    VerificationReport,
    verify_against_original,
    check_extraneous_solutions,
)

__all__ = [
    # Results
    "Reversibility",
    "VerificationRequirement",
    "TransformationResult",
    # Conditions
    "Condition",
    "DomainRestriction",
    "non_zero",
    "non_negative",
    "positive",
    # Branches
    "Branch",
    "BranchSet",
    "make_branch",
    "branch_set",
    # Primitives
    "add_subtract_both_sides",
    "multiply_divide_both_sides",
    "distributive_law",
    "square_root_both_sides",
    "square_both_sides",
    "zero_product_property",
    # Verification
    "VerificationStatus",
    "VerificationMethod",
    "VerificationResult",
    "VerificationReport",
    "verify_against_original",
    "check_extraneous_solutions",
]