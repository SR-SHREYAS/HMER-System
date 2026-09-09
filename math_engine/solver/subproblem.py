"""Subproblem delegation contract for capability-to-capability delegation.

This module defines the minimal contract for delegating a subproblem to another
capability solver. It does not implement any orchestration, decomposition, or
branching logic — it only defines the data structures and the factory method
for executing a delegated subproblem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sympy import Basic

from math_engine.models import Expression, Solution, TaskType
from math_engine.transformations.conditions import Condition


MAX_DELEGATION_DEPTH = 3
"""Maximum allowed delegation depth to prevent runaway recursion."""


@dataclass(frozen=True, slots=True)
class SubproblemRequest:
    """Request to solve a subproblem within a parent capability.

    Attributes:
        capability: The capability/task type to invoke.
        expression: The subproblem expression to solve.
        parent_context: Optional parent state (variable bindings, branch info,
            domain restrictions, etc.). Reserved for future phases.
        depth: Current delegation depth. 0 = top-level parent requesting first
            child. Must not exceed MAX_DELEGATION_DEPTH.
    """

    capability: TaskType
    expression: Expression
    parent_context: dict[str, Any] = field(default_factory=dict)
    depth: int = 0


@dataclass(frozen=True, slots=True)
class SubproblemResult:
    """Result of a delegated subproblem.

    Attributes:
        solution: The complete solution produced by the child capability.
        subproblem_kind: String identifying the subproblem type,
            e.g., "derivative_subproblem", "quadratic_equation_subproblem".
        conditions: Domain/condition metadata from the child capability,
            if any. Empty tuple for this phase.
    """

    solution: Solution
    subproblem_kind: str
    conditions: tuple[Condition, ...] = ()


__all__ = [
    "SubproblemRequest",
    "SubproblemResult",
    "MAX_DELEGATION_DEPTH",
]