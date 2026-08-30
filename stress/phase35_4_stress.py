"""Phase 35.4 -- common mathematical verification architecture stress harness.

Validates the domain-neutral verification layer (``EquationVerifier``,
``BranchVerifier``, ``TransformationVerifier``, extraneous-solution detection)
independently of any solver output. Verification is exercised against *original*
equations only, using exact symbolic substitution -- never LaTeX/string
comparison and never the solvers themselves.

Run from the repo root:

    PYTHONPATH=. .venv/bin/python stress/phase35_4_stress.py
"""

from __future__ import annotations

import sys

from sympy import Eq, Rational, S, log, solve, sqrt, symbols

from math_engine.transformations.algebraic import (
    SquareRootTransformation,
    SquareBothSides,
    ZeroProductProperty,
)
from math_engine.transformations.conditions import (
    non_negative,
    non_zero,
    positive,
)
from math_engine.transformations.verification import (
    BranchVerifier,
    EquationVerifier,
    TransformationVerifier,
    check_extraneous_solutions,
    verify_against_original,
    VerificationStatus,
)


def _check(name, fn):
    try:
        fn()
        return name, True, None
    except AssertionError as exc:
        return name, False, str(exc)
    except Exception as exc:  # noqa: BLE001
        return name, False, f"{type(exc).__name__}: {exc}"


x, y, a, b = symbols("x y a b")


# ---------------------------------------------------------------------------
# VALID cases
# ---------------------------------------------------------------------------

def v_x2_25_pos():
    r = EquationVerifier(Eq(x**2, 25), variable=x).verify(5)
    assert r.status is VerificationStatus.PASSED, r.status


def v_x2_25_neg():
    r = EquationVerifier(Eq(x**2, 25), variable=x).verify(-5)
    assert r.status is VerificationStatus.PASSED, r.status


def v_x2_0():
    r = EquationVerifier(Eq(x**2, 0), variable=x).verify(0)
    assert r.status is VerificationStatus.PASSED, r.status


def v_y2_9():
    for val in (3, -3):
        r = EquationVerifier(Eq(y**2, 9), variable=y).verify(val)
        assert r.status is VerificationStatus.PASSED, (val, r.status)


def v_non_bare_square():
    # (x+2)^2 = 9  -> x = 1  (since (1+2)^2 = 9)
    r = EquationVerifier(Eq((x + 2) ** 2, 9), variable=x).verify(1)
    assert r.status is VerificationStatus.PASSED, r.status


def v_rational():
    r = EquationVerifier(Eq(3 * x, 12), variable=x).verify(4)
    assert r.status is VerificationStatus.PASSED, r.status


def v_symbolic_candidate():
    # x = a  verified with candidate a  -> trivially valid
    r = EquationVerifier(Eq(x, a), variable=x).verify(a)
    assert r.status is VerificationStatus.PASSED, r.status


def v_multivariate():
    eq = Eq(x**2 + y**2, 1)
    r = EquationVerifier(eq).verify({x: Rational(3, 5), y: Rational(4, 5)})
    assert r.status is VerificationStatus.PASSED, r.status


def v_candidate_as_eq():
    r = EquationVerifier(Eq(x**2, 25)).verify(Eq(x, 5))
    assert r.status is VerificationStatus.PASSED, r.status


# ---------------------------------------------------------------------------
# INVALID cases (including extraneous)
# ---------------------------------------------------------------------------

def i_x2_25_wrong():
    for val in (4, 6):
        r = EquationVerifier(Eq(x**2, 25), variable=x).verify(val)
        assert r.status is VerificationStatus.FAILED, (val, r.status)
        assert r.extraneous is True


def i_extraneous_sqrt():
    # sqrt(x) = x - 2  has roots {1, 4}; x = 1 is extraneous, x = 4 valid.
    orig = Eq(sqrt(x), x - 2)
    assert EquationVerifier(orig, variable=x).verify(1).status is VerificationStatus.FAILED
    assert EquationVerifier(orig, variable=x).verify(4).status is VerificationStatus.PASSED


def i_denominator_zero():
    eq = Eq(x / y, 2)
    r = EquationVerifier(eq, conditions=[non_zero(y)]).verify({x: 0, y: 0})
    assert r.status is VerificationStatus.FAILED, r.status


def i_log_domain():
    eq = Eq(log(x), 0)
    r = EquationVerifier(eq, variable=x, conditions=[positive(x)]).verify(-1)
    assert r.status is VerificationStatus.FAILED, r.status


def i_radicand_domain():
    eq = Eq(sqrt(x), 5)
    r = EquationVerifier(eq, variable=x, conditions=[non_negative(x)]).verify(-1)
    assert r.status is VerificationStatus.FAILED, r.status


# ---------------------------------------------------------------------------
# INDETERMINATE cases
# ---------------------------------------------------------------------------

def ind_unresolved_symbolic():
    # x = a  verified with candidate b (unrelated) -> difference a - b unresolved
    r = EquationVerifier(Eq(x, a), variable=x).verify(b)
    assert r.status is VerificationStatus.INDETERMINATE, r.status


def ind_bare_value_no_variable():
    # Bare scalar without an explicit variable -> must be indeterminate, never
    # silently VALID.
    r = EquationVerifier(Eq(x**2, 25)).verify(5)
    assert r.status is VerificationStatus.INDETERMINATE, r.status


def ind_non_equation():
    # Verifying against a bare expression (not an Eq) is indeterminate by design.
    r = EquationVerifier(x**2, variable=x).verify(5)
    assert r.status is VerificationStatus.INDETERMINATE, r.status


