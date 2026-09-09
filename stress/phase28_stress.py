"""Phase 28 -- Linear & Quadratic solver stress test harness.

Independent generalized stress test for the existing linear and quadratic
equation-solving capabilities. Generates equations programmatically from
parameters (known solutions / known roots), renders them to LaTeX, pushes them
through the REAL parser -> dispatcher -> solver path (and the API adapter
path), and compares the engine's solution set against an independently
computed reference.

This is a diagnostic harness only: it never modifies production code and never
tries to make the engine pass.

Run from the repo root:

    PYTHONPATH=. .venv/bin/python stress/phase28_stress.py

Exit code 0 always (failures are reported, not raised).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from sympy import I as _I
from sympy import Rational, Symbol, simplify, solve, symbols
from sympy.parsing.latex import parse_latex

from math_engine.dispatcher import dispatch
from math_engine.models import Expression
from math_engine.parser import latex_to_expression
from math_engine.reasoning import default_engine
from math_engine.solver import SolverError, default_factory

import api.adapter as adapter

# --------------------------------------------------------------------------
# Reference computation (independent of the engine).
# --------------------------------------------------------------------------


def _render_latex(eq) -> str:
    """Render a SymPy equality to the LaTeX the parser will receive."""
    from sympy import latex
    return latex(eq)


def reference_linear(a, b, c, d):
    """Expected solution of a*x + b = c*x + d, computed directly."""
    from sympy import symbols as _s
    x = _s("x")
    return solve((a - c) * x + (b - d), x)[0]


def reference_quadratic(a, b, c):
    """Reference roots of a*x**2 + b*x + c = 0 (independent of engine)."""
    from sympy import symbols as _s
    x = _s("x")
    return set(solve(a * x**2 + b * x + c, x))


def reference_quadratic_from_roots(a, r1, r2):
    """Reference roots given a leading coefficient and the two roots."""
    return {r1, r2}


# --------------------------------------------------------------------------
# Linear generators.
# --------------------------------------------------------------------------


def build_linear(category, a, b, c, root):
    """Construct a linear equation from parameters with known solution.

    Returns (sympy_eq, expected_solution).
    """
    from sympy import Eq
    x = symbols("x")
    a, b, c, root = (Rational(v) for v in (a, b, c, root))
    d = (a - c) * root + b  # ensures x = root solves a*x+b = c*x+d
    eq = Eq(a * x + b, c * x + d)
    return eq, root


def build_linear_parenthesized(a, k, c, root):
    """Construct a*(x + k) = c*x + d with known solution root."""
    from sympy import Eq
    x = symbols("x")
    a, k, c, root = (Rational(v) for v in (a, k, c, root))
    d = (a - c) * root + a * k
    eq = Eq(a * (x + k), c * x + d)
    return eq, root


def build_linear_frac(den, b, root):
    """Construct x/den + b = d with known solution root."""
    from sympy import Eq
    x = symbols("x")
    den, b, root = (Rational(v) for v in (den, b, root))
    d = root / den + b
    eq = Eq(x / den + b, d)
    return eq, root


# --------------------------------------------------------------------------
# Quadratic generators.
# --------------------------------------------------------------------------


def build_quadratic_standard(a, r1, r2):
    """a*(x-r1)*(x-r2) expanded to a*x**2 + b*x + c = 0."""
    from sympy import Eq
    x = symbols("x")
    a = Rational(a)
    b = -a * (r1 + r2)
    c = a * r1 * r2
    eq = Eq(a * x**2 + b * x + c, 0)
    return eq, {r1, r2}


def build_quadratic_both_sides(a, r1, r2):
    """Terms on both sides: a*x**2 + b*x = -c."""
    from sympy import Eq
    x = symbols("x")
    a = Rational(a)
    b = -a * (r1 + r2)
    c = a * r1 * r2
    eq = Eq(a * x**2 + b * x, -c)
    return eq, {r1, r2}


def build_quadratic_reversed(a, r1, r2):
    """Reversed equality: -c = a*x**2 + b*x."""
    from sympy import Eq
    x = symbols("x")
    a = Rational(a)
    b = -a * (r1 + r2)
    c = a * r1 * r2
    eq = Eq(-c, a * x**2 + b * x)
    return eq, {r1, r2}


def build_quadratic_factored(a, r1, r2):
    """a*(x-r1)*(x-r2) = 0 in factored form (roots must be nonzero)."""
    from sympy import Eq
    x = symbols("x")
    eq = Eq(Rational(a) * (x - r1) * (x - r2), 0)
    return eq, {r1, r2}


def build_quadratic_square(a, r1, r2):
    """a*(x - k)**2 = a*((r1-r2)/2)**2 with k=(r1+r2)/2 (roots r1, r2)."""
    from sympy import Eq
    x = symbols("x")
    a = Rational(a)
    k = Rational(r1 + r2, 2)
    m = Rational(a * (r1 - r2) ** 2, 4)
    eq = Eq(a * (x - k) ** 2, m)
    return eq, {r1, r2}


def build_quadratic_missing_b(a, r):
    """a*x**2 = a*r**2  (missing linear term, roots r and -r)."""
    from sympy import Eq
    x = symbols("x")
    a = Rational(a)
    eq = Eq(a * x**2, a * r**2)
    return eq, {r, -r}


def build_quadratic_missing_c(a, r):
    """a*x*(x - r) = 0 -> a*x**2 - a*r*x = 0 (missing constant, roots 0, r)."""
    from sympy import Eq
    x = symbols("x")
    a = Rational(a)
    eq = Eq(a * x**2 - a * r * x, 0)
    return eq, {0, r}


def build_quadratic_complex(a, b, c):
    """General a*x**2 + b*x + c = 0 with complex roots (D < 0)."""
    from sympy import Eq
    x = symbols("x")
    eq = Eq(a * x**2 + b * x + c, 0)
    return eq, reference_quadratic(a, b, c)


# --------------------------------------------------------------------------
# Pipeline runners (real parser/dispatcher/solver path).
# --------------------------------------------------------------------------


@dataclass
class CaseResult:
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


def run_engine(latex: str) -> tuple[str | None, str | None]:
    """Parse, dispatch, solve. Returns (final_answer or None, error or None)."""
    try:
        parsed = latex_to_expression(latex)
        expr = Expression(raw_latex=latex, sympy_expression=parsed)
        classified = dispatch(expr)
        solver = default_factory.build(classified)
        solution = solver.solve(classified)
        return solution.final_answer, None
    except Exception as exc:  # noqa: BLE001 - capture any failure
        return None, f"{type(exc).__name__}: {str(exc)[:140]}"


def run_api(latex: str) -> tuple[str | None, str | None]:
    """Run through the API adapter pipeline."""
    try:
        resp = adapter._run_pipeline(latex)
        if resp.get("success"):
            return resp.get("result"), None
        return None, resp.get("error") or "adapter returned success=False"
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {str(exc)[:140]}"


def run_http(latex: str) -> tuple[str | None, str | None]:
    """Run through the FastAPI TestClient POST /solve endpoint."""
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)
        resp = client.post("/solve", json={"input": latex, "type": "equation"})
        body = resp.json()
        if resp.status_code == 200 and body.get("success"):
            return body.get("result"), None
        return None, body.get("error") or f"HTTP {resp.status_code}"
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {str(exc)[:140]}"


def run_reasoning(latex: str) -> tuple[str | None, str | None]:
    """Run solve + reasoning engine (the demo /predict path).

    Returns the final ``solution.final_answer`` (the value the demo /predict
    route actually reports) when reasoning steps were produced, or an error.
    """
    try:
        parsed = latex_to_expression(latex)
        expr = Expression(raw_latex=latex, sympy_expression=parsed)
        classified = dispatch(expr)
        solver = default_factory.build(classified)
        solution = solver.solve(classified)
        reasoned = default_engine.generate(solution)
        if not reasoned.steps:
            return None, "reasoning produced no steps"
        return solution.final_answer, None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {str(exc)[:140]}"


# --------------------------------------------------------------------------
# Solution-set comparison (mathematical, not string).
# --------------------------------------------------------------------------


def extract_values(answer: str) -> list:
    """Turn an engine final_answer string into a list of SymPy values.

    Handles linear ('2', '5/2', '-3') and quadratic
    ('x_1 = 5, x_2 = -5', 'x = 1', 'x_1 = i, x_2 = - i') formats.
    """
    if answer is None:
        return []
    if "=" not in answer:
        try:
            return [parse_latex(answer)]
        except Exception:  # noqa: BLE001
            return []
    values: list = []
    for part in answer.split(","):
        if "=" in part:
            value = part.split("=", 1)[1].strip()
        else:
            value = part.strip()
        if not value:
            continue
        try:
            values.append(parse_latex(value))
        except Exception:  # noqa: BLE001
            continue
    return values


def same_value(a, b) -> bool:
    a = _as_sympy_value(a)
    b = _as_sympy_value(b)
    try:
        return simplify(a - b) == 0
    except Exception:  # noqa: BLE001
        return False


def _as_sympy_value(value):
    """Map Symbol('i') from parse_latex to the imaginary unit."""
    if isinstance(value, Symbol):
        if value.name == "i":
            return _I
        return value
    if isinstance(value, (int, Rational)):
        return value
    try:
        return value.subs({Symbol("i"): _I})
    except Exception:  # noqa: BLE001
        return value


def solution_sets_equal(engine_values: list, expected: Any) -> bool:
    """Compare the engine's extracted values against the expected set."""
    if isinstance(expected, set):
        expected_list = list(expected)
    elif isinstance(expected, (list, tuple)):
        expected_list = list(expected)
    else:
        expected_list = [expected]

    if len(engine_values) != len(expected_list):
        return False
    remaining = list(expected_list)
    for ev in engine_values:
        for i, ex in enumerate(remaining):
            if same_value(ev, ex):
                del remaining[i]
                break
    return len(remaining) == 0


