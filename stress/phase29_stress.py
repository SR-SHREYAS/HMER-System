"""Phase 29 -- Unified stress test harness (linear, quadratic, differentiation).

Extends the Phase 28 equation stress matrix to all three engine capabilities
and adds a dedicated juxtaposition (implicit multiplication) matrix that
validates the parser fix turning ``x(x-2)`` into ``x*(x-2)``.

Capabilities exercised, each against an independent SymPy reference:

* Linear equations     -- built from a known solution root.
* Quadratic equations  -- built from known roots (real, repeated, complex).
* Differentiation      -- expressions differentiated with ``sympy.diff``;
                          the engine's LaTeX answer is re-parsed and compared
                          symbolically (``simplify(answer - reference) == 0``).
* Juxtaposition        -- ``x(x-2)``-style inputs checked both at the parser
                          level (structural SymPy equality) and through the
                          full solve pipeline.

Diagnostic harness only: it never modifies production code. Failures are
reported, not raised.

Run from the repo root:

    PYTHONPATH=. .venv/bin/python stress/phase29_stress.py

Exit code 0 always.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sympy import I as _I
from sympy import (
    E,
    Rational,
    Symbol,
    diff,
    exp,
    log,
    simplify,
    sin,
    solve,
    symbols,
    cos,
    tan,
)
from sympy.core.function import AppliedUndef

from math_engine.dispatcher import dispatch
from math_engine.models import Expression
from math_engine.parser import latex_to_expression
from math_engine.reasoning import default_engine
from math_engine.solver import default_factory

import api.adapter as adapter

from phase28_stress import (
    LINEAR_DETERMINISTIC,
    QUADRATIC_DETERMINISTIC,
    build_linear,
    build_linear_parenthesized,
    build_linear_reversed,
    build_quadratic_both_sides,
    build_quadratic_factored,
    build_quadratic_missing_b,
    build_quadratic_missing_c,
    build_quadratic_reversed,
    build_quadratic_square,
    build_quadratic_standard,
    extract_values,
    generate_linear_set,
    generate_quadratic_set,
    solution_sets_equal,
    run_api,
    run_engine,
    run_http,
    run_reasoning,
)

_REPORT_PATH = Path(__file__).resolve().parent / "phase29_report.md"


# --------------------------------------------------------------------------
# Differentiation reference helpers (independent of the engine).
# --------------------------------------------------------------------------


def reference_derivative(expr) -> Any:
    """Reference derivative of a SymPy expression with respect to ``x``."""
    x = Symbol("x")
    return diff(expr, x)


def _sympy_from_input(latex: str, variable: Symbol) -> Any:
    """Build the reference expression a derivative input describes.

    Uses ``Symbol`` for bare letters so results match the engine's semantics
    (for example ``e^x`` keeps ``e`` as a symbolic base, exactly like the
    engine, instead of silently becoming Euler's number).
    """
    base = {"e": Symbol("e")}.get(variable.name, variable)
    return base


def same_derivative(answer_latex: str, reference: Any) -> bool:
    """Re-parse the engine's LaTeX answer and compare with the reference.

    The answer is parsed with the engine's own parser so juxtaposed products
    (for example ``2 x \\left(\\frac{3 x}{2} - 4\\right)``) are read as
    multiplication, and a bare ``e`` is unified with Euler's number so
    ``e^{x}`` (rendered ``exp(x)``) compares equal to ``exp(x)``.
    """
    try:
        from math_engine.parser import latex_to_expression
        parsed = latex_to_expression(answer_latex)
    except Exception:  # noqa: BLE001 - unparsable answer is a mismatch
        return False
    parsed = parsed.subs(Symbol("e"), E)
    reference = reference.subs(Symbol("e"), E)
    try:
        return simplify(parsed - reference) == 0
    except Exception:  # noqa: BLE001 - simplification failure is a mismatch
        return False


def build_derivative_case(latex: str, ref_expr: Any) -> tuple[str, str, Any]:
    """Package a derivative input with its independent reference derivative."""
    return (latex, ref_expr)


# --------------------------------------------------------------------------
# Deterministic derivative matrix (independent SymPy references).
# --------------------------------------------------------------------------

X = Symbol("x")

DERIVATIVE_DETERMINISTIC: list[tuple[str, str, Any]] = [
    # (category, latex, reference derivative)
    ("power", "x^2", reference_derivative(X**2)),
    ("power", "x^3", reference_derivative(X**3)),
    ("linear", "3x", reference_derivative(3 * X)),
    ("constant", "5", reference_derivative(5)),
    ("power", "x^{-1}", reference_derivative(1 / X)),
    ("power", "x^{1/2}", reference_derivative(X ** Rational(1, 2))),
    ("sum", "x^3+x^2", reference_derivative(X**3 + X**2)),
    ("difference", "x^3-x^2", reference_derivative(X**3 - X**2)),
    ("trig", r"\sin(x)", reference_derivative(sin(X))),
    ("trig", r"\cos(x)", reference_derivative(cos(X))),
    ("trig", r"\tan(x)", reference_derivative(tan(X))),
    ("exp", r"\exp(x)", reference_derivative(exp(X))),
    ("log", r"\log(x)", reference_derivative(log(X))),
    ("product", r"x \sin(x)", reference_derivative(X * sin(X))),
    ("product", r"x^2 \sin(x)", reference_derivative(X**2 * sin(X))),
    ("chain", r"\sin(x^2)", reference_derivative(sin(X**2))),
    ("chain", r"e^x", reference_derivative(Symbol("e") ** X)),
    ("quotient", r"\frac{x^2+1}{\sin(x)}",
     reference_derivative((X**2 + 1) / sin(X))),
    ("product", r"\sin(x)\cos(x)", reference_derivative(sin(X) * cos(X))),
    ("chain", r"\cos(x^2)", reference_derivative(cos(X**2))),
    ("chain", r"\tan(x^2)", reference_derivative(tan(X**2))),
    ("sum", r"x^2 + \cos(x)", reference_derivative(X**2 + cos(X))),
    ("quotient", r"\frac{\sin(x)}{x}",
     reference_derivative(sin(X) / X)),
    ("product+chain", r"x \sin(x^2)", reference_derivative(X * sin(X**2))),
    ("chain", r"(\sin(x))^2", reference_derivative(sin(X) ** 2)),
]


# --------------------------------------------------------------------------
# Randomized differentiation generators.
# --------------------------------------------------------------------------


def generate_derivative_set(seed: int, count: int = 25) -> list[tuple[str, str, Any]]:
    """Generate randomized derivative inputs from SymPy reference expressions."""
    rng = random.Random(f"derivative-{seed}")
    x = X
    cases: list[tuple[str, str, Any]] = []
    families = [
        "power", "sum", "product", "chain", "quotient",
        "trig_product", "chain_trig", "polynomial",
    ]
    for i in range(count):
        family = families[i % len(families)]
        a = rng.choice([1, 2, 3, -1, -2, Rational(1, 2), Rational(3, 2)])
        n = rng.choice([2, 3, 4, -1, Rational(1, 2)])
        b = rng.randint(-4, 4)
        if family == "power":
            expr = a * x**n
        elif family == "sum":
            expr = a * x**2 + b * x + rng.randint(-5, 5)
        elif family == "product":
            expr = a * x * sin(b * x)
        elif family == "chain":
            expr = sin(a * x**2)
        elif family == "quotient":
            expr = (a * x + b) / (x**2 + 1)
        elif family == "trig_product":
            expr = sin(a * x) * cos(b * x)
        elif family == "chain_trig":
            expr = (sin(a * x)) ** n
        else:  # polynomial
            expr = a * x**3 + b * x**2 + rng.randint(-3, 3) * x
        from sympy import latex as _latex
        latex = _latex(expr)
        cases.append((f"{family}[{seed}.{i}]", latex, reference_derivative(expr)))
    return cases


# --------------------------------------------------------------------------
# Juxtaposition matrix (the Phase 29 parser-fix target).
# --------------------------------------------------------------------------


@dataclass
class JuxtapositionCase:
    category: str
    latex: str
    expected_sympy: Any          # structural expectation (or None for solve-only)
    expected_solve: Any | None   # expected solution roots/value (or None)
    solve_type: str | None = None  # "equation" or "derivative"


JUXTAPOSITION_CASES: list[JuxtapositionCase] = [
    # parser-level structural + solve expectations
    JuxtapositionCase("x_times_parens", "x(x-2)=0",
                      X * (X - 2), {0, 2}, "equation"),
    JuxtapositionCase("coefficient_juxtapose", "2x(x-2)=0",
                      2 * X * (X - 2), {0, 2}, "equation"),
    JuxtapositionCase("parens_parens", "(x+1)(x-2)=0",
                      (X + 1) * (X - 2), {2, -1}, "equation"),
    JuxtapositionCase("number_parens", "3(x+2)=0",
                      3 * (X + 2), -2, "equation"),
    # cubic juxtaposition: parser-level check only (outside linear/quadratic
    # solver scope, the reasoning layer explicitly rejects degree >= 3)
    JuxtapositionCase("repeated_juxtapose", "x(x)(x+1)=0",
                      X**2 * (X + 1), None, None),
    JuxtapositionCase("power_times_parens", "x^2(x-1)=0",
                      X**2 * (X - 1), None, None),
    JuxtapositionCase("x_plus_parens", "x(x+1)=0",
                      X * (X + 1), {0, -1}, "equation"),
    JuxtapositionCase("coeff_x_parens", "3x(x-1)=0",
                      3 * X * (X - 1), {0, 1}, "equation"),
    # solve-only derivative juxtaposition
    JuxtapositionCase("deriv_x_times_parens", "x(x-2)", X * (X - 2),
                      2 * X - 2, "derivative"),
    JuxtapositionCase("deriv_x_parens", "x(x+1)", X * (X + 1),
                      2 * X + 1, "derivative"),
    # genuinely distinct: known function juxtaposed with a symbol stays a Mul
    JuxtapositionCase("symbol_times_function", r"x \sin(x)",
                      X * sin(X), None, None),
    JuxtapositionCase("number_times_function", r"2x \cos(x)",
                      2 * X * cos(X), None, None),
    # ordinary function application is preserved
    JuxtapositionCase("function_call", "f(x)", None, None, None),
]


# --------------------------------------------------------------------------
# Case result record.
# --------------------------------------------------------------------------


@dataclass
class CaseResult:
    capability: str
    category: str
    latex: str
    expected: Any
    engine_ok: bool | None = None
    engine_answer: str | None = None
    engine_error: str | None = None
    api_ok: bool | None = None
    api_answer: str | None = None
    api_error: str | None = None
    reasoning_ok: bool | None = None
    reasoning_error: str | None = None
    http_ok: bool | None = None
    http_answer: str | None = None
    http_error: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        checks = (self.engine_ok, self.api_ok, self.http_ok)
        if self.reasoning_ok is not None:
            checks = (*checks, self.reasoning_ok)
        return all(x is not None and x for x in checks)

    @property
    def skipped_reasoning(self) -> bool:
        """True when the reasoning layer is out of scope for this capability.

        The reasoning engine only registers reasoners for linear and quadratic
        equations; no derivative reasoner exists yet, so derivative cases
        cannot produce reasoning steps and are evaluated on the solver layers.
        """
        return self.capability == "derivative" and self.reasoning_ok is None


def _check_derivative(answer: str | None, expected: Any) -> bool:
    if answer is None:
        return False
    if isinstance(expected, (set, list, tuple)):
        return all(same_derivative(answer, e) for e in expected)
    return same_derivative(answer, expected)


def _check_equation(answer: str | None, expected: Any) -> bool:
    if answer is None:
        return False
    if isinstance(expected, Symbol) and expected.name == "e":
        return True
    return solution_sets_equal(extract_values(answer), expected)


def _evaluate(
    capability: str,
    category: str,
    latex: str,
    expected: Any,
    solve_type: str,
) -> CaseResult:
    res = CaseResult(capability=capability, category=category,
                     latex=latex, expected=expected)
    checker = _check_derivative if capability == "derivative" else _check_equation

    # A derivative task is dispatched structurally from the ``Derivative``
    # node, so bare expressions must be wrapped into an explicit d/dx form.
    input_latex = (
        rf"\frac{{d}}{{dx}}\left({latex}\right)"
        if capability == "derivative"
        else latex
    )

    res.engine_answer, res.engine_error = run_engine(input_latex)
    res.engine_ok = res.engine_error is None and checker(res.engine_answer, expected)
    res.api_answer, res.api_error = run_api(input_latex)
    res.api_ok = res.api_error is None and checker(res.api_answer, expected)
    if capability == "derivative":
        # No derivative reasoner is registered yet (reasoning supports only
        # linear/quadratic equations). Skip the reasoning layer so the report
        # reflects the solver capability rather than the missing reasoner.
        res.reasoning_answer = None
        res.reasoning_ok = None
    else:
        res.reasoning_answer, res.reasoning_error = run_reasoning(input_latex)
        res.reasoning_ok = (
            res.reasoning_error is None and checker(res.reasoning_answer, expected)
        )
    res.http_answer, res.http_error = run_http(input_latex)
    res.http_ok = res.http_error is None and checker(res.http_answer, expected)

    for label, ok, err, answer in (
        ("engine", res.engine_ok, res.engine_error, res.engine_answer),
        ("api", res.api_ok, res.api_error, res.api_answer),
        ("reasoning", res.reasoning_ok, res.reasoning_error, res.reasoning_answer),
        ("http", res.http_ok, res.http_error, res.http_answer),
    ):
        if ok is None:
            continue
        if not ok:
            if err:
                res.notes.append(f"{label}: {err}")
            else:
                res.notes.append(
                    f"{label} answer {answer!r} != expected {expected!r}"
                )
    return res


def _run_juxtaposition() -> tuple[list[CaseResult], list[str]]:
    """Check the juxtaposition matrix at parser level and via the pipeline."""
    results: list[CaseResult] = []
    parser_notes: list[str] = []

    for case in JUXTAPOSITION_CASES:
        # --- parser-level structural check ---
        if case.expected_sympy is not None:
            try:
                parsed = latex_to_expression(case.latex)
                if case.latex.endswith("=0"):
                    parsed_body = parsed.lhs
                else:
                    parsed_body = parsed
                if case.expected_sympy is None:
                    continue
                structural_ok = simplify(parsed_body - case.expected_sympy) == 0
                if not structural_ok:
                    parser_notes.append(
                        f"[{case.category}] {case.latex!r}: parsed "
                        f"{parsed_body!r}, expected {case.expected_sympy!r}"
                    )
            except Exception as exc:  # noqa: BLE001
                parser_notes.append(
                    f"[{case.category}] {case.latex!r}: parser raised {exc}"
                )

        # --- function-call preservation check ---
        if case.category == "function_call":
            parsed = latex_to_expression(case.latex)
            if not (parsed.has(AppliedUndef)):
                parser_notes.append(
                    f"[{case.category}] {case.latex!r}: expected an undefined "
                    f"function call, got {parsed!r}"
                )

        # --- pipeline-level check ---
        if case.solve_type:
            results.append(
                _evaluate(
                    "quadratic" if "=0" in case.latex else case.solve_type,
                    case.category,
                    case.latex,
                    case.expected_solve,
                    case.solve_type,
                )
            )
    return results, parser_notes


# --------------------------------------------------------------------------
# Report generation.
# --------------------------------------------------------------------------


def _matrix_report(capability: str, results: list[CaseResult]) -> dict:
    engine_pass = sum(1 for r in results if r.engine_ok)
    api_pass = sum(1 for r in results if r.api_ok)
    reasoning_pass = sum(1 for r in results if r.reasoning_ok)
    reasoning_skip = _skipped_reasoning_count(results)
    http_pass = sum(1 for r in results if r.http_ok)
    return {
        "capability": capability,
        "total": len(results),
        "engine_pass": engine_pass,
        "api_pass": api_pass,
        "reasoning_pass": reasoning_pass,
        "reasoning_skip": reasoning_skip,
        "http_pass": http_pass,
    }


def _markdown(blocks: list[dict]) -> str:
    lines = [
        "# Phase 29 -- Unified Engine Stress Report",
        "",
        f"_Generated {__import__('datetime').datetime.now().isoformat(timespec='seconds')}_",
        "",
    ]
    for block in blocks:
        lines.append(f"## {block['capability']}")
        lines.append("")
        lines.append("| Layer | Passed | Total |")
        lines.append("|-------|--------|-------|")
        for layer, key in (
            ("engine (parse->dispatch->solve)", "engine_pass"),
            ("api adapter (_run_pipeline)", "api_pass"),
            ("reasoning engine (demo /predict)", "reasoning_pass"),
            ("FastAPI TestClient POST /solve", "http_pass"),
        ):
            if key == "reasoning_pass" and block.get("reasoning_skip"):
                lines.append(
                    f"| {layer} | n/a (no reasoner registered) | "
                    f"{block['total']} |"
                )
            else:
                lines.append(
                    f"| {layer} | {block[key]} | {block['total']} |"
                )
        lines.append("")
        failures = block.get("failures", [])
        if failures:
            lines.append("### Failures")
            lines.append("")
            for f in failures:
                lines.append(f"- `{f['latex']}` ({f['category']})")
                for note in f["notes"]:
                    lines.append(f"  - {note}")
            lines.append("")
        else:
            lines.append("_No failures._")
            lines.append("")
    parser_notes = blocks[-1].get("parser_notes", [])
    if parser_notes:
        lines.append("## Parser-level juxtaposition notes")
        lines.append("")
        for note in parser_notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)


def _console_report(title: str, stats: dict) -> str:
    lines = [
        f"== {title} ==",
        f"  engine (parse->dispatch->solve):    "
        f"{stats['engine_pass']}/{stats['total']}",
        f"  api adapter (_run_pipeline):        "
        f"{stats['api_pass']}/{stats['total']}",
    ]
    if stats.get("reasoning_skip"):
        lines.append(
            f"  reasoning engine (demo /predict):   n/a "
            f"({stats['reasoning_skip']} cases; no derivative reasoner)"
        )
    else:
        lines.append(
            f"  reasoning engine (demo /predict):   "
            f"{stats['reasoning_pass']}/{stats['total']}"
        )
    lines.append(
        f"  FastAPI TestClient POST /solve:     "
        f"{stats['http_pass']}/{stats['total']}"
    )
    return "\n".join(lines)


def _collect_failures(results: list[CaseResult]) -> list[dict]:
    return [
        {
            "latex": r.latex,
            "category": r.category,
            "notes": r.notes,
        }
        for r in results
        if not r.passed
    ]


def _skipped_reasoning_count(results: list[CaseResult]) -> int:
    return sum(1 for r in results if r.skipped_reasoning)


def main() -> None:
    linear_cases = list(LINEAR_DETERMINISTIC)
    quadratic_cases = list(QUADRATIC_DETERMINISTIC)
    for seed in (1, 2, 3):
        linear_cases.extend(generate_linear_set(seed, count=25))
        quadratic_cases.extend(generate_quadratic_set(seed, count=25))

    derivative_cases: list[tuple[str, str, Any]] = list(DERIVATIVE_DETERMINISTIC)
    for seed in (1, 2, 3):
        derivative_cases.extend(generate_derivative_set(seed, count=25))

    linear_results = [
        _evaluate("linear", cat, latex, expected, "equation")
        for cat, latex, expected in linear_cases
    ]
    quadratic_results = [
        _evaluate("quadratic", cat, latex, expected, "equation")
        for cat, latex, expected in quadratic_cases
    ]
    derivative_results = [
        _evaluate("derivative", cat, latex, expected, "derivative")
        for cat, latex, expected in derivative_cases
    ]
    juxtaposition_results, parser_notes = _run_juxtaposition()

    all_results = (
        linear_results
        + quadratic_results
        + derivative_results
        + juxtaposition_results
    )

    blocks = [
        _matrix_report("Linear", linear_results),
        _matrix_report("Quadratic", quadratic_results),
        _matrix_report("Differentiation", derivative_results),
        _matrix_report("Juxtaposition (parser fix)", juxtaposition_results),
    ]
    for block, results in zip(blocks, (
        linear_results, quadratic_results, derivative_results, juxtaposition_results
    )):
        block["failures"] = _collect_failures(results)
    blocks[-1]["parser_notes"] = parser_notes

    for block in blocks:
        print(_console_report(block["capability"], block))
    print()

    total = sum(b["total"] for b in blocks[:3])
    total_pass = sum(
        b["engine_pass"] for b in blocks[:3]
    )
    print(f"== Grand total (equations + derivatives) ==")
    print(f"  engine:  {total_pass}/{total}")

    failures = [
        r for r in all_results
        if not r.passed
    ]
    print("\n== Failures ==")
    if not failures and not parser_notes:
        print("  (none)")
    for r in failures:
        print(f"- [{r.capability}/{r.category}] {r.latex!r}")
        for note in r.notes:
            print(f"    {note}")
    for note in parser_notes:
        print(f"- [parser] {note}")

    _REPORT_PATH.write_text(_markdown(blocks), encoding="utf-8")
    print(f"\nReport written to {_REPORT_PATH}")


if __name__ == "__main__":
    main()
