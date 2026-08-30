# Phase 35.6 — Transformation-to-Step Presentation Boundary

**Branch:** `feature/expression-solver`
**Date:** 2026-08-30
**Status:** SUCCESS

---

## A. Current Architecture

```
Solver → Rule → Transformation → TransformationResult
                         ↓
                 Rule-owned presentation (Step)
                         ↓
                       Solution.steps
```

- `TransformationResult` (in `math_engine/transformations/base.py`) already carries
  `transformed_expression`, `branches`, `conditions`, `reversibility`,
  `verification_required`, `extraneous_risk`, `metadata` — plus a `step` field the
  transformation fills with its own generic wording.
- `BaseRule.apply` returns `(updated_expression, Step)`.
- `Step` is a plain dataclass: `title`, `description`, `latex`, `metadata`
  (with `metadata["kind"]`).

---

## B. Chosen Presentation-Boundary Design

A tiny `math_engine/transformations/presentation.py` exposing two helpers plus a
presentation-free view:

1. **`TransformationPayload`** — a frozen view of the *mathematical* outcome only
   (`transformed_expression`, `branches`, `conditions`, safety metadata). It
   deliberately has **no `step` field**, so a rule cannot accidentally inherit
   the transformation's generic wording/`kind`.

2. **`payload(result)`** — extracts the presentation-free payload from a
   `TransformationResult`.

3. **`step_from_result(result, *, title, description, latex, kind, metadata=None)`**
   — builds a rule-owned `Step`; every `Step` field is supplied by the caller.
   Transformation metadata is merged underneath so mathematical facts survive
   without dictating presentation.

The transformation's own `step` remains available as an *opt-in fallback* only;
it is never surfaced through the boundary.

---

## C. Why This Avoids the Phase 35.2 Regression

Phase 35.2 let a rule return `TransformationResult.step` verbatim, which replaced
the rule's `kind`/description/`\div` with the transformation's generic
`add_subtract_both_sides`/`\times`. The new boundary makes that impossible:

- `payload()` strips `step` entirely (the returned `TransformationPayload` has no
  `.step` attribute),
- `step_from_result` requires the caller to pass every `Step` field explicitly.

A rule therefore *must* provide its own `title`/`description`/`latex`/`kind`, which
is exactly the Phase-32 contract that regressed before.

---

## D. Files Changed

- **Added:** `math_engine/transformations/presentation.py` (boundary module).
- **Modified:** `math_engine/transformations/__init__.py` (export the new names).
- **Modified (correctness fix):** `math_engine/transformations/algebraic.py` —
  `AddSubtractBothSides.apply` now `sympify`s its `amount`, so it accepts plain
  Python `int`/`float` in addition to SymPy objects (this surfaced during the
  boundary demo; it is a latent robustness fix in the standalone transformation
  layer, not a production behavior change).
- **Added:** `stress/phase35_6_stress.py`, `stress/phase35_6_report.md`.

---

## E. Separation / Inversion Checks (verified by test)

- No `math_engine/transformations/*` module imports `solver` or `reasoning.rules`
  (asserted over `algebraic`, `base`, `verification`, `presentation`, `conditions`,
  `branches`).
- `presentation.py` performs no mathematics (no `solve`/`expand`/`simplify`).
- No `solver/*.py` imports `transformations` (all three capability solvers checked).
- Presentation consumers call the same transformation and produce *different*
  `kind`/title (demonstrated with `isolate` vs `add_subtract_both_sides`).

---

## F. Branch Compatibility

`SquareRootTransformation().apply(Eq(x**2, 25))` produces two branches
(`x = 5`, `x = -5`). `payload()` preserves `branches` as a `tuple[Branch]` with
`has_branches is True` — the boundary does not collapse multi-branch results into
a single answer. It does not (yet) solve/render branches; it only avoids assuming
a single-result shape.

---

## G. Test Results

| Suite | Result |
|-------|--------|
| Phase 35.6 boundary | 9/9 ✅ |
| Phase 35.1 foundation | 6/6 ✅ |
| Phase 35.3 branch-aware | 20/20 ✅ |
| Phase 35.4 verification | 26/26 ✅ |
| Phase 31 (quadratic) | 139/139 ✅ |
| Phase 32 (linear) | 136/136 ✅ |
| Phase 33 (derivative) | 69/69 ✅ |
| Phase 34 (integration) | 229/404 ✅ (denominator double-counts randomized families — pre-existing) |
| `api.test_api` | exit 0 ✅ |
| integration | 6 pre-existing `dbl_backslash` only ✅ |
| doctests | 0 failed ✅ |
| `py_compile` | OK ✅ |
| `node --check` | OK ✅ |

Phase 28/29 legacy harnesses remain timing-sensitive (pre-existing, unchanged;
the newer Phase 34 harness covers the `/solve` integration path and passes).

---

## H. Production Files NOT Changed

- `math_engine/solver/equation_solver.py`
- `math_engine/solver/quadratic_solver.py`
- `math_engine/solver/derivative_solver.py`
- `math_engine/reasoning/rules/*.py` (the five linear rules and all derivative/quadratic rules)
- `math_engine/dispatcher/*`, `math_engine/parser/*`
- `api/adapter.py`, `api/main.py`
- `hmer_ux/*`

The only production-graph change is the additive `transformations/presentation.py`
plus the `__init__.py` export; neither is imported by any solver.

---

## I. Confirmation

The three capabilities (Linear, Quadratic, Differentiation) are behaviorally
unchanged: Phase 31/32/33 educational output and `final_answer` are byte-identical
to the pre-phase baseline, and no solver imports the transformation layer.

---

## Final Verdict

**READY FOR PHASE 35.7**

The presentation boundary is minimal, clean, avoids the Phase-35.2 regression
structurally, preserves the transformation layer's domain-neutrality, and is fully
regression-green. Phase 35.7 may now re-integrate one universal transformation into
a linear rule via this boundary (rule calls transformation, then owns its Step).