# --------------------------------------------------------------------------
# Deterministic matrices (generalized, not copies of solver doctests).
# --------------------------------------------------------------------------

LINEAR_DETERMINISTIC: list[tuple[str, str, object]] = [
    # (category, latex, expected)
    ("basic", "3x-4=2", 2),
    ("basic", "2x+5=13", 4),
    ("parenthesized", "2(x+3)=10", 2),
    ("both_sides", "3x+7=x-5", -6),
    ("negative_coeff", "5-2x=11", -3),
    ("rational_coeff", "(3/2)x+4=10", 4),
    ("fraction", "x/3+2=5", 9),
    ("parenthesized+both", "2(x-4)+3=x+7", 12),
    ("reversed", "13=2x+5", 4),
    ("reversed", "7=5x-3", 2),
    ("zero_root", "12=3x", 4),
    ("zero_root", "0=5x", 0),
    ("zero_root", "x=0", 0),
    ("negative_solution", "-x=5", -5),
    ("rational_solution", "10=2x+5", Rational(5, 2)),
    ("rational_coeff", "2x/3=8", 12),
    ("rational_coeff", "(3/4)x=9", 12),
    ("multi_term", "x/2+x/3=5", 6),
    ("multi_term", "2x+3x=10", 2),
    ("multi_term", "3x-2x+7=9", 2),
    ("both_sides", "x-5=3x+7", -6),
    ("move_terms", "5=x", 5),
]

