"""Common mathematical transformation infrastructure.

This package provides domain-neutral infrastructure for reusable mathematical
transformations that can be shared across linear, quadratic, differentiation,
and future capabilities (integration, limits, etc.).

The transformations here are universal algebraic operations that preserve
mathematical meaning across different problem domains. They do not contain
domain-specific logic such as quadratic formula, chain rule, etc.
"""

from .base import (
    TransformationResult,
    Reversibility,
    Condition,
    Branch,
    Transformation,
)

from .conditions import (
    Condition,
    DomainRestriction,
    NonZeroCondition,
    NonNegativeCondition,
    PositiveCondition,
)

from .branches import (
    Branch,
    BranchSet,
)

from .presentation import (
    TransformationPayload,
    payload,
    step_from_result,
)

__all__ = [
    "TransformationResult",
    "Reversibility",
    "Condition",
    "Branch",
    "Transformation",
    "Condition",
    "DomainRestriction",
    "NonZeroCondition",
    "NonNegativeCondition",
    "PositiveCondition",
    "Branch",
    "BranchSet",
    "TransformationPayload",
    "payload",
    "step_from_result",
]