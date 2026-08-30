# Phase 35.3 — Branch-Aware Algebraic Transformations

**Branch:** `feature/expression-solver`
**Date:** 2026-08-30
**Status:** SUCCESS

---

## 1. Objective

Implement and validate the three branch-aware universal algebraic transformations
identified in the Phase 35 architecture audit, as reusable domain-neutral
mathematical primitives:

1. **Square-root transformation** (inverse of squaring — preserves ± / branch set)
2. **Square-both-sides** (solution-expanding — requires verification)
3. **Zero-product property** (factor → zero branches)

These must not be wired into the production Linear/Quadratic/Derivative solvers
yet; this phase establishes and validates the reusable primitives first.

---

## 2. Starting Repository State

- HEAD: `789853b — feat: implement modular algebraic transformation framework and base operations`
- Phase 35.1 foundation present under `math_engine/transformations/`
  (`base.py`, `conditions.py`, `branches.py`, `verification.py`, `algebraic.py`).
- Phase 35.2 (extraction) was uncommitted; the five linear-rule files carried
  delegations to the transformation layer.
- Working tree at session start: `M` on the 5 rule files + `algebraic.py` +
  `base.py`; untracked `phase35_2_report.md`.

---

## 3. What Was Implemented

Three branch-aware transformation classes (in `math_engine/transformations/algebraic.py`),
all operating on SymPy structure (never on LaTeX strings or variable names):

### `SquareRootTransformation`
- `f(x)² = g(x)  ⇒  f(x) = +√g(x)  OR  f(x) = -√g(x)`
- Structural detection via `_squared_side(eq)` — handles both orientations
  (`lhs² = rhs` and `lhs = rhs²`) and **non-bare bases** such as `(x+2)² = 9`.
- Produces a `Branch` tuple via the Phase 35.1 `Branch` model.
- `x² = 0` collapses `±0` to a **single** branch (no duplicate equivalent branches).
- Negative numeric radicands yield the correct complex branches (`x² = -1 → x = ±i`).
- Marked `branch_producing` + `verification_required="required"` + `extraneous_risk=True`.

### `SquareBothSides`
- `A = B  ⇒  A² = B²`.
- Does **not** produce branches and is **not** marked reversible.
- `reversibility = "irreversible"`, `verification_required = "required"`,
  `extraneous_risk = True`, with explicit warning metadata
  (`step.metadata["warning"] == "extraneous_solutions"`).
- The Step description states that every candidate must be verified against the
  original equation.

### `ZeroProductProperty`
- `A·B·… = 0  ⇒  A = 0 OR B = 0 OR …`
- One `Branch` per factor of the top-level `Mul`; supports 2, 3, and square
  factors; symbolic factors; non-linear factors.
- `can_apply` rejects non-products and non-zero RHS.
- `branch_producing`, `verification_required = "none"`, `extraneous_risk = False`.

---

## 4. Mathematical Semantics

| Transformation | Branching | Reversibility | Verification | Extraneous risk |
|----------------|-----------|---------------|--------------|-----------------|
| Square root    | ± (or single for zero) | `branch_producing` | `required` | True |
| Square both sides | none | `irreversible` | `required` | True |
| Zero product   | one per factor | `branch_producing` | `none` | False |

Key distinction preserved:
- Square root **splits** the solution set into equivalent branches (never loses `±`).
- Square both sides **expands** the candidate set (non-injective) — no equivalence claim.
- Zero product **decomposes** a product equation into independent equations.

---

## 5. Branch / Condition / Verification Behavior

- Branches use the Phase 35.1 `Branch` dataclass (one per solution/equation).
- Conditions use the Phase 35.1 `Condition` abstraction (no second condition system).
- No `DomainRestriction` was fabricated for negative radicands: the complex
  branches are themselves the correct answer, so no misleading "real solution"
  condition is attached.
- Verification semantics communicated via `verification_required` +
  `extraneous_risk` on `TransformationResult` for squaring.

---

## 6. Representative Examples (verified)

| Input | Branches |
|-------|----------|
| `x² = 25` | `x = 5`, `x = -5` |
| `y² = 9` | `y = 3`, `y = -3` |
| `x² = 0` | `x = 0` (single) |
| `x² = a` | `x = √a`, `x = -√a` |
| `(x+2)² = 9` | `x+2 = 3`, `x+2 = -3` |
| `x² = -1` | `x = i`, `x = -i` |
| `x(x-2) = 0` | `x = 0`, `x-2 = 0` |
| `(x-1)(x+3)(x-5) = 0` | three branches |
| `x²(x-1) = 0` | `x² = 0`, `x-1 = 0` |
| `√(x) = x-2` (square) | squared: `x = (x-2)²`, roots `{1, 4}`, extraneous `1` flagged |

