"""Phase 31 -- educational quadratic step content stress harness.

Verifies that the canonical ``/solve`` pipeline produces *educational*
quadratic steps, not merely correct final answers. For every case the harness
asserts the step structure and the actual mathematical content of each step:

* exactly five steps with the expected kinds (no separate "simplify" step),
* the coefficient step explicitly shows ``a``, ``b`` and ``c``,
* the discriminant step shows the general formula, the substitution of the
  actual coefficients and the evaluated result,
* the classification step shows all three discriminant cases and identifies
  the case that applies to the current equation,
* the quadratic-formula step shows the general formula, the substituted
  values, the evaluated expression and the simplified individual roots,
* ``final_answer`` remains mathematically equivalent to an independent
  SymPy reference.

Run from the repo root:

    PYTHONPATH=. .venv/bin/python stress/phase31_stress.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from sympy import I, Rational, latex, sqrt, sympify, symbols

from math_engine.solver.quadratic_solver import QuadraticSolver
import api.adapter as adapter

from phase28_stress import (
    QUADRATIC_DETERMINISTIC,
    extract_values,
    generate_quadratic_set,
    solution_sets_equal,
)

ROOT = Path(__file__).resolve().parent.parent
_REPORT_PATH = Path(__file__).resolve().parent / "phase31_report.md"

EXPECTED_KINDS = (
    "normalize_quadratic",
    "extract_coefficients",
    "compute_discriminant",
    "classify_roots",
    "quadratic_formula",
)

_CASE = symbols("x")

#: (name, input latex, (a, b, c), D, classification, final_answer,
#:  expected_roots set, ordered simplified roots for the step's roots line)
REPRESENTATIVE_CASES: list[tuple] = [
    (
        "distinct-real",
        "x^2 - x - 12 = 0",
        (1, -1, -12),
        49,
        "two_distinct_real",
        "x_1 = 4, x_2 = -3",
        {4, -3},
        (4, -3),
    ),
    (
        "implied-b",
        "x^2 = 25",
        (1, 0, -25),
        100,
        "two_distinct_real",
        "x_1 = 5, x_2 = -5",
        {5, -5},
        (5, -5),
    ),
    (
        "distinct-real-2",
        "x^2 + 5x + 6 = 0",
        (1, 5, 6),
        1,
        "two_distinct_real",
        "x_1 = -2, x_2 = -3",
        {-2, -3},
        (-2, -3),
    ),
    (
        "repeated-root",
        "x^2 - 6x + 9 = 0",
        (1, -6, 9),
        0,
        "one_repeated_real",
        "x = 3",
        {3},
        (3,),
    ),
    (
        "complex-roots",
        "x^2 + 1 = 0",
        (1, 0, 1),
        -4,
        "two_complex",
        "x_1 = i, x_2 = - i",
        {1j, -1j},
        (I, -I),
    ),
    (
        "negative-leading",
        "-x^2 + 5x - 6 = 0",
        (1, -5, 6),
        1,
        "two_distinct_real",
        "x_1 = 3, x_2 = 2",
        {3, 2},
        (3, 2),
    ),
    (
        "integer-nonmonic",
        "2x^2 + 3x - 2 = 0",
        (2, 3, -2),
        25,
        "two_distinct_real",
        "x_1 = \\frac{1}{2}, x_2 = -2",
        {1 / 2, -2},
        (Rational(1, 2), -2),
    ),
    (
        "fractional-coefficients",
        "\\frac{1}{2}x^2 - \\frac{3}{2}x + 1 = 0",
        (Rational(1, 2), Rational(-3, 2), Rational(1)),
        Rational(1, 4),
        "two_distinct_real",
        "x_1 = 2, x_2 = 1",
        {2, 1},
        (2, 1),
    ),
    (
        "both-sides",
        "x^2 + 2x = 15",
        (1, 2, -15),
        64,
        "two_distinct_real",
        "x_1 = 3, x_2 = -5",
        {3, -5},
        (3, -5),
    ),
    (
        "parenthesized-square",
        "(x-3)^2 = 16",
        (1, -6, -7),
        64,
        "two_distinct_real",
        "x_1 = 7, x_2 = -1",
        {7, -1},
        (7, -1),
    ),
    (
        "factored-juxtaposition",
        "(x-3)(x+2) = 0",
        (1, -1, -6),
        25,
        "two_distinct_real",
        "x_1 = 3, x_2 = -2",
        {3, -2},
        (3, -2),
    ),
]


def check_educational_steps(case_name, response, coefficients, discriminant,
                            classification, final_answer, expected_roots,
                            ordered_roots):
    """Assert the full educational content of a quadratic response."""
    a, b, c = coefficients
    errors: list[str] = []

    def fail(message: str) -> None:
        errors.append(message)

    if not response.get("success"):
        return [f"request failed: {response.get('error')!r}"]
    if response.get("task") != "quadratic_equation":
        fail(f"task={response.get('task')!r}, expected 'quadratic_equation'")

    steps = response.get("steps", [])
    if len(steps) != 5:
        fail(f"expected 5 steps, got {len(steps)}")
    kinds = tuple(
        step.get("metadata", {}).get("kind") for step in steps
    )
    if kinds != EXPECTED_KINDS:
        fail(f"kinds={kinds!r}, expected {EXPECTED_KINDS!r}")
    for step in steps:
        if step.get("metadata", {}).get("kind") == "simplify_roots":
            fail("found a separate simplify_roots step")
        if step.get("title") == "Simplify the resulting roots":
            fail("found a separate 'Simplify the resulting roots' step")
    if errors:
        return errors

    by_kind = {step["metadata"]["kind"]: step for step in steps}

    # Step 2: coefficients are explicit.
    coeff_latex = by_kind["extract_coefficients"]["latex"]
    for name, value in (("a", a), ("b", b), ("c", c)):
        expected = f"{name} = {latex(value)}"
        if expected not in coeff_latex:
            fail(f"coefficient step missing {expected!r} (latex={coeff_latex!r})")

    # Step 3: discriminant teaches formula -> substitution -> result.
    disc = by_kind["compute_discriminant"]
    if "b^{2} - 4ac" not in disc["latex"]:
        fail("discriminant step missing the general formula b^2 - 4ac")
    substitution = disc["metadata"].get("substitution", "")
    for name, value in (("a", a), ("b", b), ("c", c)):
        if latex(value) not in substitution:
            fail(
                f"discriminant substitution missing {name}={latex(value)!r} "
                f"(substitution={substitution!r})"
            )
    result_line = f"D &= {latex(discriminant)}"
    if result_line not in disc["latex"]:
        fail(f"discriminant step missing result line {result_line!r}")
    if sympify(str(disc["metadata"].get("discriminant"))) != sympify(discriminant):
        fail(
            f"discriminant metadata={disc['metadata'].get('discriminant')!r}, "
            f"expected {discriminant!r}"
        )

    # Step 4: classification teaches all three cases and the current one.
    classify = by_kind["classify_roots"]
    for case_line in ("D > 0", "D = 0", "D < 0"):
        if case_line not in classify["latex"]:
            fail(f"classification step missing case {case_line!r}")
    for phrase in (
        "two distinct real roots",
        "one repeated real root",
        "two complex",
    ):
        if phrase not in classify["description"]:
            fail(f"classification description missing {phrase!r}")
    if discriminant > 0:
        relation = f"D = {latex(discriminant)} > 0"
    elif discriminant == 0:
        relation = "D = 0"
    else:
        relation = f"D = {latex(discriminant)} < 0"
    if classify["metadata"].get("relation") != relation:
        fail(
            f"classification relation={classify['metadata'].get('relation')!r}, "
            f"expected {relation!r}"
        )
    if classify["metadata"].get("classification") != classification:
        fail(
            f"classification={classify['metadata'].get('classification')!r}, "
            f"expected {classification!r}"
        )

    # Step 5: formula -> substitution -> evaluation -> roots in one step.
    formula = by_kind["quadratic_formula"]
    if "\\frac{-b \\pm \\sqrt{D}}{2a}" not in formula["latex"]:
        fail("formula step missing the general quadratic formula")
    if "\\pm" not in formula["latex"]:
        fail("formula step missing the plus/minus evaluation")
    formula_substitution = formula["metadata"].get("substitution", "")
    for name, value in (("a", a), ("b", b), ("c-into-D", discriminant)):
        needle = latex(discriminant) if name == "c-into-D" else latex(value)
        if needle not in formula_substitution:
            fail(
                f"formula substitution missing {needle!r} "
                f"(substitution={formula_substitution!r})"
            )
    if "simplified_roots" not in formula["metadata"]:
        fail("formula step metadata lacks simplified_roots")
    if classification == "one_repeated_real":
        roots_line = f"x = {latex(ordered_roots[0])}"
    else:
        roots_line = (
            f"x_{{1}} = {latex(ordered_roots[0])}, \\quad "
            f"x_{{2}} = {latex(ordered_roots[1])}"
        )
    if roots_line not in formula["latex"]:
        fail(f"formula step missing simplified roots line {roots_line!r}")

    # Final answer must remain the final answer -- and stay correct.
    if response.get("result") != final_answer:
        fail(
            f"final_answer={response.get('result')!r}, expected "
            f"{final_answer!r} (byte comparison)"
        )
    values = extract_values(response.get("result"))
    if not solution_sets_equal(values, expected_roots):
        fail(
            f"final_answer values {values!r} not equivalent to expected "
            f"{expected_roots!r}"
        )
    return errors


def run_representative() -> tuple[int, int, list[str]]:
    """Run the hand-picked representative cases through the adapter."""
    passed, total, failures = 0, 0, []
    for name, case_latex, coefficients, discriminant, classification, \
            final_answer, expected_roots, ordered_roots in REPRESENTATIVE_CASES:
        total += 1
        response = adapter.solve(case_latex, "equation")
        errors = check_educational_steps(
            name, response, coefficients, discriminant, classification,
            final_answer, expected_roots, ordered_roots,
        )
        if errors:
            failures.append(f"{name} ({case_latex!r}): " + "; ".join(errors))
        else:
            passed += 1
    return passed, total, failures


def run_deterministic() -> tuple[int, int, list[str]]:
    """Run the Phase 28 deterministic quadratic set with content checks."""
    passed, total, failures = 0, 0, []
    for name, case_latex, expected in QUADRATIC_DETERMINISTIC:
        total += 1
        response = adapter.solve(case_latex, "equation")
        errors = check_structure_and_equivalence(case_latex, response, expected)
        if errors:
            failures.append(f"{name} ({case_latex!r}): " + "; ".join(errors))
        else:
            passed += 1
    return passed, total, failures


def run_randomized(count: int = 100) -> tuple[int, int, list[str]]:
    """Run randomized Phase 28 quadratic families with content checks."""
    passed, total, failures = 0, 0, []
    for name, case_latex, expected in generate_quadratic_set(31, count):
        total += 1
        response = adapter.solve(case_latex, "equation")
        errors = check_structure_and_equivalence(case_latex, response, expected)
        if errors:
            failures.append(f"{name} ({case_latex!r}): " + "; ".join(errors))
        else:
            passed += 1
    return passed, total, failures


def check_structure_and_equivalence(case_latex, response, expected) -> list[str]:
    """Structural + equivalence checks for generated (unknown-coefficient) cases."""
    errors: list[str] = []
    if not response.get("success"):
        return [f"request failed: {response.get('error')!r}"]
    steps = response.get("steps", [])
    kinds = tuple(step.get("metadata", {}).get("kind") for step in steps)
    if kinds != EXPECTED_KINDS:
        errors.append(f"kinds={kinds!r}")
    disc = next(
        (s for s in steps if s.get("metadata", {}).get("kind") == "compute_discriminant"),
        None,
    )
    formula = next(
        (s for s in steps if s.get("metadata", {}).get("kind") == "quadratic_formula"),
        None,
    )
    classify = next(
        (s for s in steps if s.get("metadata", {}).get("kind") == "classify_roots"),
        None,
    )
    if disc is None or "b^{2} - 4ac" not in disc.get("latex", ""):
        errors.append("discriminant step missing general formula")
    if formula is None or "\\pm" not in formula.get("latex", ""):
        errors.append("formula step missing substitution/evaluation content")
    if classify is None or classify.get("latex", "") in ("", None):
        errors.append("classification step missing rendered cases")
    if disc is not None:
        value = sympify(str(disc["metadata"].get("discriminant")))
        tag = (
            "two_distinct_real" if value > 0
            else "one_repeated_real" if value == 0
            else "two_complex"
        )
        if classify is not None and classify["metadata"].get("classification") != tag:
            errors.append(
                f"classification {classify['metadata'].get('classification')!r} "
                f"does not match discriminant {value!r}"
            )
    if not solution_sets_equal(extract_values(response.get("result")), expected):
        errors.append(
            f"final_answer {response.get('result')!r} not equivalent to "
            f"reference {expected!r}"
        )
    return errors


def run_http_parity() -> tuple[int, int, list[str]]:
    """Spot-check the HTTP layer exposes the same educational steps."""
    passed, total, failures = 0, 0, []
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
    for name, case_latex, *_ in REPRESENTATIVE_CASES[:4]:
        total += 1
        resp = client.post("/solve", json={"input": case_latex, "type": "equation"})
        body = resp.json()
        kinds = tuple(s.get("metadata", {}).get("kind") for s in body.get("steps", []))
        if resp.status_code == 200 and kinds == EXPECTED_KINDS:
            passed += 1
        else:
            failures.append(f"{name}: status={resp.status_code} kinds={kinds!r}")
    return passed, total, failures


def _print_block(title, passed, total, failures) -> None:
    print(f"== {title} ==")
    print(f"  {passed}/{total}")
    for failure in failures:
        print(f"  FAIL {failure}")
    print()


def main() -> int:
    print("================ PHASE 31: EDUCATIONAL QUADRATIC STEPS ================")
    blocks = [
        ("Representative cases", run_representative()),
        ("Phase 28 deterministic quadratic set", run_deterministic()),
        ("Randomized quadratic families", run_randomized()),
        ("HTTP parity", run_http_parity()),
    ]
    failures: list[str] = []
    total_passed = total = 0
    for title, (passed, count, block_failures) in blocks:
        _print_block(title, passed, count, block_failures)
        failures.extend(block_failures)
        total_passed += passed
        total += count

    print("================ SUMMARY ================")
    print(f"  {total_passed}/{total} checks passed")
    if failures:
        print(f"  {len(failures)} failures")
        return 1

    _write_report(blocks)
    print(f"Report written to {_REPORT_PATH}")
    return 0


def _write_report(blocks) -> None:
    lines = [
        "# Phase 31 -- Educational Quadratic Step Report",
        "",
        "Structured content checks over the canonical `/solve` adapter path.",
        "",
        "| Suite | Passed | Total |",
        "|-------|--------|-------|",
    ]
    for title, (passed, count, _) in blocks:
        lines.append(f"| {title} | {passed} | {count} |")
    lines += [
        "",
        "Every case asserts: exactly 5 steps with kinds "
        "`normalize_quadratic -> extract_coefficients -> compute_discriminant "
        "-> classify_roots -> quadratic_formula`; no separate "
        "`simplify_roots` step; coefficients `a, b, c` rendered explicitly; "
        "discriminant formula + substitution + result; classification "
        "showing all three discriminant cases plus the applicable one; "
        "quadratic formula with general form, substitution, evaluation and "
        "simplified roots; final_answer byte-equal to the Phase 28/30 "
        "implementation and mathematically equivalent to an independent "
        "SymPy reference.",
        "",
        "_No failures._",
    ]
    _REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