# ---------------------------------------------------------------------------
# Valid domain-satisfied cases (must be VALID, not wrongly downgraded)
# ---------------------------------------------------------------------------

def domain_valid_radicand():
    r = EquationVerifier(Eq(sqrt(x), 5), variable=x, conditions=[non_negative(x)]).verify(25)
    assert r.status is VerificationStatus.PASSED, r.status


def domain_valid_log():
    r = EquationVerifier(Eq(log(x), 0), variable=x, conditions=[positive(x)]).verify(1)
    assert r.status is VerificationStatus.PASSED, r.status


def domain_valid_denominator():
    r = EquationVerifier(Eq(x / y, 2), conditions=[non_zero(y)]).verify({x: 4, y: 2})
    assert r.status is VerificationStatus.PASSED, r.status


# ---------------------------------------------------------------------------
# Branch verification
# ---------------------------------------------------------------------------

def branch_both_valid():
    res = SquareRootTransformation().apply(Eq(x**2, 25))
    bv = BranchVerifier(Eq(x**2, 25), variable=x)
    results = bv.verify_branch_set(res.branches)
    assert len(results) == 2, len(results)
    for _, r in results:
        assert r.status is VerificationStatus.PASSED, r.status


def branch_mixed_valid_invalid():
    orig = Eq(sqrt(x), x - 2)
    roots = solve((x - (x - 2) ** 2), x)
    bv = BranchVerifier(orig, variable=x)
    results = bv.verify_branch_set(roots)
    statuses = {str(c): r.status for c, r in results}
    # 4 valid, 1 extraneous
    assert results[0][1].status is not VerificationStatus.INDETERMINATE


def branch_zero_collapse():
    res = SquareRootTransformation().apply(Eq(x**2, 0))
    bv = BranchVerifier(Eq(x**2, 0), variable=x)
    results = bv.verify_branch_set(res.branches)
    assert len(results) == 1, len(results)
    assert results[0][1].status is VerificationStatus.PASSED


def branch_zero_product():
    res = ZeroProductProperty().apply(Eq(x * (x - 2), 0))
    bv = BranchVerifier(Eq(x * (x - 2), 0), variable=x)
    results = bv.verify_branch_set(res.branches)
    assert len(results) == 2, len(results)
    for _, r in results:
        assert r.status is VerificationStatus.PASSED


# ---------------------------------------------------------------------------
# Transformation + verification composition
# ---------------------------------------------------------------------------

def compose_square_root():
    res = SquareRootTransformation().apply(Eq(x**2, 25))
    tv = TransformationVerifier(Eq(x**2, 25), variable=x)
    out = tv.verify_result(res)
    assert all(r.status is VerificationStatus.PASSED for _, r in out)


def compose_square_and_detect_extraneous():
    orig = Eq(sqrt(x), x - 2)
    res = SquareBothSides().apply(orig)
    candidates = solve(res.transformed_expression.lhs - res.transformed_expression.rhs, x)
    valid, extraneous, indet = check_extraneous_solutions(candidates, orig, variable=x)
    assert set(valid) == {4}, valid
    assert set(extraneous) == {1}, extraneous
    assert indet == ()


# ---------------------------------------------------------------------------

_COLLECTION = {
    "valid": {
        "x^2=25 +": v_x2_25_pos,
        "x^2=25 -": v_x2_25_neg,
        "x^2=0 zero": v_x2_0,
        "y^2=9 +/-3": v_y2_9,
        "(x+2)^2=9 non-bare": v_non_bare_square,
        "rational": v_rational,
        "symbolic candidate": v_symbolic_candidate,
        "multivariate": v_multivariate,
        "candidate as Eq": v_candidate_as_eq,
    },
    "invalid": {
        "x^2=25 wrong 4/6": i_x2_25_wrong,
        "extraneous sqrt": i_extraneous_sqrt,
        "denominator zero": i_denominator_zero,
        "log domain": i_log_domain,
        "radicand domain": i_radicand_domain,
    },
    "indeterminate": {
        "unresolved symbolic": ind_unresolved_symbolic,
        "bare value no variable": ind_bare_value_no_variable,
        "non-equation": ind_non_equation,
    },
    "domain_valid": {
        "radicand ok": domain_valid_radicand,
        "log arg ok": domain_valid_log,
        "denominator ok": domain_valid_denominator,
    },
    "branch": {
        "both valid": branch_both_valid,
        "mixed valid/invalid": branch_mixed_valid_invalid,
        "zero collapse": branch_zero_collapse,
        "zero-product": branch_zero_product,
    },
    "composition": {
        "square-root -> verify": compose_square_root,
        "square -> extraneous detect": compose_square_and_detect_extraneous,
    },
}


def main() -> int:
    print("================ PHASE 35.4: VERIFICATION ARCHITECTURE ================")
    total = total_pass = total_fail = 0
    failures = []
    for section, cases in _COLLECTION.items():
        print(f"== {section} ==")
        sec_pass = sec_total = 0
        for label, fn in cases.items():
            sec_total += 1
            name, ok, msg = _check(f"{section}: {label}", fn)
            if ok:
                sec_pass += 1
            else:
                failures.append(f"{name} -> {msg}")
                print(f"  FAIL {label}: {msg}")
        total += sec_total
        total_pass += sec_pass
        total_fail += sec_total - sec_pass
        print(f"  {sec_pass}/{sec_total}\n")

    print("================ SUMMARY ================")
    print(f"  {total_pass}/{total} passed")
    if total_fail:
        print(f"  {total_fail} failures")
        for f in failures:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())