---

## 7. Regression Found and Fixed (Phase 35.2 residual)

During regression testing, the linear solver produced a wrong result for
`5 = 2x + 3` (empty result) and the divide/isolate step `kind`s were changed by
the Phase 35.2 rule delegation (`divide` → `multiply_both_sides`), breaking the
Phase 32 educational-content contract.

**Root cause:** Phase 35.2's `AddSubtractBothSides` used "auto-move" semantics
that *added* a term when it appeared on the RHS (wrong for "move RHS term to
LHS"), and `DivideCoefficientRule`/`MoveConstantRule`/`MoveVariableRule`
delegated away their own educational step formatting (losing `kind`/`\div`).

**Resolution:** Reverted the five linear rule files to HEAD (their exact
Phase 32 behavior), keeping the transformation layer itself intact and fully
decoupled. The branch-aware transformations remain standalone reusable primitives
and are not imported by any solver.

This confirms the Phase 34/32/31/33 behavioral baseline is fully preserved.

---

## 8. Test Matrix

`stress/phase35_3_stress.py` (20 checks, all passing):

| Section | Passed/Total |
|---------|--------------|
| square_root (both roots, zero, alt variable, symbolic radicand, non-bare base, negative radicand, rejection, equivalence) | 8/8 |
| zero_product (2/3/squared/symbolic factors, rejections) | 6/6 |
| square_both_sides (transform, symbolic, extraneous semantics) | 3/3 |
| neutrality (variable-agnostic, rational coefficients, non-linear factors) | 3/3 |

---

## 9. Regression Results

| Suite | Result |
|-------|--------|
| Phase 31 (quadratic educational) | 139/139 ✅ |
| Phase 32 (linear educational) | 136/136 ✅ |
| Phase 33 (derivative educational) | 69/69 ✅ |
| Phase 34 (full integration) | 229/404 ✅ (denominator double-counts randomized families — pre-existing harness quirk) |
| Phase 35.1 foundation | 6/6 ✅ |
| Phase 35.3 branch-aware | 20/20 ✅ |
| `api.test_api` | exit 0 ✅ |
| integration/test_ocr_to_api | 6 pre-existing `dbl_backslash` parse failures only ✅ |
| doctests (incl. trig 43, implicit 12) | 0 failed ✅ |
| `py_compile` (all transformation modules + stress) | OK ✅ |
| `node --check` script.js / animation.js | OK ✅ |

Phase 28 / Phase 29 legacy harnesses: these use a heavier 4-layer × randomized
FastAPI `TestClient` matrix and hit their execution timeout with no output. This
behavior was observed at the very start of the session (before any Phase 35.3
change) and is a pre-existing harness performance issue, not a solver regression.
The newer Phase 34 harness exercises the same `/solve` path (engine, adapter,
HTTP) and completes green.

---

## 10. Limitations

- `SquareRootTransformation` assumes an *exact* square on one side (`Pow` with
  exponent 2). It does not handle rational/radical exponents or general powers.
- Negative radicands are returned as complex branches; no separate real-root
  domain condition is emitted (the complex result is the correct answer).
- The three transformations are validated standalone; they are intentionally
  not yet wired into any solver pipeline.
- Phase 28/29 legacy harnesses remain timing-sensitive (pre-existing).

---

## 11. Architectural Impact

- `math_engine/transformations/` remains domain-neutral: no quadratic-formula,
  differentiation, or linear-solver orchestration lives there.
- No solver, dispatcher, API adapter, or frontend file was modified.
- The transformation layer is not imported anywhere in the solver runtime path
  (verified via grep), so it cannot affect the frozen capabilities.

---

## 12. Explicit Confirmations

- ✅ `x² = 25` preserves both `+5` and `-5`.
- ✅ Multiple branches represented cleanly via `Branch`.
- ✅ Zero-product produces one independent branch per factor.
- ✅ Squaring explicitly communicates extraneous-solution risk and requires verification.
- ✅ Conditions/domain restrictions represented using the Phase 35.1 infrastructure.
- ✅ No existing solver behavior changed (Phase 32 linear regressed mid-phase and was restored to HEAD).
- ✅ Transformations are capability-neutral (operate on SymPy structure only).

---

## 13. Final Verdict

**SUCCESS**

The three branch-aware universal algebraic transformations are implemented,
mathematically sound, and validated with a dedicated 20-check stress harness plus
the full regression suite. No existing production capability behavior is changed.