QUADRATIC_DETERMINISTIC: list[tuple[str, str, object]] = [
    # (category, latex, expected roots)
    ("standard", "x^2=25", {5, -5}),
    ("standard", "x^2+5x+6=0", {-2, -3}),
    ("reversed", "5=x^2+4x", {1, -5}),
    ("standard", "2x^2+3x-5=0", {1, Rational(-5, 2)}),
    ("parenthesized", "3(x+2)^2=12", {0, -4}),
    ("factored", "(x-3)(x+2)=0", {3, -2}),
    ("rational", "(1/2)x^2-3x+1=0", {3 + 7**Rational(1, 2), 3 - 7**Rational(1, 2)}),
    ("both_sides", "x^2+2x=8", {2, -4}),
    ("missing_b", "x^2-4=0", {2, -2}),
    ("complex", "x^2+1=0", {_I, -_I}),
    ("missing_b", "2x^2=8", {2, -2}),
    ("repeated", "x^2-2x+1=0", {1}),
    ("repeated", "x^2=0", {0}),
    ("missing_b", "4x^2=9", {Rational(3, 2), Rational(-3, 2)}),
    ("negative_leading", "-x^2+4=0", {2, -2}),
    ("missing_c", "x^2+x=0", {0, -1}),
    ("missing_c", "x^2-5x=0", {5, 0}),
    ("factored", "3(x-1)(x+2)=0", {1, -2}),
    ("repeated", "x^2-4x+4=0", {2}),
    ("rational", "(2/3)x^2+1/2=0", {
        _I * 3**Rational(1, 2) / 2,
        -_I * 3**Rational(1, 2) / 2,
    }),
    ("parenthesized", "2(x-1)^2-8=0", {3, -1}),
    ("complex", "x^2+2x+5=0", {-1 + 2 * _I, -1 - 2 * _I}),
    ("variable_t", "t^2-3t+2=0", {2, 1}),
    ("variable_y", "9y^2-16=0", {Rational(4, 3), Rational(-4, 3)}),
]


