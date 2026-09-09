# Phase 30 — Architecture Cleanup & Production-Path Audit Report

Branch: `feature/expression-solver`
Date: 2026-08-11

## Summary

Phase 30 audited the production path of the three frozen capabilities (linear
equations, quadratic equations, differentiation), identified one architectural
defect — linear equations produced **0 steps** on the canonical `/solve` path
because the step-by-step reasoning lived only behind the legacy `/predict`
reasoning engine — and fixed it by wiring the existing, validated linear rules
into `EquationSolver`. No mathematical behaviour was changed: every `final_answer`
is byte-for-byte identical to the pre-change engine (verified across the full
Phase 28 + Phase 29 stress matrices, 443 + 304 cases).

## Changes

1. **`math_engine/solver/equation_solver.py`** — `EquationSolver.solve()` now
   runs the shared linear rule pipeline (`ExpandRule` → `MultiplyBothSidesRule`
   → `MoveVariableRule` → `MoveConstantRule` → `DivideCoefficientRule`) via
   `RuleEngine` and bookends the produced steps with "Present the equation" and
   "Final answer" steps. The authoritative `final_answer` is still produced by
   SymPy's `solve()` and is unchanged. Non-linear and multi-symbol equations
   (`x^3 - x = 0`, `x + y = 5`) gracefully fall back to 0 steps.

2. **`math_engine/reasoning/equation_reasoner.py`** — `EquationReasoner` is now
   a pure relay (like `QuadraticReasoner`): it returns the solver-generated
   steps unchanged and performs no mathematics. This removes the second,
   competing mathematical implementation for linear reasoning and makes the
   solver the single source of truth on both the canonical `/solve` path and
   the legacy `/predict` path.

3. **`hmer_ux/script.js`** — removed `renderPredictionDetails()`, a function
   with no call sites (verified dead).

## Architecture Findings

- **Canonical production path** (what the frontend actually consumes):
  browser → `script.js` → `/predict` (uses only `data.sequence` + `data.latex`)
  → `/solve` (`type: "derivative"`) → `demo.py:solve_proxy` → `api.adapter.solve`
  → `_run_pipeline` (normalize → `latex_to_expression` → `_to_problem` →
  `dispatch` → `default_factory.build` → `solver.solve` → `_solution_response`).
  Steps are rendered from `data.steps` via `renderSolveSuccess`/`buildStepNodes`.

- **`/solve` does NOT use `ReasoningEngine`.** Steps come directly from the
  solvers' rule pipelines. This is the correct architecture and is preserved.

- **`ReasoningEngine` + `EquationReasoner`/`QuadraticReasoner` are legacy
  compatibility** — wired only to the demo `/predict` math fields, which the
  frontend ignores. They remain as relays so `/predict` still returns coherent
  JSON; they are kept intentionally (not deleted) per Phase 30 constraints.

- **Pre-existing defect fixed in this phase:** linear equations produced 0
  steps on `/solve` while quadratic produced 6 and derivative produced 3. Now
  linear equations produce 3–5 steps (present + rule applications + answer).

- **No derivative reasoner exists** and none was created (derivative steps come
  from `DerivativeSolver`'s own rule pipeline). `x^2` bare still raises
  `UnknownTaskError` on `/solve`; the adapter wraps bare expressions into
  `Derivative`, so this is only reachable through the engine/reasoning path.

## Cleanup Performed

- `EquationReasoner` converted from a competing rule-driving implementation to
  a step relay (single source of truth = solver rule pipeline).
- Dead frontend `renderPredictionDetails()` removed.

## Cleanup NOT Performed + Reason

- `ReasoningEngine`/`EquationReasoner`/`QuadraticReasoner` not deleted: they
  are legacy compatibility for `/predict`, which must keep working.
- `/predict` response fields `expression`/`task`/`answer`/`steps` not removed:
  they are part of the demo API contract and harmless; the frontend just does
  not consume them.
- No `DerivativeReasoner` added (would be symmetry, not a real requirement).
- `demo.py` `/predict` kept as-is (HMER recognition dependency).
- Adapter contract (`_SUPPORTED_TYPES`, `_PREFERRED_VARIABLES`, structural
  routing, timeout thread) left untouched.

## Production Path Verification

- Canonical `/solve` (FastAPI TestClient, `type="derivative"`):
  - `3x-4=2` → 4 steps `['present','isolate','divide','answer']`, result `2`
  - `2(x+3)=10` → 5 steps (expand path), result `2`
  - `x/3+2=5` → 4 steps (multiply-through path), result `9`
  - `x^2=25` → 6 quadratic steps, result `x_1 = 5, x_2 = -5`
  - `\frac{d}{dx}(x^3)` → 3 derivative steps, result `3 x^{2}`
- Legacy `/predict` reasoning still yields steps for every linear/quadratic case.

## Regression

| Suite | Linear | Quadratic | Derivative | Juxtaposition |
|-------|--------|-----------|------------|---------------|
| Phase 28 stress (engine) | 147/147 | 149/149 | — | — |
| Phase 28 stress (adapter) | 147/147 | 149/149 | — | — |
| Phase 28 stress (reasoning) | 147/147 | 149/149 | — | — |
| Phase 28 stress (HTTP) | 147/147 | 149/149 | — | — |
| Phase 29 stress (engine) | 97/97 | 99/99 | 100/100 | 8/8 |
| Phase 29 stress (adapter) | 97/97 | 99/99 | 100/100 | 8/8 |
| Phase 29 stress (reasoning) | 97/97 | 99/99 | n/a* | n/a* |
| Phase 29 stress (HTTP) | 97/97 | 99/99 | 100/100 | 8/8 |
| `api.test_api` | exit 0 | | | |
| `integration/test_ocr_to_api.py` | 6 pre-existing `dbl_backslash` parsing failures only | | | |
| `latex_parser` / `base_rule` doctests | clean import, no failures | | | |
| `node --check` on `script.js`/`animation.js` | OK | | | |

\* No derivative reasoner exists; these are skipped by design.

## Three-Capability Status

- **Linear equations:** READY — steps now flow on the canonical `/solve` path.
- **Quadratic equations:** READY — 6 in-solver steps, unchanged.
- **Differentiation:** READY — 3 in-solver steps, unchanged.

## Future Capability Readiness

Adding a new capability (e.g. integration/limits) follows the established
pattern: register a `BaseSolver` subclass against `default_factory`, run its
rule pipeline in-solver to produce steps, and (optionally) register a relay
reasoner for `/predict` parity. A new rule lives under
`math_engine/reasoning/rules/` and is exported from that package's `__init__.py`.

## Problems Encountered

- `python -m doctest math_engine/parser/latex_parser.py` fails at import due to
  relative imports; run doctests programmatically instead (`doctest.testmod`
  after importing the module). No actual doctest blocks exist.
- `api.test_api` reports `passed=False` for equations: this is pre-existing
  verification metadata (symbolic-substitution verification is not implemented
  for equations), not a solve failure — confirmed identical before this change.
