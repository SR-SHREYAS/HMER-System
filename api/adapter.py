"""Integration adapter between HTTP inputs and the math engine.

The adapter is the only translation layer the API uses. It normalizes raw
LaTeX, parses it through the stable :mod:`math_engine` parser, wraps the
result into the task-specific SymPy form the engine expects, invokes the
solver pipeline, and serializes the produced solution into the JSON contract
the API exposes.

Every failure -- parsing errors, unsupported expressions, runtime failures --
is converted into a structured error response instead of an uncaught
exception, so callers always receive a well-formed payload.
"""

from __future__ import annotations

import re
import threading
from typing import Any

from sympy import Derivative, Eq, Symbol

from math_engine.dispatcher import DispatcherError, dispatch
from math_engine.models import Expression
from math_engine.parser import (
    EmptyLatexError,
    InvalidLatexError,
    LatexParserError,
    UnsupportedLatexError,
    latex_to_expression,
)
from math_engine.solver import SolverError, default_factory

#: Request types accepted by the API. ``"derivative"`` stays supported for
#: backward compatibility, but final routing is structural (see ``_to_problem``):
#: an equality in the parsed input wins over the requested type.
_SUPPORTED_TYPES: tuple[str, ...] = ("derivative", "equation")

#: Symbols preferred as the differentiation variable, in order.
_PREFERRED_VARIABLES: tuple[str, ...] = ("x", "t", "u", "z")

_ENGINE_ERRORS: tuple[type[BaseException], ...] = (
    LatexParserError,
    EmptyLatexError,
    InvalidLatexError,
    UnsupportedLatexError,
    DispatcherError,
    SolverError,
)


class UnsupportedProblemTypeError(Exception):
    """Raised when the requested problem type is not supported yet."""


def solve(latex: str, problem_type: str = "derivative") -> dict[str, Any]:
    """Solve a LaTeX math problem and return the API response mapping.

    Parameters
    ----------
    latex :
        The raw LaTeX string describing the problem.
    problem_type :
        The kind of problem to solve. ``"derivative"`` and ``"equation"``
        are accepted; other values raise :class:`UnsupportedProblemTypeError`.
        Routing to the right solver is structural (based on the parsed SymPy
        object), so an equality input is always solved as an equation even
        when the request type says ``"derivative"``.

    Returns
    -------
    dict
        A JSON-safe response following the API contract: ``success``,
        ``result``, ``steps``, ``verification`` and ``error``.

    Raises
    ------
    UnsupportedProblemTypeError
        If ``problem_type`` is not supported.
    """
    if problem_type not in _SUPPORTED_TYPES:
        return _error_response(
            f"Unsupported problem type {problem_type!r}; supported: "
            f"{', '.join(_SUPPORTED_TYPES)}."
        )
    try:
        return _solve_with_timeout(latex)
    except _ENGINE_ERRORS as exc:
        return _error_response(f"{type(exc).__name__}: {exc}")
    except Exception as exc:  # noqa: BLE001 - last-resort guardrail
        return _error_response(f"Unexpected failure: {exc}")


#: Wall-clock budget for a single solve, in seconds.
_SOLVE_TIMEOUT_SECONDS: int = 10


def _solve_with_timeout(latex: str) -> dict[str, Any]:
    """Run the engine pipeline with a hard time budget.

    Pathological inputs (for example deeply nested ``factorial`` chains
    produced by punctuation like ``!!!``) can make SymPy's simplifier run for
    an unreasonably long time. Running the solve in a worker thread with a
    join timeout guarantees the API always returns promptly instead of
    hanging on garbage input.
    """
    output: dict[str, Any] = {"success": False}
    worker_error: list[tuple[type[BaseException], str]] = []

    def _run() -> None:
        try:
            output.clear()
            output.update(_run_pipeline(latex))
        except Exception as exc:  # noqa: BLE001 - preserve original exception
            worker_error.append((type(exc), str(exc)))

    worker = threading.Thread(target=_run, daemon=True)
    worker.start()
    worker.join(timeout=_SOLVE_TIMEOUT_SECONDS)
    if worker.is_alive():
        return _error_response(
            f"Timed out after {_SOLVE_TIMEOUT_SECONDS}s (input too complex "
            "or unsupported)."
        )
    if worker_error:
        exc_type, message = worker_error[0]
        raise exc_type(message)
    return output


def _run_pipeline(latex: str) -> dict[str, Any]:
    """Parse, classify and solve ``latex`` through the math engine."""
    normalized = _normalize_latex(latex)
    parsed = latex_to_expression(normalized)
    sympy_expression = _to_problem(parsed)
    expression = Expression(
        raw_latex=normalized, sympy_expression=sympy_expression
    )
    classified = dispatch(expression)
    solver = default_factory.build(classified)
    solution = solver.solve(classified)
    return _solution_response(classified, solution)


