"""Core transformation data models.

This module defines the core data structures for representing mathematical
transformations in a domain-neutral way. These models are designed to be
reusable across linear, quadratic, differentiation, and future capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sympy import Basic

from math_engine.models import Step


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

    CONDITIONAL_REVERSIBLE = "conditionally_reversible"
    """Transformation is reversible only when specific conditions are met.

    Similar to CONDITIONAL but explicitly indicates the transformation itself
    is mathematically reversible when conditions are met, as opposed to
    transformations that fundamentally change the solution set."""

    IRREVERSIBLE = "irreversible"
    """Transformation is not reversible (information is lost).

    The original problem cannot be exactly recovered from the transformed state.
    Example: squaring both sides of an equation, taking a square root without
    preserving the negative branch."""

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
class Condition:
    """A mathematical condition or constraint on a transformation.

    Conditions represent mathematical constraints that must hold for a
    transformation to be valid, or that describe domain restrictions on
    the solution set.

    Conditions are represented as symbolic expressions rather than strings
    to preserve mathematical meaning and enable future symbolic reasoning.
    """

    expression: Basic
    """The symbolic condition expression (e.g., x != 0, x >= 0)."""

    description: str = ""
    """Human-readable description of the condition."""

    def __str__(self) -> str:
        return self.description or str(self.expression)

    def __bool__(self) -> bool:
        """A condition is truthy if it has a non-empty expression."""
        return self.expression is not None


@dataclass(frozen=True, slots=True)
class DomainRestriction:
    """A domain restriction on the variable(s) in an expression.

    Domain restrictions specify the valid domain of variables for a
    transformation to be mathematically valid.
    """

    variable: str
    """The variable name this restriction applies to."""

    condition: Condition
    """The condition describing the restriction."""

    description: str = ""
    """Human-readable description of the domain restriction."""


@dataclass(frozen=True, slots=True)
class Branch:
    """A single solution branch from a branch-producing transformation.

    When a transformation produces multiple solution branches (e.g., taking
    the square root of both sides, applying the zero product property),
    each branch is represented as a separate Branch object.
    """

    expression: Basic
    """The expression or equation for this branch."""

    conditions: tuple[Condition, ...] = field(default_factory=tuple)
    """Conditions that must hold for this branch to be valid."""

    description: str = ""
    """Human-readable description of this branch."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata about this branch."""

    def __str__(self) -> str:
        return self.description or str(self.expression)


@dataclass(frozen=True, slots=True)
class BranchSet:
    """A collection of branches from a branch-producing transformation.

    When a transformation produces multiple branches (e.g., square root,
    zero product property), the branches are collected into a BranchSet.
    """

    branches: tuple[Branch, ...]
    """The individual solution branches."""

    original_expression: Basic
    """The original expression before the branch-producing transformation."""

    def __len__(self) -> int:
        return len(self.branches)

    def __iter__(self):
        return iter(self.branches)

    def __getitem__(self, index: int) -> Branch:
        return self.branches[index]


@dataclass(frozen=True, slots=True)
class TransformationResult:
    """Result of applying a mathematical transformation.

    This class encapsulates the complete result of applying a mathematical
    transformation, including the transformed expression, any generated
    branches, conditions, safety information, and educational step data.
    """

    original_expression: Basic
    """The original expression before transformation."""

    transformed_expression: Basic
    """The expression after applying the transformation."""

    step: "Step"
    """The educational step representing this transformation."""

    branches: tuple[Branch, ...] = field(default_factory=tuple)
    """Additional solution branches produced by this transformation.

    Empty for single-result transformations. Non-empty for branch-producing
    transformations like square root, zero product property, etc."""

    conditions: tuple[Condition, ...] = field(default_factory=tuple)
    """Conditions that must hold for this transformation to be valid.

    Examples: x != 0 (for division), x >= 0 (for square root)."""

    domain_restrictions: tuple[str, ...] = field(default_factory=tuple)
    """Domain restrictions on variables (as strings for serialization).

    Examples: ["x != 0", "x >= 0"]."""

    reversibility: str = "reversible"
    """Reversibility classification of this transformation.

    Values: "reversible", "conditional", "irreversible", "branch_producing"."""

    verification_required: str = "none"
    """Whether verification of the result against the original problem is needed.

    Values: "none", "recommended", "required"."""

    extraneous_risk: bool = False
    """Whether this transformation can introduce extraneous solutions.

    True for operations like squaring both sides that can introduce
    extraneous solutions requiring verification against the original problem."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata about the transformation."""

    @property
    def has_branches(self) -> bool:
        """Whether this transformation produces multiple branches."""
        return len(self.branches) > 0

    @property
    def is_reversible(self) -> bool:
        """Whether the transformation is fully reversible."""
        return self.reversibility == "reversible"

    @property
    def requires_verification(self) -> bool:
        """Whether verification of results is required."""
        return self.verification_required in ("recommended", "required")


@dataclass(frozen=True, slots=True)
class Transformation:
    """Base class for mathematical transformations.

    A transformation encapsulates a single mathematical operation that can be
    applied to an expression to produce a new expression, along with metadata
    about the transformation's properties and educational explanation.
    """

    name: str
    """Unique identifier for this transformation (e.g., 'add_subtract_both_sides')."""

    description: str
    """Human-readable description of what this transformation does."""

    reversibility: str = "reversible"
    """Default reversibility classification for this transformation."""

    verification_required: str = "none"
    """Default verification requirement for this transformation."""

    extraneous_risk: bool = False
    """Whether this transformation can introduce extraneous solutions."""

    def __init__(self, name: str | None = None, description: str | None = None, **kwargs):
        # Use class attributes as defaults if not provided
        if name is None:
            name = getattr(self, 'name', '')
        if description is None:
            description = getattr(self, 'description', '')
        object.__setattr__(self, 'name', name)
        object.__setattr__(self, 'description', description)
        for k, v in kwargs.items():
            object.__setattr__(self, k, v)

    def can_apply(self, expression) -> bool:
        """Check if this transformation can be applied to the given expression.

        Args:
            expression: The expression to check.

        Returns:
            True if this transformation can be applied, False otherwise.
        """
        raise NotImplementedError

    def apply(self, expression) -> "TransformationResult":
        """Apply this transformation to the given expression.

        Args:
            expression: The expression to transform.

        Returns:
            A TransformationResult containing the transformed expression,
            any branches, conditions, and educational step information.

        Raises:
            TransformationError: If the transformation cannot be applied.
        """
        raise NotImplementedError

    def format_step_latex(self, original: Any, transformed: Any) -> str:
        """Format the LaTeX representation of this transformation step.

        Args:
            original: The original expression.
            transformed: The transformed expression.

        Returns:
            LaTeX string for rendering the step.
        """
        raise NotImplementedError


class TransformationError(Exception):
    """Exception raised when a transformation cannot be applied."""

    pass


__all__ = [
    "Reversibility",
    "VerificationRequirement",
    "Condition",
    "DomainRestriction",
    "Branch",
    "BranchSet",
    "TransformationResult",
    "Transformation",
    "TransformationError",
]