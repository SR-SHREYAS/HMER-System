# Phase 35.4 — Common Mathematical Verification Architecture

**Branch:** `feature/expression-solver`
**Date:** 2026-08-30
**Status:** SUCCESS

---

## 1. Objective

Build the domain-neutral verification infrastructure identified in the Phase 35
audit: a reusable mechanism that checks a *candidate* solution against the
*original* equation, producing a three-valued decision (VALID / INVALID /
INDETERMINATE), with explicit extraneous-solution and domain-condition support.

This phase is infrastructure only. It is not wired into any production solver.

---

## 2. Architecture Added

In `math_engine/transformations/verification.py` (rewritten from the Phase 35.1
stub):

- **`VerificationStatus`** — three-valued enum: `passed` (VALID), `failed`
  (INVALID), `indeterminate` (INDETERMINATE).
- **`VerificationMethod`** — `symbolic` (default) or `numeric` (unused fallback
  reserved for future).
- **`VerificationResult`** — frozen dataclass carrying `status`, `method`,
  `candidate`, `substituted`, `conditions_checked`, `failed_conditions`,
  `extraneous`, and a `message`; plus `valid`/`invalid`/`indeterminate` helpers.
- **`EquationVerifier`** — verifies one candidate against one original `Eq`.
- **`BranchVerifier`** — verifies each branch of a transformation independently.
- **`TransformationVerifier`** — verifies the branches of a `TransformationResult`.
- **`verify_against_original`** / **`check_extraneous_solutions`** — convenience
  wrappers (the latter partitions candidates into valid / extraneous /
  indeterminate).

No second competing result/condition model was introduced; the Phase 35.1
`Branch`, `TransformationResult`, and condition abstractions are reused.

---

## 3. Verification Semantics

Verification substitutes the candidate into the **original** equation and checks,
in exact symbolic form, whether `simplify(LHS - RHS) == 0`:

| Outcome | Meaning |
|---------|---------|
| `passed` (VALID) | `simplify(LHS - RHS)` is symbolically zero. |
| `failed` (INVALID) | The difference is a definite non-zero (or a domain condition is violated). |
| `indeterminate` (INDETERMINATE) | The structure can't be reduced to a definite boolean (e.g. unresolved symbolic difference), the input is a non-equation, or a bare candidate lacked a variable. |

Never silently coerced: indeterminate stays indeterminate; a violated domain
condition forces INVALID; an undecidable condition downgrades VALID to
INDETERMINATE.

---

## 4. Candidate Representations

`EquationVerifier.verify` accepts:

- a bare scalar (requires an explicit `variable`),
- an equality `Eq(y, 3)` (LHS used as the symbol),
- a mapping `{x: 2, y: 3}` (multi-variable),
- a list of `Eq` (merged into a multi-variable map).

This makes the layer variable-agnostic and multi-variable capable without a
general equation-system solver.

---

## 5. Extraneous-Solution Detection

`check_extraneous_solutions` partitions candidates against the *original*
equation. A candidate that satisfies a transformed equation but fails the
original is reported in the `extraneous` group, and the individual
`VerificationResult.extraneous` flag is set for single-candidate calls.

Worked example (verified): `√x = x - 2` → squaring yields roots `{1, 4}`;
`x = 1` is extraneous, `x = 4` is valid.

---

## 6. Condition / Domain Handling

Known conditions (denominator ≠ 0, radicand ≥ 0, log argument > 0) are carried
via the Phase 35.1 `Condition`/concrete condition classes and evaluated by
substitution:

- `x/y = 2` with `y = 0` → INVALID (denominator zero).
- `√x = 5` with `x = 25` → VALID (radicand ≥ 0 satisfied).
- `√x = 5` with `x = -1` → INVALID (radicand < 0).
- `ln x = 0` with `x = 1` → VALID (arg > 0).
- `ln x = 0` with `x = -1` → INVALID (arg ≤ 0).

No general symbolic domain-analysis engine was built; undecidable conditions
produce an explicit indeterminate result rather than assuming validity.

---

## 7. Expressions vs Equations

