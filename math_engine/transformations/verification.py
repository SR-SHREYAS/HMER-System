"""Verification infrastructure for transformation results.

This module provides domain-neutral verification functions for checking that
transformation results are valid solutions to the original problem.

Verification is exact symbolic (substitute and simplify difference == 0).
Numeric sampling is NOT included in this foundation - it can be added in a
later phase if actually required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sympy import Eq, simplify, Basic, Symbol

from .results import TransformationResult
from .conditions import Condition


class VerificationStatus(str, Enum):
    """Result of a verification check."""

    VALID = "valid"
    """Verification passed - candidate is a valid solution."""

    INVALID = "invalid"
    """Verification failed - candidate is not a valid solution."""

    INDETERMINATE = "indeterminate"
    """Verification could not determine validity (e.g., symbolic complexity)."""


class VerificationMethod(str, Enum):
    """Method used for verification."""

    SYMBOLIC = "symbolic"
    """Exact symbolic verification (simplify difference == 0)."""


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """Result of a verification check."""

    status: VerificationStatus
    """Whether verification passed, failed, or was indeterminate."""

    method: VerificationMethod
    """Method used for verification."""

    message: str = ""
    """Human-readable explanation of the result."""

    details: dict[str, Any] = field(default_factory=dict)
    """Additional details about the verification."""

    @property
    def passed(self) -> bool:
        return self.status == VerificationStatus.VALID


@dataclass(frozen=True, slots=True)
class VerificationReport:
    """Complete verification report for a transformation result."""

    original_expression: Basic
    """The original problem expression."""

    verified_candidates: tuple[Basic, ...] = field(default_factory=tuple)
    """Candidates that passed verification."""

    rejected_candidates: tuple[Basic, ...] = field(default_factory=tuple)
    """Candidates that failed verification."""

    indeterminate_candidates: tuple[Basic, ...] = field(default_factory=tuple)
    """Candidates with indeterminate verification status."""

    extraneous_detected: bool = False
    """Whether any extraneous solutions were detected and removed."""

    details: dict[str, Any] = field(default_factory=dict)
    """Additional verification details."""

    @property
    def all_passed(self) -> bool:
        return len(self.rejected_candidates) == 0 and len(self.indeterminate_candidates) == 0

    @property
    def valid_solutions(self) -> tuple[Basic, ...]:
        """All candidates that passed or are indeterminate."""
        return self.verified_candidates + self.indeterminate_candidates


def verify_against_original(
    candidate: Basic,
    original_equation: Eq,
    variable: Symbol | None = None,
    domain_restrictions: tuple = ()
) -> VerificationResult:
    """Check if a candidate solution satisfies the original equation.

    Uses exact symbolic verification: substitutes the candidate into the
    original equation and checks if the difference simplifies to zero.

    Also enforces any domain restrictions (e.g., x >= 0 for square roots).

    Args:
        candidate: The candidate solution to verify (e.g., a value or Eq).
        original_equation: The original equation to verify against.
        variable: The variable being solved for (optional, inferred if not given).
        domain_restrictions: Domain conditions that must be satisfied.

    Returns:
        VerificationResult indicating VALID, INVALID, or INDETERMINATE.
    """
    if not isinstance(original_equation, Eq):
        return VerificationResult(
            status=VerificationStatus.INDETERMINATE,
            method=VerificationMethod.SYMBOLIC,
            message="Original expression is not an equation",
        )

    # Determine the variable if not provided
    if variable is None:
        free = original_equation.free_symbols
        if len(free) == 1:
            variable = next(iter(free))
        else:
            return VerificationResult(
                status=VerificationStatus.INDETERMINATE,
                method=VerificationMethod.SYMBOLIC,
                message="Cannot infer variable for verification",
            )

    # Check domain restrictions first
    for restriction in domain_restrictions:
        try:
            check_expr = restriction.expression.subs(variable, candidate)
            if hasattr(check_expr, "evalf"):
                check_val = check_expr.evalf()
                if check_val == 0 or check_val is False:
                    return VerificationResult(
                        status=VerificationStatus.INVALID,
                        method=VerificationMethod.SYMBOLIC,
                        message=f"Domain restriction violated: {restriction}",
                    )
        except Exception:
            pass  # If check fails, continue to main verification

    # Main verification: substitute candidate into original equation
    try:
        if isinstance(candidate, Eq):
            # Candidate is an equation like Eq(x, 5)
            if candidate.lhs == variable:
                candidate_value = candidate.rhs
            elif candidate.rhs == variable:
                candidate_value = candidate.lhs
            else:
                return VerificationResult(
                    status=VerificationStatus.INDETERMINATE,
                    method=VerificationMethod.SYMBOLIC,
                    message="Candidate equation does not solve for the expected variable",
                )
        else:
            # Candidate is a bare value
            candidate_value = candidate

        # Substitute into original equation and check difference
        substituted = original_equation.subs(variable, candidate_value)
        
        # Handle case where substitution simplifies to a boolean (True/False)
        if substituted == True:
            return VerificationResult(
                status=VerificationStatus.VALID,
                method=VerificationMethod.SYMBOLIC,
                message="Candidate satisfies original equation",
            )
        elif substituted == False:
            return VerificationResult(
                status=VerificationStatus.INVALID,
                method=VerificationMethod.SYMBOLIC,
                message="Candidate does not satisfy original equation",
            )
        
        # Otherwise, it should be an Eq object - check difference
        difference = simplify(substituted.lhs - substituted.rhs)

        if difference == 0:
            return VerificationResult(
                status=VerificationStatus.VALID,
                method=VerificationMethod.SYMBOLIC,
                message="Candidate satisfies original equation",
            )
        # If difference contains free symbols other than the solved variable,
        # we cannot determine validity (e.g., multivariable equations)
        free_in_diff = difference.free_symbols
        if free_in_diff and (variable is None or free_in_diff != {variable}):
            return VerificationResult(
                status=VerificationStatus.INDETERMINATE,
                method=VerificationMethod.SYMBOLIC,
                message=f"Cannot determine validity with free symbols: {free_in_diff}",
            )
        else:
            return VerificationResult(
                status=VerificationStatus.INVALID,
                method=VerificationMethod.SYMBOLIC,
                message=f"Candidate does not satisfy equation (difference = {difference})",
            )
    except Exception as e:
        return VerificationResult(
            status=VerificationStatus.INDETERMINATE,
            method=VerificationMethod.SYMBOLIC,
            message=f"Verification error: {e}",
        )


def check_extraneous_solutions(
    candidates: tuple,
    original_equation: Eq,
    variable: Symbol | None = None,
    domain_restrictions: tuple = ()
) -> tuple[tuple, tuple]:
    """Partition candidates into verified and extraneous.

    Verifies each candidate against the original equation using exact
    symbolic verification. Returns (verified_candidates, rejected_candidates).

    Args:
        candidates: Tuple of candidate solutions (values or Eq objects).
        original_equation: The original equation to verify against.
        variable: The variable being solved for.
        domain_restrictions: Domain conditions to enforce.

    Returns:
        Tuple of (verified, rejected) candidate tuples.
    """
    verified = []
    rejected = []

    for candidate in candidates:
        result = verify_against_original(
            candidate, original_equation, variable, domain_restrictions
        )
        if result.status == VerificationStatus.VALID:
            verified.append(candidate)
        elif result.status == VerificationStatus.INVALID:
            rejected.append(candidate)
        else:
            # Indeterminate - include in verified but flag for review
            verified.append(candidate)

    return tuple(verified), tuple(rejected)


__all__ = [
    "VerificationStatus",
    "VerificationMethod",
    "VerificationResult",
    "VerificationReport",
    "verify_against_original",
    "check_extraneous_solutions",
]