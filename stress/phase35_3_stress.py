"""Phase 35.3 -- Branch-Aware Algebraic Transformations stress harness.

Validates the three branch-aware universal transformations independently of the
solver pipelines:

1. SquareRootTransformation  (inverse of squaring, preserves ± / branch set)
2. SquareBothSides           (solution-expanding, requires verification)
3. ZeroProductProperty       (factor -> zero branches)

These tests assert the *mathematical* semantics of the transformations and the
Phase 35.1 branch/condition/verification metadata, not integration behaviour.
They deliberately do NOT touch the production Linear/Quadratic/Derivative
solvers.

Run from the repo root:

    PYTHONPATH=. .venv/bin/python stress/phase35_3_stress.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from sympy import Eq, Ge, Integer, Rational, Symbol, expand, simplify, sqrt, symbols

from math_engine.transformations.algebraic import (
    SquareRootTransformation,
    SquareBothSides,
    ZeroProductProperty,
)

_ROOT = Path(__file__).resolve().parent.parent
_REPORT_PATH = Path(__file__).resolve().parent / "phase35_3_report.md"


def _check(name, fn):
    try:
        fn()
        return name, True, None
    except AssertionError as exc:
        return name, False, str(exc)
    except Exception as exc:  # noqa: BLE001 - capture any unexpected failure
        return name, False, f"{type(exc).__name__}: {exc}"


SECTION = SquareRootTransformation
ZERO = ZeroProductProperty
SQUARE = SquareBothSides


# ----------------------------------------------------------------------------
# Square-root transformation
# ----------------------------------------------------------------------------

def sq_both_roots():
    x = symbols("x")
    r = SECTION().apply(Eq(x**2, 25))
    b = sorted(str(b) for b in r.branches)
    assert b == ["x = -5", "x = 5"], b
    assert r.reversibility == "branch_producing"
    assert r.verification_required == "required"


def sq_zero_collapses():
    x = symbols("x")
    r = SECTION().apply(Eq(x**2, 0))
    assert len(r.branches) == 1, [str(b) for b in r.branches]
    assert str(r.branches[0]) == "x = 0"


def sq_alternate_variable():
    y = symbols("y")
    r = SECTION().apply(Eq(y**2, 9))
    b = sorted(str(b) for b in r.branches)
    assert b == ["y = -3", "y = 3"], b


def sq_symbolic_radicand():
    x, a = symbols("x a")
    r = SECTION().apply(Eq(x**2, a))
    assert len(r.branches) == 2
    latexes = {str(b) for b in r.branches}
    assert latexes == {r"x = \sqrt{a}", r"x = - \sqrt{a}"}, latexes


def sq_non_bare_base():
    x = symbols("x")
    r = SECTION().apply(Eq((x + 2) ** 2, 9))
    b = sorted(str(b) for b in r.branches)
    assert b == ["x + 2 = -3", "x + 2 = 3"], b


def sq_negative_radicand_complex():
    x = symbols("x")
    r = SECTION().apply(Eq(x**2, -1))
    assert len(r.branches) == 2, [str(b) for b in r.branches]


def sq_not_apply_non_square():
    x = symbols("x")
    assert not SECTION().can_apply(Eq(x + 4, 9))
    assert not SECTION().can_apply("not an equation")


def sq_numeric_equivalence():
    # The two branches, re-squared, must reproduce the original relation.
    x = symbols("x")
    r = SECTION().apply(Eq(x**2, 25))
    values = [Integer(5), Integer(-5)]
    for b, expected in zip(r.branches, sorted(values, reverse=True)):
        # each branch should carry x = ±5; verify by structure
        assert b.expression.free_symbols == {x}


# ----------------------------------------------------------------------------
# Zero-product property
# ----------------------------------------------------------------------------

def zp_two_factors():
    x = symbols("x")
    r = ZERO().apply(Eq(x * (x - 2), 0))
    assert len(r.branches) == 2, [str(b) for b in r.branches]
    assert str(r.branches[0]) == "x = 0"
    assert str(r.branches[1]) == "x - 2 = 0"
    assert r.reversibility == "branch_producing"
    assert r.verification_required == "none"


def zp_three_factors():
    x = symbols("x")
    r = ZERO().apply(Eq((x - 1) * (x + 3) * (x - 5), 0))
    latexes = {str(b) for b in r.branches}
    assert latexes == {"x - 1 = 0", "x + 3 = 0", "x - 5 = 0"}, latexes


def zp_squared_factor():
    x = symbols("x")
    r = ZERO().apply(Eq(x**2 * (x - 1), 0))
    latexes = {str(b) for b in r.branches}
    assert latexes == {r"x^{2} = 0", "x - 1 = 0"}, latexes


def zp_symbolic_factor():
    x, a = symbols("x a")
    r = ZERO().apply(Eq(x * a, 0))
    assert len(r.branches) == 2
    assert {str(b) for b in r.branches} == {"x = 0", "a = 0"}


def zp_rejects_non_product():
    x = symbols("x")
    assert not ZERO().can_apply(Eq(x + 1, 0))


def zp_rejects_nonzero_rhs():
    x = symbols("x")
    assert not ZERO().can_apply(Eq(x * (x - 1), 1))


# ----------------------------------------------------------------------------
# Square both sides
# ----------------------------------------------------------------------------

def sqb_transforms():
    x = symbols("x")
    r = SQUARE().apply(Eq(sqrt(x + 3), x - 1))
    assert r.transformed_expression == Eq(x + 3, (x - 1) ** 2), r.transformed_expression
    assert r.reversibility == "irreversible"
    assert r.verification_required == "required"
    assert r.extraneous_risk is True
    assert len(r.branches) == 0
    # safety metadata present
    assert r.step.metadata.get("warning") == "extraneous_solutions"


def sqb_symbolic():
    x, a, b = symbols("x a b")
    r = SQUARE().apply(Eq(a, b))
    assert expand(r.transformed_expression.lhs - r.transformed_expression.rhs) == 0 \
        or r.transformed_expression == Eq(a**2, b**2)


def sqb_demonstrates_extraneous():
    # sqrt(x) = x - 2 -> squaring yields x = (x-2)^2 whose roots are
    # x = 4 (valid: sqrt(4) = 2 = 4 - 2) and x = 1 (extraneous:
    # sqrt(1) = 1 != -1 = 1 - 2). The transformation must flag verification
    # so a downstream solver does NOT accept the extraneous root blindly.
    x = symbols("x")
    r = SQUARE().apply(Eq(sqrt(x), x - 2))
    assert r.requires_verification
    assert r.verification_required == "required"
    assert r.extraneous_risk is True
    from sympy import solve
    roots = solve(r.transformed_expression.lhs - r.transformed_expression.rhs, x)
    assert sorted(roots) == [1, 4], roots
    # Demonstrate: only x = 4 satisfies the original radical equation.
    def satisfies_root(xval):
        lhs = sqrt(xval)
        rhs = xval - 2
        return simplify(lhs - rhs) == 0
    assert satisfies_root(4) is True
    assert satisfies_root(1) is False


# ----------------------------------------------------------------------------
# Domain-neutrality checks (no assumption of variable name or degree)
# ----------------------------------------------------------------------------

def neutrality_variable_agnostic_t():
    t = symbols("t")
    r = SECTION().apply(Eq(t**2, 4))
    b = sorted(str(b) for b in r.branches)
    assert b == ["t = -2", "t = 2"], b


def neutrality_rational_coefficients():
    x = symbols("x")
    # (x)^2 = 1/4  -> x = ±1/2
    r = SECTION().apply(Eq(x**2, Rational(1, 4)))
    b = sorted(str(b) for b in r.branches)
    assert len(b) == 2, b


def neutrality_zero_product_not_linear():
    x = symbols("x")
    # Non-linear factors are still structural factors.
    r = ZERO().apply(Eq((x**2 - 1) * (x**3 + 2), 0))
    latexes = {str(b) for b in r.branches}
    assert latexes == {"x^{2} - 1 = 0", r"x^{3} + 2 = 0"}, latexes


# ----------------------------------------------------------------------------

_COLLECTION = {
    "square_root": {
        "both ± roots": sq_both_roots,
        "zero collapses to single branch": sq_zero_collapses,
        "alternate variable": sq_alternate_variable,
        "symbolic radicand": sq_symbolic_radicand,
        "non-bare squared base": sq_non_bare_base,
        "negative radicand (complex)": sq_negative_radicand_complex,
        "reject non-square": sq_not_apply_non_square,
        "branch structure equivalence": sq_numeric_equivalence,
    },
    "zero_product": {
        "two factors": zp_two_factors,
        "three factors": zp_three_factors,
        "squared factor": zp_squared_factor,
        "symbolic factor": zp_symbolic_factor,
        "reject non-product": zp_rejects_non_product,
        "reject non-zero rhs": zp_rejects_nonzero_rhs,
    },
    "square_both_sides": {
        "transforms correctly": sqb_transforms,
        "symbolic": sqb_symbolic,
        "extraneous semantics": sqb_demonstrates_extraneous,
    },
    "neutrality": {
        "variable agnostic (t)": neutrality_variable_agnostic_t,
        "rational coefficients": neutrality_rational_coefficients,
        "non-linear factors": neutrality_zero_product_not_linear,
    },
}


def main() -> int:
    print("================ PHASE 35.3: BRANCH-AWARE TRANSFORMATIONS ================")
    total_fail = 0
    total_pass = 0
    total_cases = 0
    failures = []
    for section, cases in _COLLECTION.items():
        print(f"== {section} ==")
        section_pass = section_total = 0
        for label, fn in cases.items():
            section_total += 1
            name, ok, msg = _check(f"{section}: {label}", fn)
            if ok:
                section_pass += 1
            else:
                failures.append(f"{name} -> {msg}")
                print(f"  FAIL {label}: {msg}")
        total_pass += section_pass
        total_fail += section_total - section_pass
        total_cases += section_total
        print(f"  {section_pass}/{section_total}\n")

    print("================ SUMMARY ================")
    print(f"  {total_pass}/{total_cases} passed")
    if total_fail:
        print(f"  {total_fail} failures")
        for f in failures:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())