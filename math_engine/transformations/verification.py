"""Domain-neutral mathematical verification infrastructure.

This module provides a reusable mechanism for checking whether a *candidate*
solution satisfies a *original* mathematical equation/expression, independent of
any particular solver or capability (linear, quadratic, differentiation, etc.).

Verification operates on SymPy objects only -- never on LaTeX strings, rendered
text, or variable-name assumptions. It distinguishes three outcomes:

* ``VALID``         -- exact symbolic substitution proves the candidate solves
                       the original equation (``simplify(LHS - RHS) == 0``).
* ``INVALID``       -- the candidate provably does **not** solve the original
                       equation (including extraneous and domain-invalid cases).
* ``INDETERMINATE`` -- the symbolic structure cannot safely establish validity
                       (e.g. an undecidable domain condition). Never silently
                       coerced to ``VALID``.

This is a *pure* verification layer. It does not solve, transform, or generate
candidates, and it must not be confused with the existing
:class:`DerivativeSolver` verification (which remains untouched).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping

from sympy import Eq, S, simplify, sympify

from .base import Branch, TransformationResult


class VerificationStatus(str, Enum):
    """Three-valued outcome of a verification check.

    ``passed`` corresponds to VALID, ``failed`` to INVALID, and
    ``indeterminate`` to INDETERMINATE.
    """

    PASSED = "passed"
    FAILED = "failed"
    INDETERMINATE = "indeterminate"


class VerificationMethod(str, Enum):
    """How a verification decision was reached."""

    SYMBOLIC = "symbolic"
    """Exact symbolic check (``simplify(LHS - RHS) == 0``)."""

    NUMERIC = "numeric"
    """Numeric evaluation at substituted values (fallback only)."""


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """Structured result of a single verification check."""

    status: VerificationStatus
    """Whether the candidate is valid, invalid, or indeterminate."""

    method: VerificationMethod
    """The method that produced the decision."""

    candidate: object = None
    """The candidate that was verified."""

    substituted: object = None
    """The substitution applied to the original equation (e.g. ``{x: 5}``)."""

    conditions_checked: tuple = field(default_factory=tuple)
    """Conditions (SymPy relationals or ``Condition``) that were evaluated."""

    failed_conditions: tuple = field(default_factory=tuple)
    """Conditions the candidate violated."""

    extraneous: bool = False
    """True when the candidate is satisfiable by a *transformed* equation but
    provably fails the *original* equation."""

    message: str = ""
    """Human-readable explanation of the outcome."""

    @property
    def valid(self) -> bool:
        return self.status is VerificationStatus.PASSED

    @property
    def invalid(self) -> bool:
        return self.status is VerificationStatus.FAILED

    @property
    def indeterminate(self) -> bool:
        return self.status is VerificationStatus.INDETERMINATE


def _candidate_substitution(candidate, variable) -> Mapping:
    """Normalize a candidate into a ``{symbol: value}`` substitution mapping.

    Accepts:

    * a bare value (``5``, ``-5``, ``sqrt(2)``) -- requires a single ``variable``
      to be supplied,
    * an equality ``Eq(y, 3)`` -- the LHS is used as the symbol,
    * a mapping ``{x: 2, y: 3}`` -- used directly (multi-variable),
    * an iterable of equalities ``[Eq(x,2), Eq(y,3)]`` -- merged.
    """
    if isinstance(candidate, Mapping):
        return {sympify(k): sympify(v) for k, v in candidate.items()}
    if isinstance(candidate, Eq):
        return {sympify(candidate.lhs): sympify(candidate.rhs)}
    if isinstance(candidate, (list, tuple)) and all(
        isinstance(item, Eq) for item in candidate
    ):
        mapping = {}
        for item in candidate:
            mapping[sympify(item.lhs)] = sympify(item.rhs)
        return mapping
    # Bare scalar value.
    if variable is None:
        raise ValueError(
            "A bare candidate value requires an explicit variable for "
            "substitution."
        )
    return {sympify(variable): sympify(candidate)}


def _check_substitution(original_eq: Eq, mapping: Mapping) -> tuple:
    """Return ``(status, method)`` for substituting ``mapping`` into ``original_eq``.

    Uses exact symbolic comparison first; if the difference is a definite
    non-zero number it is INVALID; if it remains unresolved it is INDETERMINATE.
    """
    lhs = original_eq.lhs
    rhs = original_eq.rhs
    try:
        diff = simplify(sympify(lhs - rhs).subs(mapping))
    except Exception:  # noqa: BLE001 - substitution may fail on exotic objects
        return VerificationStatus.INDETERMINATE, VerificationMethod.SYMBOLIC

    # Exact symbolic equality.
    try:
        if diff.is_zero is True:
            return VerificationStatus.PASSED, VerificationMethod.SYMBOLIC
    except Exception:  # noqa: BLE001
        pass
    try:
        if diff.equals(S(0)):
            return VerificationStatus.PASSED, VerificationMethod.SYMBOLIC
    except Exception:  # noqa: BLE001
        pass

    # If the difference is a concrete, non-zero number we can definitively reject.
    if diff.is_number:
        if not diff.is_zero and diff.is_real or (diff.is_number and diff != 0):
            return VerificationStatus.FAILED, VerificationMethod.SYMBOLIC

    return VerificationStatus.INDETERMINATE, VerificationMethod.SYMBOLIC


def _check_conditions(mapping: Mapping, conditions: Iterable) -> tuple:
    """Return ``(checked, failed)`` for a list of conditions.

    Each condition is either a ``Condition`` (from the transformation layer), a
    Phase 35.1 concrete condition class (``NonZeroCondition`` etc., which expose
    an ``.expression`` property), or a raw SymPy relational. A condition that
    cannot be conclusively evaluated is reported in ``failed`` with a ``None``
    value so callers treat the candidate conservatively.
    """
    checked = []
    failed = []
    for condition in conditions:
        # Normalize: any object exposing a symbolic `.expression` (dataclass
        # field or property) is unwrapped; raw SymPy relationals pass through.
        symbolic = getattr(condition, "expression", condition)

        checked.append(condition)
        try:
            result = sympify(symbolic).subs(mapping)
        except Exception:  # noqa: BLE001
            failed.append((condition, None))
            continue

        simplified = simplify(result)
        if simplified is S.true:
            continue
        if simplified is S.false:
            failed.append((condition, simplified))
            continue
        if simplified.is_Relational or isinstance(simplified, bool):
            try:
                if bool(simplified):
                    continue
                failed.append((condition, simplified))
                continue
            except Exception:  # noqa: BLE001 - undecidable boolean
                failed.append((condition, None))
                continue
        # Residual non-boolean expression that could not be reduced.
        failed.append((condition, None))

    return tuple(checked), tuple(failed)


class EquationVerifier:
    """Verify candidate solutions against an original equation.

    Parameters
    ----------
    original_equation:
        The *original* equation (SymPy ``Eq``) that candidates must satisfy.
    variable:
        The single variable to substitute a bare scalar candidate into; optional
        when candidates are passed as ``Eq``/mapping.
    conditions:
        Optional domain conditions (``Condition`` or SymPy relationals) that a
        candidate must also satisfy (e.g. ``x != 0``, ``x >= 0``).
    """

    def __init__(
        self,
        original_equation,
        variable=None,
        conditions: Iterable = (),
    ):
        self.original_equation = original_equation
        self.variable = variable
        self.conditions = tuple(conditions)

    def verify(self, candidate) -> VerificationResult:
        """Verify a single candidate against the original equation.

        Parameters
        ----------
        candidate:
            A bare value, an ``Eq``, a mapping, or an iterable of ``Eq``.

        Returns
        -------
        VerificationResult
            A structured result carrying the decision plus diagnostics.
        """
        # Non-equalities cannot be substitution-verified in this manner.
        if not isinstance(self.original_equation, Eq):
            return VerificationResult(
                status=VerificationStatus.INDETERMINATE,
                method=VerificationMethod.SYMBOLIC,
                candidate=candidate,
                substituted=None,
                conditions_checked=(),
                failed_conditions=(),
                extraneous=False,
                message="Original problem is not an equality; cannot verify by substitution.",
            )

        try:
            mapping = _candidate_substitution(candidate, self.variable)
        except ValueError as exc:
            return VerificationResult(
                status=VerificationStatus.INDETERMINATE,
                method=VerificationMethod.SYMBOLIC,
                candidate=candidate,
                substituted=None,
                conditions_checked=(),
                failed_conditions=(),
                extraneous=False,
                message=str(exc),
            )

        status, method = _check_substitution(self.original_equation, mapping)

        checked, failed = _check_conditions(mapping, self.conditions)

        # A violated domain condition forces INVALID (never silently VALID).
        if failed and any(not (isinstance(f, tuple) and f[1] is None) for f in failed):
            if status is not VerificationStatus.FAILED:
                status = VerificationStatus.FAILED
            message = "Candidate violates one or more domain conditions."
        elif status is VerificationStatus.PASSED and any(
            isinstance(f, tuple) and f[1] is None for f in failed
        ):
            # An undecidable condition downgrades VALID to INDETERMINATE.
            status = VerificationStatus.INDETERMINATE
            message = "A domain condition could not be conclusively evaluated."
        elif status is VerificationStatus.INDETERMINATE and not failed:
            message = (
                "Could not conclusively establish equality via symbolic "
                "substitution."
            )
        elif status is VerificationStatus.FAILED:
            message = (
                "Candidate does not satisfy the original equation "
                "(extraneous or incorrect)."
            )
        else:
            message = "Candidate satisfies the original equation."

        extraneous = (
            status is VerificationStatus.FAILED
            and len(mapping) > 0
        )

        return VerificationResult(
            status=status,
            method=method,
            candidate=candidate,
            substituted=mapping,
            conditions_checked=checked,
            failed_conditions=failed,
            extraneous=extraneous,
            message=message,
        )


def verify_against_original(candidate, original_equation, variable=None) -> VerificationResult:
    """Convenience wrapper returning a full :class:`VerificationResult`."""
    return EquationVerifier(original_equation, variable=variable).verify(candidate)


class BranchVerifier:
    """Verify every branch produced by a transformation, independently."""

    def __init__(self, original_equation, variable=None, conditions=()):
        self._verifier = EquationVerifier(
            original_equation, variable=variable, conditions=conditions
        )

    def verify_branch_set(self, branches: Iterable) -> list[tuple]:
        """Verify each branch against the original equation.

        Parameters
        ----------
        branches:
            An iterable of ``Branch`` (or ``Eq``/candidate values).

        Returns
        -------
        list of ``(branch, VerificationResult)`` pairs, preserving branch order.
        """
        results = []
        for branch in branches:
            expr = branch.expression if isinstance(branch, Branch) else branch
            results.append((branch, self._verifier.verify(expr)))
        return results


def check_extraneous_solutions(
    candidates: Iterable, original_equation, variable=None, conditions=()
) -> tuple:
    """Partition candidates into ``(valid, extraneous, indeterminate)``.

    A candidate is *extraneous* when it fails the original equation. This is the
    mechanism future solvers use to reject solutions produced by non-injective
    transformations (e.g. squaring both sides).
    """
    verifier = EquationVerifier(original_equation, variable=variable, conditions=conditions)
    valid, extraneous, indeterminate = [], [], []
    for candidate in candidates:
        result = verifier.verify(candidate)
        if result.valid:
            valid.append(candidate)
        elif result.invalid:
            extraneous.append(candidate)
        else:
            indeterminate.append(candidate)
    return tuple(valid), tuple(extraneous), tuple(indeterminate)


class TransformationVerifier:
    """Verify a :class:`TransformationResult` against an original problem."""

    def __init__(self, original_equation, variable=None, conditions=()):
        self._verifier = EquationVerifier(
            original_equation, variable=variable, conditions=conditions
        )

    def verify_result(self, result: TransformationResult) -> list[tuple]:
        """Verify the branches (or single result) of a transformation.

        Returns
        -------
        list of ``(candidate, VerificationResult)`` for each branch of
        ``result``; for a single-result transformation a one-element list.
        """
        if result.branches:
            candidates = [b.expression for b in result.branches]
        else:
            candidates = [result.transformed_expression]
        return [(c, self._verifier.verify(c)) for c in candidates]


__all__ = [
    "VerificationStatus",
    "VerificationMethod",
    "VerificationResult",
    "EquationVerifier",
    "BranchVerifier",
    "TransformationVerifier",
    "verify_against_original",
    "check_extraneous_solutions",
]