"""Branch representation for transformation results.

This module provides the branch abstraction for transformations that produce
multiple solution branches (e.g., square root, zero product property).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from sympy import Basic

from .base import Branch, BranchSet


@dataclass(frozen=True, slots=True)
class Branch:
    """A single solution branch from a branch-producing transformation.

    When a transformation produces multiple solution branches (e.g., taking
    the square root of both sides, applying the zero product property),
    each branch is represented as a separate Branch object.
    """

    expression: object  # sympy.Basic
    """The expression or equation for this branch."""

    conditions: tuple = field(default_factory=tuple)
    """Conditions that must hold for this branch to be valid."""

    description: str = ""
    """Human-readable description of this branch."""

    metadata: dict = field(default_factory=dict)
    """Additional metadata about this branch."""

    def __str__(self) -> str:
        return self.description or str(self.expression)


@dataclass(frozen=True, slots=True)
class BranchSet:
    """A collection of branches from a branch-producing transformation.

    When a transformation produces multiple branches (e.g., square root,
    zero product property), the branches are collected into a BranchSet.
    """

    branches: tuple
    """The individual solution branches."""

    original_expression: object
    """The original expression before the branch-producing transformation."""

    def __len__(self) -> int:
        return len(self.branches)

    def __iter__(self):
        return iter(self.branches)

    def __getitem__(self, index: int):
        return self.branches[index]

    def __bool__(self) -> bool:
        return len(self.branches) > 0


def make_branch(
    expression,
    conditions: tuple = (),
    description: str = "",
    **metadata
) -> "Branch":
    """Create a branch with the given expression and optional conditions."""
    from .base import Branch
    return Branch(
        expression=expression,
        conditions=conditions,
        description=description,
    )


def branch_set(branches: Iterable, original_expression) -> "BranchSet":
    """Create a BranchSet from an iterable of branches."""
    return BranchSet(
        branches=tuple(branches),
        original_expression=original_expression,
    )


__all__ = [
    "Branch",
    "BranchSet",
    "make_branch",
    "branch_set",
]