# --------------------------------------------------------------------------
# Randomized generators.
# --------------------------------------------------------------------------


def generate_linear_set(seed: int, count: int = 25) -> list[tuple[str, str, object]]:
    """Generate randomized linear equations from parameters.

    Equations are built from (a, b, c, root) with the solution root chosen
    first; the constant on the right is then derived so the equation provably
    has that root. Structural families are cycled.
    """
    rng = random.Random(f"linear-{seed}")
    cases: list[tuple[str, str, object]] = []
    families = ["standard", "both_sides", "reversed", "negative", "rational",
                "parenthesized", "both_sides", "fraction"]
    for i in range(count):
        family = families[i % len(families)]
        # coefficient / constant ranges, positive and negative
        a = rng.randint(1, 9) * rng.choice([1, -1])
        c = rng.randint(1, 9) * rng.choice([1, -1])
        if a == c:  # would produce the degenerate identity a*x+b == a*x+b
            c = c + (1 if c > 0 else -1)
        b = rng.randint(-9, 9)
        root = rng.randint(-9, 9)
        if root == 0 and rng.random() < 0.5:
            root = rng.choice([2, 3, -4, 5, 7, -6])

        if family == "fraction":
            den = rng.choice([2, 3, 4, 6])
            eq, expected = build_linear_frac(den, b, root)
            latex = _render_latex(eq)
            cases.append((f"fraction[{seed}.{i}]", latex, expected))
            continue
        if family == "parenthesized":
            k = rng.randint(-5, 5)
            pa, pc = a, c
            if pa == pc:
                pc = pc + (1 if pc > 0 else -1)
            eq, expected = build_linear_parenthesized(pa, k, pc, root)
            latex = _render_latex(eq)
            cases.append((f"parenthesized[{seed}.{i}]", latex, expected))
            continue
        if family == "rational":
            # rational leading coefficient p/q
            den = rng.choice([2, 3, 4])
            a_r = Rational(rng.randint(1, 8), den) * rng.choice([1, -1])
            d = (a_r - c) * root + b
            from sympy import Eq
            x = symbols("x")
            eq = Eq(a_r * x + b, c * x + d)
            latex = _render_latex(eq)
            cases.append((f"rational[{seed}.{i}]", latex, root))
            continue

        if family == "reversed":
            eq, expected = build_linear_reversed(a, b, c, root)
            latex = _render_latex(eq)
            cases.append((f"reversed[{seed}.{i}]", latex, expected))
            continue

        eq, expected = build_linear(family, a, b, c, root)
        latex = _render_latex(eq)
        cases.append((f"{family}[{seed}.{i}]", latex, expected))
    return cases


def build_linear_reversed(a, b, c, root):
    """Construct c*x + d = a*x + b (RHS/LHS swapped) with known root."""
    from sympy import Eq
    x = symbols("x")
    a, b, c, root = (Rational(v) for v in (a, b, c, root))
    d = (a - c) * root + b
    eq = Eq(c * x + d, a * x + b)
    return eq, root