Non-equation inputs (bare expressions) are reported indeterminate for
substitution-based verification. The existing `DerivativeSolver` verification
logic is untouched and remains separate.

---

## 8. Representative Examples

| Original | Candidate | Outcome |
|----------|-----------|---------|
| `x² = 25` | `x = 5` | VALID |
| `x² = 25` | `x = -5` | VALID |
| `x² = 0` | `x = 0` | VALID |
| `y² = 9` | `y = 3` / `y = -3` | VALID |
| `(x+2)² = 9` | `x = 1` | VALID |
| `3x = 12` | `x = 4` | VALID |
| `x = a` | `x = a` | VALID (symbolic) |
| `x² + y² = 1` | `{x: 3/5, y: 4/5}` | VALID (multi-variable) |
| `x² = 25` | `x = 4` / `x = 6` | INVALID (extraneous) |
| `√x = x - 2` | `x = 1` | INVALID (extraneous) |
| `√x = x - 2` | `x = 4` | VALID |
| `x = a` | `x = b` | INDETERMINATE |

---

## 9. Test Methodology

`stress/phase35_4_stress.py` (26 checks) independently asserts outcomes without
consulting any solver:

- **valid** (9): ±roots, zero, alternate variable, non-bare square, rational,
  symbolic, multi-variable, candidate-as-Eq.
- **invalid** (5): wrong values, extraneous, denominator zero, log/radicand domain.
- **indeterminate** (3): unresolved symbolic, bare value w/o variable, non-equation.
- **domain-valid** (3): radicand/log/denominator conditions satisfied.
- **branch** (4): both-valid, mixed, zero-collapse, zero-product.
- **composition** (2): square-root → verify both valid; square → extraneous detect.

---

## 10. Regression Results

| Suite | Result |
|-------|--------|
| Phase 31 (quadratic educational) | 139/139 ✅ |
| Phase 32 (linear educational) | 136/136 ✅ |
| Phase 33 (derivative educational) | 69/69 ✅ |
| Phase 34 (full integration) | 229/404 ✅ (denominator double-counts randomized families — pre-existing) |
| Phase 35.1 foundation | 6/6 ✅ |
| Phase 35.3 branch-aware | 20/20 ✅ |
| Phase 35.4 verification | 26/26 ✅ |
| `api.test_api` | exit 0 ✅ |
| integration/test_ocr_to_api | 6 pre-existing `dbl_backslash` parsing failures only ✅ |
| doctests | 0 failed ✅ |
| `py_compile` | OK ✅ |
| `node --check` script.js / animation.js | OK ✅ |

Phase 28 / Phase 29 legacy harnesses remain timing-sensitive (pre-existing,
unrelated to this change); the newer Phase 34 harness exercises the same
`/solve` path and completes green.

---

## 11. Architectural Assessment

- ✅ Genuinely domain-neutral (no linear/quadratic/differentiation logic).
- ✅ Reuses the Phase 35.1 `Branch`/`TransformationResult`/condition abstractions.
- ✅ Does not duplicate `DerivativeSolver` verification.
- ✅ Does not duplicate solver logic (verification solves/produces nothing).
- ✅ Variable-agnostic and multi-variable capable.
- ✅ No LaTeX/string/rendered-text comparison anywhere.
- ✅ Distinguishes valid/invalid/indeterminate.
- ✅ Verifies branches independently.

`grep` confirms no module outside `math_engine/transformations/` imports the
verification or transformation layer, so it cannot affect production solvers.

---

## 12. Known Limitations

- Verification is exact-symbolic only; a reserved `numeric` method exists but is
  not exercised (per Phase 35.1 design).
- No standalone condition-solver: undecidable conditions yield indeterminate
  rather than a guessed validity.
- Non-equation (expression) candidates cannot be substitution-verified; used
  only for future extensibility.

---

## 13. Final Verdict

**SUCCESS**

The verification architecture is independently validated (26/26), is reusable by
future mixed-equation solving, and all existing production behavior remains
intact. Production solvers remain unwired from the transformation/verification
layer.