def solve_to_dict(latex: str, problem_type: str = "derivative") -> dict[str, Any]:
    """Alias of :func:`solve` kept for explicit call-sites.

    The core API entry point is a single function; this name simply mirrors
    the response-dictionary shape for readability.
    """
    return solve(latex, problem_type=problem_type)


#: Bare-function names normalized to their backslash forms, in order.
_FUNCTION_NAMES: tuple[str, ...] = (
    "sin",
    "cos",
    "tan",
    "sec",
    "csc",
    "cot",
    "sinh",
    "cosh",
    "tanh",
    "exp",
    "ln",
    "log",
    "sqrt",
)

#: Matches a bare function name immediately followed by an opening brace or
#: parenthesis (optionally separated by spaces) so it can be backslash-scaped.
#: The negative lookbehind prevents re-escaping names that already carry a
#: backslash (real OCR output always emits ``\\sin``), which would otherwise
#: turn a valid ``\\sin(x)`` into an unparsable ``\\\\sin(x)``.
_FUNCTION_PATTERN = re.compile(
    r"(?<!\\)\b(" + "|".join(_FUNCTION_NAMES) + r")\s*([\(])"
)


def _normalize_latex(latex: str) -> str:
    """Lightweight normalization of raw input LaTeX.

    Strips surrounding whitespace, collapses runs of internal whitespace to a
    single space, and prefixes bare function names (``sin(x)``, ``cos(x)`` …)
    with a backslash so the engine's parser treats them as functions. Even
    though this is basic cleanup, function rewriting is deliberately the only
    grammar-aware step here -- heavier parsing is delegated to the engine's
    parser.
    """
    if not latex:
        raise EmptyLatexError("Input LaTeX is empty.")
    return _FUNCTION_PATTERN.sub(r"\\\1\2", " ".join(latex.split()))


def _to_problem(parsed: Any) -> Any:
    """Return the parsed SymPy object in the form the engine expects.

    Classification is purely structural, based on the actual SymPy type:

    * An already-parsed ``Eq`` (from ``x^2 = 25``, ``3x - 4 = 2``) is passed
      through unchanged and is dispatched as :class:`TaskType.EQUATION` -- the
      existing :class:`EquationSolver` then routes linear vs quadratic.
    * An already-parsed ``Derivative`` (from ``\\frac{d}{dx} x^2``) is passed
      through unchanged and is dispatched as :class:`TaskType.DERIVATIVE`.
    * Any other bare expression (``x^2``, ``sin(x)``, ``x^x``) keeps the
      historical derivative API behavior and is wrapped into
      ``Derivative(expr, variable)``.

    An equality is never wrapped into a derivative.
    """
    if isinstance(parsed, (Eq, Derivative)):
        return parsed
    variable = _select_variable(parsed)
    return Derivative(parsed, variable)


def _select_variable(expression: Any) -> Symbol:
    """Pick the differentiation variable for a wrapped expression.

    Prefers ``x``, then other conventional variable names, then the first
    free symbol; falls back to ``x`` when no free symbol exists.
    """
    free = sorted(expression.free_symbols, key=lambda symbol: symbol.name)
    for name in _PREFERRED_VARIABLES:
        for symbol in free:
            if symbol.name == name:
                return symbol
    return free[0] if free else Symbol("x")


def _solution_response(classified: Expression, solution: Any) -> dict[str, Any]:
    """Serialize a classified expression and its solution to the response."""
    verification = dict(solution.metadata.get("verification", {}))
    return {
        "success": True,
        "result": solution.final_answer,
        "input": classified.raw_latex,
        "task": classified.task.value if classified.task else None,
        "steps": [_serialize_step(step) for step in solution.steps],
        "verification": {
            "passed": bool(verification.get("passed", False)),
            "method": verification.get("method", "symbolic"),
            "samples": verification.get("samples", 0),
        },
        "error": None,
    }


def _serialize_step(step: Any) -> dict[str, Any]:
    """Convert a reasoning Step model into a JSON-safe dictionary."""
    return {
        "title": step.title,
        "description": step.description,
        "latex": step.latex,
        "metadata": _json_safe(dict(step.metadata)),
    }


def _json_safe(value: Any) -> Any:
    """Recursively convert a value into a JSON-serializable form.

    Keeps primitive values intact and stringifies every other object (SymPy
    expressions, special numbers) so the API always returns valid JSON.
    """
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _error_response(message: str) -> dict[str, Any]:
    """Build a well-formed failure response."""
    return {
        "success": False,
        "result": "",
        "input": None,
        "task": None,
        "steps": [],
        "verification": {
            "passed": False,
            "method": "symbolic",
            "samples": 0,
        },
        "error": message,
    }


__all__ = [
    "UnsupportedProblemTypeError",
    "solve",
    "solve_to_dict",
]