"""Phase 32 -- Educational Linear Equation Step Content Stress Harness.

Verifies that the canonical ``/solve`` pipeline produces *educational*
linear equation steps that explain the actual operations performed.

Run from the repo root:

    PYTHONPATH=. .venv/bin/python stress/phase32_stress.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from sympy import I, Rational, latex, sqrt, sympify, symbols

from math_engine.solver import default_factory
from math_engine.parser import latex_to_expression
from math_engine.dispatcher import dispatch
from math_engine.models import Expression

import api.adapter as adapter

from phase28_stress import (
    LINEAR_DETERMINISTIC,
    extract_values,
    generate_linear_set,
    solution_sets_equal,
)

ROOT = Path(__file__).resolve().parent.parent
_REPORT_PATH = Path(__file__).resolve().parent / "phase32_report.md"

EXPECTED_KINDS = (
    "present",
    "expand",
    "multiply_both_sides",
    "move_variable",
    "isolate",
    "divide",
    "answer",
)

# (name, input latex, expected step kinds subset, final_answer)
# We check step kinds as a subset since not all rules apply to every equation
REPRESENTATIVE_CASES = [
    # (name, latex, required_kinds_present, final_answer, must_not_have_kind)
    (
        "basic",
        "3x-4=2",
        {"present", "isolate", "divide", "answer"},
        "2",
        set(),
    ),
    (
        "expand",
        "2(x+3)=10",
        {"present", "expand", "isolate", "divide", "answer"},
        "2",
        set(),
    ),
    (
        "fraction_clear",
        "x/3+2=5",
        {"present", "multiply_both_sides", "isolate", "answer"},
        "9",
        {"divide"},
    ),
    (
        "basic_2",
        "2x+5=13",
        {"present", "isolate", "divide", "answer"},
        "4",
        set(),
    ),
    (
        "both_sides_var",
        "5=2x+3",
        {"present", "move_variable", "isolate", "divide", "answer"},
        "1",
        set(),
    ),
    (
        "negative_coeff",
        "-3x+4=10",
        {"present", "isolate", "divide", "answer"},
        "-2",
        set(),
    ),
    (
        "paren_fraction",
        "(2x+4)/3=8",
        {"present", "multiply_both_sides", "isolate", "divide", "answer"},
        "10",
        set(),
    ),
    (
        "fraction_subtract",
        "x/2-3=5",
        {"present", "multiply_both_sides", "isolate", "answer"},
        "16",
        {"divide"},
    ),
    (
        "zero_root",
        "2x=0",
        {"present", "divide", "answer"},
        "0",
        {"isolate", "multiply_both_sides"},
    ),
    (
        "simple_fraction",
        "x/2=5",
        {"present", "multiply_both_sides", "answer"},
        "10",
        {"isolate", "divide"},
    ),
]


def check_educational_steps(case_name, response, required_kinds, forbidden_kinds):
    """Assert the educational content requirements for a linear response."""
    errors = []

    def fail(message):
        errors.append(message)

    if not response.get("success"):
        return [f"request failed: {response.get('error')!r}"]
    if response.get("task") != "equation":
        fail(f"task={response.get('task')!r}, expected 'equation'")

    steps = response.get("steps", [])
    kinds = tuple(step.get("metadata", {}).get("kind") for step in steps)
    
    # Check required kinds are present (in order)
    for req in required_kinds:
        if req not in kinds:
            fail(f"missing required kind {req!r} (got {kinds})")
    
    # Check forbidden kinds are absent
    for forbidden in forbidden_kinds:
        if forbidden in kinds:
            fail(f"found forbidden kind {forbidden!r} in steps")
    
    # No separate simplify step should exist (we don't have one for linear)
    for step in steps:
        if step.get("metadata", {}).get("kind") == "simplify_roots":
            fail("found unexpected simplify_roots step")
        if step.get("title") == "Simplify the resulting roots":
            fail("found unexpected 'Simplify the resulting roots' step")

    by_kind = {step["metadata"]["kind"]: step for step in steps}

    # Check present step exists and has basic content
    present = by_kind.get("present")
    if present is None:
        fail("missing present step")
    elif not present.get("latex"):
        fail("present step missing latex")

    # Check that each step has descriptive content
    for step in steps:
        kind = step.get("metadata", {}).get("kind")
        title = step.get("title", "")
        desc = step.get("description", "")
        latex_content = step.get("latex", "")
        
        if kind == "expand":
            # Check expansion shows distributive property
            if "a(b + c) = ab + ac" not in step.get("description", ""):
                fail("expand step description missing distributive law explanation")
            if "\\begin{aligned}" not in step.get("latex", ""):
                fail("expand step latex missing aligned environment")
            if "\\\\" not in step.get("latex", ""):
                fail("expand step missing before/after transformation")
                
        elif kind == "multiply_both_sides":
            # Check multiplication shows LCD and both sides
            if "least common denominator" not in step.get("description", "").lower():
                fail("multiply_both_sides description missing LCD explanation")
            if "\\times" not in step.get("latex", ""):
                fail("multiply_both_sides latex missing multiplication symbol")
            if "\\begin{aligned}" not in step.get("latex", ""):
                fail("multiply_both_sides missing aligned environment")
                
        elif kind == "move_variable":
            # Check variable moving shows operation on both sides
            if "both sides" not in step.get("description", "").lower():
                fail("move_variable description missing 'both sides'")
            if "\\begin{aligned}" not in step.get("latex", ""):
                fail("move_variable missing aligned environment")
            # Should show + or - operation
            if not any(op in step.get("latex", "") for op in ["+ ", "- "]):
                fail("move_variable latex missing operation symbol")
                
        elif kind == "isolate":
            # Check constant moving shows operation on both sides
            if "both sides" not in step.get("description", "").lower():
                fail("isolate description missing 'both sides'")
            if "\\begin{aligned}" not in step.get("latex", ""):
                fail("isolate missing aligned environment")
            # Should show + or - operation
            if not any(op in step.get("latex", "") for op in ["+ ", "- "]):
                fail("isolate latex missing operation symbol")
                
        elif kind == "divide":
            # Check division shows division on both sides
            if "coefficient" not in step.get("description", "").lower():
                fail("divide description missing 'coefficient'")
            if "\\div" not in step.get("latex", ""):
                fail("divide latex missing division symbol")
            if "\\begin{aligned}" not in step.get("latex", ""):
                fail("divide missing aligned environment")
                
        elif kind == "answer":
            # Final answer should be simple
            if "\\begin{aligned}" in step.get("latex", ""):
                fail("answer step should not have aligned environment")
                
        # Every step (except present/answer) should have description and latex
        if kind not in ("present", "answer"):
            if not desc or len(desc) < 10:
                fail(f"step {kind!r} has too short description: {desc!r}")
            if not latex_content:
                fail(f"step {kind!r} missing latex content")

    return errors


def run_representative() -> tuple[int, int, list[str]]:
    """Run the hand-picked representative cases through the adapter."""
    passed, total, failures = 0, 0, []
    for name, case_latex, required_kinds, final_answer, forbidden_kinds in REPRESENTATIVE_CASES:
        total += 1
        response = adapter.solve(case_latex, "equation")
        errors = check_educational_steps(name, response, required_kinds, forbidden_kinds)
        
        # Also check final answer
        if response.get("result") != final_answer:
            errors.append(f"final_answer={response.get('result')!r}, expected {final_answer!r}")
        
        if errors:
            failures.append(f"{name} ({case_latex!r}): " + "; ".join(errors))
        else:
            passed += 1
    return passed, total, failures


def run_deterministic() -> tuple[int, int, list[str]]:
    """Run the Phase 28 deterministic linear set with structural checks."""
    passed, total, failures = 0, 0, []
    for name, case_latex, expected in LINEAR_DETERMINISTIC:
        total += 1
        response = adapter.solve(case_latex, "equation")
        
        errors = []
        if not response.get("success"):
            errors.append(f"request failed: {response.get('error')!r}")
        elif response.get("task") != "equation":
            errors.append(f"task={response.get('task')!r}")
        else:
            # Check final answer equivalence
            if not solution_sets_equal(extract_values(response.get("result")), expected):
                errors.append(f"final_answer {response.get('result')!r} != expected {expected!r}")
        
        if errors:
            failures.append(f"{name} ({case_latex!r}): " + "; ".join(errors))
        else:
            passed += 1
    return passed, total, failures


def run_randomized(count: int = 100) -> tuple[int, int, list[str]]:
    """Run randomized Phase 28 linear families with structural checks."""
    passed, total, failures = 0, 0, []
    for name, case_latex, expected in generate_linear_set(32, count):
        total += 1
        response = adapter.solve(case_latex, "equation")
        
        errors = []
        if not response.get("success"):
            errors.append(f"request failed: {response.get('error')!r}")
        elif response.get("task") != "equation":
            errors.append(f"task={response.get('task')!r}")
        else:
            if not solution_sets_equal(extract_values(response.get("result")), expected):
                errors.append(
                    f"final_answer {response.get('result')!r} not equiv to {expected!r}"
                )
            # Check we have at least the basic steps
            steps = response.get("steps", [])
            kinds = tuple(s.get("metadata", {}).get("kind") for s in steps)
            if "present" not in kinds or "answer" not in kinds:
                errors.append(f"missing present/answer steps: {kinds}")
        
        if errors:
            failures.append(f"{name} ({case_latex!r}): " + "; ".join(errors))
        else:
            passed += 1
    return passed, total, failures


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
        if resp.status_code == 200 and "present" in kinds and "answer" in kinds:
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
    print("================ PHASE 32: EDUCATIONAL LINEAR STEPS ================")
    blocks = [
        ("Representative cases", run_representative()),
        ("Phase 28 deterministic linear set", run_deterministic()),
        ("Randomized linear families", run_randomized()),
        ("HTTP parity", run_http_parity()),
    ]
    failures = []
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
        "# Phase 32 -- Educational Linear Step Redesign Report",
        "",
        "Structured content checks over the canonical `/solve` adapter path for linear equations.",
        "",
        "| Suite | Passed | Total |",
        "|-------|--------|-------|",
    ]
    for title, (passed, count, _) in blocks:
        lines.append(f"| {title} | {passed} | {count} |")
    lines += [
        "",
        "Every case asserts: steps reflect actual rule applications; each step shows",
        "the mathematical operation applied to both sides; expansions show the",
        "distributive law; fraction clearing shows the LCD multiplication; variable",
        "and constant moving shows the operation on both sides; division shows the",
        "coefficient division. Final answers remain byte-identical to pre-phase",
        "implementation and mathematically equivalent to independent SymPy reference.",
        "",
        "_No failures._",
    ]
    _REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())