def generate_quadratic_set(seed: int, count: int = 25) -> list[tuple[str, str, object]]:
    """Generate randomized quadratic equations from known roots.

    Root pairs are chosen first; each family then arranges the same roots into
    a structurally different equation. Reference roots come directly from the
    construction parameters (never from the engine).
    """
    rng = random.Random(f"quadratic-{seed}")
    cases: list[tuple[str, str, object]] = []
    families = ["standard", "both_sides", "reversed", "factored", "square",
                "missing_b", "missing_c", "standard"]
    for i in range(count):
        family = families[i % len(families)]
        a = rng.choice([1, 2, 3, -1, -2, Rational(1, 2), Rational(3, 2)])
        r1 = rng.randint(-8, 8)
        r2 = rng.randint(-8, 8)

        if family == "repeated" or (r1 == r2 and rng.random() < 0.4):
            r2 = r1
        if family == "missing_b":
            eq, expected = build_quadratic_missing_b(a, r1 if r1 != 0 else 3)
            cases.append((f"missing_b[{seed}.{i}]", _render_latex(eq), expected))
            continue
        if family == "missing_c":
            eq, expected = build_quadratic_missing_c(a, r1 if r1 != 0 else 4)
            cases.append((f"missing_c[{seed}.{i}]", _render_latex(eq), expected))
            continue
        if family == "factored" and r1 != 0 and r2 != 0:
            eq, expected = build_quadratic_factored(a, r1, r2)
            cases.append((f"factored[{seed}.{i}]", _render_latex(eq), expected))
            continue
        if family == "square":
            k = rng.randint(-4, 4)
            r1 = k + rng.randint(1, 4)
            r2 = k - rng.randint(1, 4)
            eq, expected = build_quadratic_square(a, r1, r2)
            cases.append((f"square[{seed}.{i}]", _render_latex(eq), expected))
            continue
        if family == "both_sides":
            eq, expected = build_quadratic_both_sides(a, r1, r2)
            cases.append((f"both_sides[{seed}.{i}]", _render_latex(eq), expected))
            continue
        if family == "reversed":
            eq, expected = build_quadratic_reversed(a, r1, r2)
            cases.append((f"reversed[{seed}.{i}]", _render_latex(eq), expected))
            continue
        eq, expected = build_quadratic_standard(a, r1, r2)
        cases.append((f"standard[{seed}.{i}]", _render_latex(eq), expected))
    return cases


# --------------------------------------------------------------------------
# Reporting.
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Hidden-assumption probes (diagnostic, no assertions -- reports only).
# --------------------------------------------------------------------------


def run_hidden_assumption_probes() -> None:
    """Probe structural assumptions not covered by the main matrix."""
    print("\n== Hidden-assumption probes (diagnostic only) ==")

    probes = [
        ("non-x variable (linear)", "2t+3=7", "linear", 2),
        ("non-x variable (quadratic)", "9y^2-16=0", "quadratic", {Rational(4, 3), -Rational(4, 3)}),
        ("variable z", "3z-1=8", "linear", 3),
        ("large coefficients", "1234x-567=1001", "linear", Rational(1568, 1234)),
        ("decimal-ish rational", "0.5x+1=3", "linear", 4),
        ("leading -1 quadratic", "-x^2+5x-6=0", "quadratic", {2, 3}),
        ("nested parens linear", "2(3x-1)+4=5x+7", "linear", 5),
        ("nested parens quadratic", "2(3x-1)^2-8=0", "quadratic", {
            Rational(1 + 2, 3), Rational(1 - 2, 3),
        }),
        ("x(x-2)=0 juxtaposition", "x(x-2)=0", "quadratic", {0, 2}),
        ("2x(x-2)=0 juxtaposition", "2x(x-2)=0", "quadratic", {0, 2}),
        ("(x)(x-2)=0 parenthesized", "(x)(x-2)=0", "quadratic", {0, 2}),
        ("x^2=25 non-zero b implied", "x^2-25=0", "quadratic", {5, -5}),
        ("coeff -1 linear", "-x+3=1", "linear", 2),
        ("equation with e", "e^x=1", "unsupported", None),
        ("two variables", "x+y=5", "unsupported", None),
    ]

    for name, latex, eq_type, expected in probes:
        answer, err = run_engine(latex)
        if err:
            print(f"  {name:34s} {latex!r:22s} -> ERROR {err[:70]}")
            continue
        if eq_type == "unsupported":
            print(f"  {name:34s} {latex!r:22s} -> answer {answer!r} (outside scope)")
            continue
        values = extract_values(answer or "")
        ok = solution_sets_equal(values, expected)
        status = "OK" if ok else f"ANSWER {answer!r} (expected {expected})"
        print(f"  {name:34s} {latex!r:22s} -> {status}")


