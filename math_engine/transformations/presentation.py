"""Presentation boundary between transformations and capability rules.

This module defines the *only* sanctioned way a capability rule consumes a
:class:`TransformationResult`. Its purpose is to keep two concerns apart:

* the transformation owns the **mathematics** (the transformed expression,
  branches, conditions, reversibility, verification requirement); and
* the rule owns the **educational presentation** (``Step`` title, description,
  latex, ``kind``, ordering).

The boundary is deliberately tiny. It does **not** reimplement any mathematical
operation (addition/division/expansion/square root/squaring/zero-product); it
only reads the fields a transformation already produced and hands them to the
caller as a plain, presentation-free payload.

Design rationale (from the Phase 35.2 regression): an earlier attempt let a rule
return ``TransformationResult.step`` verbatim, which leaked the transformation's
generic ``kind``/description into the linear educational contract (``divide`` →
``multiply_both_sides``, ``\\div`` → ``\\times 1/c``). The fix is to make the
transformation's ``step`` an *opt-in fallback* only, and to expose a
``TransformationPayload`` that a rule must turn into its own ``Step``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Iterable

from sympy import Basic

from math_engine.models import Step

from .base import Branch, Condition, TransformationResult


@dataclass(frozen=True, slots=True)
class TransformationPayload:
    """A presentation-free view of a ``TransformationResult``.

    This carries the mathematical outcome only. It intentionally has **no**
    ``step`` field, so a rule cannot accidentally surface the transformation's
    generic educational wording. The rule is expected to build its own
    :class:`Step`.
    """

    transformed_expression: Basic
    """The primary transformed expression."""

    branches: tuple[Branch, ...] = field(default_factory=tuple)
    """Branch equations produced by branch-aware transformations (may be empty)."""

    conditions: tuple[Condition, ...] = field(default_factory=tuple)
    """Conditions / domain restrictions attached by the transformation."""

    reversibility: str = "reversible"
    """Reversibility classification (see ``Reversibility``)."""

    verification_required: str = "none"
    """Whether downstream verification is required/recommended/none."""

    extraneous_risk: bool = False
    """Whether the transformation may introduce extraneous candidates."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Any transformation metadata a rule may wish to render."""

    @property
    def has_branches(self) -> bool:
        return len(self.branches) > 0

    @property
    def requires_verification(self) -> bool:
        return self.verification_required in ("recommended", "required")


def payload(result: TransformationResult) -> TransformationPayload:
    """Extract the mathematical payload (presentation-free) from a result.

    This is the single entry point a capability rule should call. It drops the
    transformation's own ``step`` so the rule stays the sole owner of
    educational presentation.
    """
    return TransformationPayload(
        transformed_expression=result.transformed_expression,
        branches=result.branches,
        conditions=result.conditions,
        reversibility=result.reversibility,
        verification_required=result.verification_required,
        extraneous_risk=result.extraneous_risk,
        metadata=dict(result.metadata),
    )


def step_from_result(
    result: TransformationResult,
    *,
    title: str,
    description: str,
    latex: str,
    kind: str,
    metadata: dict[str, Any] | None = None,
) -> Step:
    """Build a capability-owned ``Step`` from a ``TransformationResult``.

    Every ``Step`` field is supplied by the caller (i.e. the rule), never by the
    transformation. ``metadata`` is merged over the transformation's own
    metadata so mathematical facts survive without dictating presentation.
    """
    merged = dict(result.metadata)
    if metadata:
        merged.update(metadata)
    merged.setdefault("kind", kind)
    return Step(
        title=title,
        description=description,
        latex=latex,
        metadata=merged,
    )


__all__ = [
    "TransformationPayload",
    "payload",
    "step_from_result",
]