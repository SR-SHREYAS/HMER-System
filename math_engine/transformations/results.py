"""Core result types for universal mathematical transformations.

This module defines the domain-neutral data structures for representing the
result of a mathematical transformation, including safety metadata, branch
information, and presentation hints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sympy import Basic


class Reversibility(str, Enum):
    """Classification of a transformation's reversibility.

    This classification determines how the transformation affects the solution
    set and whether the original problem can be recovered from the result.
    """

    REVERSIBLE = "reversible"
    """Transformation is fully reversible (bijective on the solution set).

    The original problem can be exactly recovered from the transformed state.
    Example: adding the same quantity to both sides of an equation."""

    CONDITIONAL = "conditional"
    """Transformation is reversible only under specific conditions.

    The transformation is reversible when certain conditions hold.
    Example: dividing both sides by an expression (reversible when divisor != 0)."""

    IRREVERSIBLE = "irreversible"
    """Transformation is not reversible (information is lost).

    The original problem cannot be exactly recovered from the transformed state.
    Example: squaring both sides of an equation."""

    BRANCH_PRODUCING = "branch_producing"
    """Transformation produces multiple solution branches.

    The transformation splits the problem into multiple branches, each of which
    must be solved independently. The original problem's solution set is the
    union of all branch solutions.
    Example: taking the square root of both sides (x^2 = 4 -> x = 2, x = -2)."""


class VerificationRequirement(str, Enum):
    """Whether and how the transformation result needs verification."""

    NONE = "none"
    """No verification needed. Transformation is mathematically guaranteed
    to preserve the solution set."""

    RECOMMENDED = "recommended"
    """Verification is recommended but not strictly required.
    The transformation is mathematically sound but numerical errors
    or edge cases could cause issues."""

    REQUIRED = "required"
    """Verification is mandatory. The transformation can produce results
    that are not valid solutions to the original problem.
    Example: squaring both sides can introduce extraneous solutions."""


@dataclass(frozen=True, slots=True)
class TransformationResult:
    """Result of applying a mathematical transformation.

    This class encapsulates the complete mathematical result of applying a
    transformation, including the transformed expression, any generated
    branches, conditions, safety information, and presentation hints.

    It does NOT contain an educational Step. Presentation hints are provided
    for convenience but the capability rule owns the authoritative Step.
    """

    transformed_expression: Basic
    """The expression after applying the transformation."""

    branches: tuple["Branch", ...] = field(default_factory=tuple)
    """Additional solution branches produced by this transformation.

    Empty for single-result transformations. Non-empty for branch-producing
    transformations like square root, zero product property, etc."""

    conditions: tuple["Condition", ...] = field(default_factory=tuple)
    """Conditions that must hold for this transformation to be valid.

    Examples: x != 0 (for division), x >= 0 (for square root)."""

    domain_restrictions: tuple["DomainRestriction", ...] = field(default_factory=tuple)
    """Domain restrictions on variables (as structured objects).

    Examples: ["x != 0", "x >= 0"]."""

    reversibility: Reversibility = Reversibility.REVERSIBLE
    """Reversibility classification of this transformation.

    Values: "reversible", "conditional", "irreversible", "branch_producing"."""

    verification_required: VerificationRequirement = VerificationRequirement.NONE
    """Whether verification of the result against the original problem is needed.

    Values: "none", "recommended", "required"."""

    extraneous_risk: bool = False
    """Whether this transformation can introduce extraneous solutions.

    True for operations like squaring both sides that can introduce
    extraneous solutions requiring verification against the original problem."""

    # Presentation hints (capability rule MAY override these)
    suggested_kind: str = ""
    """Suggested step kind for educational presentation."""

    suggested_title: str = ""
    """Suggested step title for educational presentation."""

    suggested_description: str = ""
    """Suggested step description for educational presentation."""

    suggested_latex: str = ""
    """Suggested step LaTeX for educational presentation."""

    suggested_metadata: dict[str, Any] = field(default_factory=dict)
    """Suggested step metadata for educational presentation."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata about the transformation."""

    @property
    def has_branches(self) -> bool:
        """Whether this transformation produces multiple branches."""
        return len(self.branches) > 0

    @property
    def is_reversible(self) -> bool:
        """Whether the transformation is fully reversible."""
        return self.reversibility == Reversibility.REVERSIBLE

    @property
    def requires_verification(self) -> bool:
        """Whether verification of results is required."""
        return self.verification_required in (
            VerificationRequirement.RECOMMENDED,
            VerificationRequirement.REQUIRED,
        )


# Forward references for type hints
class Branch:
    pass


class Condition:
    pass


class DomainRestriction:
    pass


__all__ = [
    "Reversibility",
    "VerificationRequirement",
    "TransformationResult",
]