def main() -> None:
    linear_cases: list[tuple[str, str, object]] = list(LINEAR_DETERMINISTIC)
    quadratic_cases: list[tuple[str, str, object]] = list(QUADRATIC_DETERMINISTIC)

    for seed in (1, 2, 3, 4, 42):
        linear_cases.extend(generate_linear_set(seed, count=25))
        quadratic_cases.extend(generate_quadratic_set(seed, count=25))

    linear_results = [_evaluate(cat, latex, expected, "linear")
                      for cat, latex, expected in linear_cases]
    quadratic_det = [_evaluate(cat, latex, expected, "quadratic")
                     for cat, latex, expected in QUADRATIC_DETERMINISTIC]
    quadratic_rand = [_evaluate(cat, latex, expected, "quadratic")
                      for cat, latex, expected in
                      list(quadratic_cases)[len(QUADRATIC_DETERMINISTIC):]]

    print(_report("Linear", linear_results))
    print(_report("Quadratic", quadratic_det + quadratic_rand))
    print(_report("Quadratic (deterministic only)", quadratic_det))
    print(_report("Quadratic (randomized only)", quadratic_rand))

    _print_failures(linear_results + quadratic_det + quadratic_rand)
    run_hidden_assumption_probes()


def _evaluate(category: str, latex: str, expected: object, eq_type: str) -> CaseResult:
    res = CaseResult(category=category, latex=latex, expected=expected)
    res.engine_answer, res.engine_error = run_engine(latex)
    res.engine_ok = (
        res.engine_error is None
        and solution_sets_equal(extract_values(res.engine_answer or ""), expected)
    )
    res.api_answer, res.api_error = run_api(latex)
    res.api_ok = (
        res.api_error is None
        and solution_sets_equal(extract_values(res.api_answer or ""), expected)
    )
    res.reasoning_answer, res.reasoning_error = run_reasoning(latex)
    res.reasoning_ok = (
        res.reasoning_error is None
        and solution_sets_equal(
            extract_values(res.reasoning_answer or ""), expected
        )
    )
    res.http_answer, res.http_error = run_http(latex)
    res.http_ok = (
        res.http_error is None
        and solution_sets_equal(extract_values(res.http_answer or ""), expected)
    )
    if not res.engine_ok:
        if res.engine_error:
            res.notes.append(f"engine: {res.engine_error}")
        else:
            res.notes.append(f"engine answer {res.engine_answer!r} != expected {expected!r}")
    if not res.api_ok:
        if res.api_error:
            res.notes.append(f"api: {res.api_error}")
        else:
            res.notes.append(f"api answer {res.api_answer!r} != expected {expected!r}")
    if not res.reasoning_ok:
        if res.reasoning_error:
            res.notes.append(f"reasoning: {res.reasoning_error}")
        else:
            res.notes.append(f"reasoning answer {res.reasoning_answer!r} != expected {expected!r}")
    if not res.http_ok:
        if res.http_error:
            res.notes.append(f"http: {res.http_error}")
        else:
            res.notes.append(f"http answer {res.http_answer!r} != expected {expected!r}")
    return res


def _report(title: str, results: list[CaseResult]) -> str:
    engine_pass = sum(1 for r in results if r.engine_ok)
    api_pass = sum(1 for r in results if r.api_ok)
    reasoning_pass = sum(1 for r in results if r.reasoning_ok)
    http_pass = sum(1 for r in results if r.http_ok)
    lines = [
        f"== {title} ==",
        f"  engine (parse->dispatch->solve):    {engine_pass}/{len(results)}",
        f"  api adapter (_run_pipeline):        {api_pass}/{len(results)}",
        f"  reasoning engine (demo /predict):   {reasoning_pass}/{len(results)}",
        f"  FastAPI TestClient POST /solve:     {http_pass}/{len(results)}",
    ]
    return "\n".join(lines)


def _print_failures(results: list[CaseResult]) -> None:
    print("\n== Failures ==")
    failures = [
        r
        for r in results
        if not (r.engine_ok and r.api_ok and r.reasoning_ok and r.http_ok)
    ]
    if not failures:
        print("  (none)")
        return
    for r in failures:
        print(f"- [{r.category}] {r.latex!r}")
        for note in r.notes:
            print(f"    {note}")


if __name__ == "__main__":
    main()
