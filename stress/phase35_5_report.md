# Phase 35.5 — Common Transformation Integration Design Audit

**Branch:** `feature/expression-solver`
**Date:** 2026-08-30
**Type:** Architecture/design audit — **no production code changed**

---

## A. Architecture Decision

**Decision: Option C (separate transformation-execution layer beneath the rules)
with an explicit presentation adapter owned by each rule.**

The transformation layer (`math_engine/transformations/`) computes the
*mathematical* result (`TransformationResult`: new SymPy expression, branches,
conditions, reversibility, verification requirement). The existing `BaseRule`
subclasses remain the *owners of educational presentation* — a rule calls a
transformation, then constructs its own `Step` (title, description, latex,
kind) from the transformation result.

Concretely, the safest integration pattern is **A-prime**:

> A rule invokes a transformation to compute the mathematical consequence and
> then **builds its own Step**, rather than surfacing the transformation's
> default Step.

We reject the Phase-35.2 pattern (B taken too literally: rules becoming passthrough
wrappers that returned `transformation.step`) because it replaced the rule's
`kind`/title/description/LaTeX with the transformation's generic one, changing the
Step contract (e.g. `divide` → `multiply_both_sides`; `\div` → `\times 1/c`).

### How the layers currently relate

| Component | Lives in | Responsibility |
|-----------|----------|----------------|
| `Expression` / `Step` / `Solution` / `TaskType` | `models/` | Immutable typed data. |
| `BaseRule` | `reasoning/rules/base_rule.py` | `can_apply` / `apply → (expr, Step)`. |
| `RuleEngine` | `reasoning/rules/rule_engine.py` | Ordered, first-applicable, iterate-to-fixpoint. |
| `ReasoningEngine` / `*Reasoner` | `reasoning/` | Legacy `/predict` step generation (relays solver steps). |
| `*Solver` | `solver/` | Per-capability orchestration; owns rule order + final answer. |
| `TransformationResult` / `Branch` / `BranchSet` / `Condition` / `VerificationResult` | `transformations/` | Domain-neutral math result metadata. |

The transformation layer is currently **unimported** by any solver (verified via
`grep` across `math_engine/` and `api/`).

---

## B. Universal vs Capability-Specific Classification

### Transformations implemented in `math_engine/transformations/algebraic.py`

| Transformation | Classification | Notes |
|----------------|----------------|-------|
| `AddSubtractBothSides` | genuinely universal | equivalence-preserving; add a signed quantity to both sides. |
| `MultiplyDivideBothSides` | genuinely universal (conditional) | reversible only when factor ≠ 0. |
| `DistributiveLaw` | genuinely universal | a(b+c) → ab+ac. |
| `SquareRootTransformation` | genuinely universal | `f²=g ⇒ f=±√g`; branch-producing. |
| `SquareBothSides` | genuinely universal (hazardous) | solution-expanding; requires verification. |
| `ZeroProductProperty` | genuinely universal | `A·B=0 ⇒ A=0 ∨ B=0`; branch-producing. |

### Capability-specific rules that must NOT move to the common layer

| Rule | Capability |
|------|------------|
| `NormalizeQuadraticRule`, `ExtractQuadraticCoefficientsRule`, `ComputeDiscriminantRule`, `ClassifyQuadraticRootsRule`, `QuadraticFormulaRule`, `SimplifyQuadraticRootsRule` | Quadratic |
| `PowerRule`, `ProductRule`, `QuotientRule`, `ChainRule`, `TrigRule`, `ExpLogRule`, `GeneralPowerRule`, `ConstantDerivativeRule`, `SumRule`, `ExtractDerivativeStructureRule`, `ImplicitDerivativeRule` | Differentiation |
| `MoveConstantRule`, `MoveVariableRule`, `DivideCoefficientRule`, `ExpandRule`, `MultiplyBothSidesRule` | Linear (current, frozen) — mathematically universal *but* presentational coupling |

### Potentially-universal but premature (do NOT add yet)

- cross multiplication — is "multiply both sides by LCD" (already covered); a
  separate "cross-multiply" primitive is redundant and risky.
- rationalization — depends on context (numerator vs denominator, real vs
  complex); premature.
- factoring as a solver-transform — factorization is not closed over arbitrary
  expressions; premature.

**Verdict:** the current six universal primitives form a sufficient minimal common
layer. Do not expand it now.

---

## C. Recommended Integration Boundary

```
   Solver (capability orchestration)
        │  owns rule order, final answer, verification scheduling
        ▼
   Rule (educational ownership: title, desc, kind, latex)
        │  calls transformation to compute math consequence
        ▼
   Transformation (pure mathematical result + safety metadata)
```

- A rule calls `transformation.apply(...)`, reads `TransformationResult`, and
  **builds its own `Step`** from `transformed_expression`/`branches`/`conditions`.
- The transformation's own `step` field is treated as an optional *fallback* only,
  never the rule's authoritative Step for frozen capabilities.
- This preserves the exact Phase-31/32/33 `Step` contracts while sharing only
  the *mathematics*.

---

## D. Branch / Verification / Domain Propagation Design

### Branch propagation

- Branch-producing transformations return a `tuple[Branch]`; a future solver
  carrying a `BranchSet` must treat each branch as an independent continuation.
- `x²=25` → two branches `x=5`, `x=-5`. `(x-2)²=9` → `x-2=3`, `x-2=-3`.
  `A·B=0` → `A=0`, `B=0`.
- Branches must remain *labeled* (Phase 35.1 `Branch`) and never auto-collapsed
  except for mathematically identical ones (`x²=0 → x=0`). A `BranchSet` carries
  the original expression for later verification.

### Verification boundaries

- Verification belongs **after** a transformation whose `extraneous_risk=True`
  (squaring) and, more generally, at **solver level** (single authoritative point),
  not inside transformations (which must stay pure). A dedicated orchestration
  helper is permissible but must not duplicate `DerivativeSolver` verification.
- `√(x+3)=x-1`: square → solve → **verify each candidate against original** →
  drop extraneous.

### Domain restriction propagation

- Conditions (denominator≠0, radicand≥0, log arg>0) attach to results via
  `Condition`; they coexist with branches by attaching per-branch or result-wide.
- Do not build a domain solver; carry/evaluate known conditions only (Phase 35.4
  already provides `EquationVerifier` condition checking).

---

## E. Mixed-Problem Architectural Direction

Stress case: `√(sin(x³)) − √156 = x² − x − 12`.

A future architecture would need to:

1. recognize the whole thing as an equation (structural, not `=`-string scan);
2. preserve `lhs` and `rhs` as opaque SymPy subtrees;
3. select equation-manipulation transformations (add/subtract, square both sides,
   square-root) *by structure*, not by rule-name;
4. invoke differentiation only when a derivative is explicitly requested — never
   as a blanket "simplify the subexpression" step;
5. detect when the residual is quadratic and delegate to `QuadraticSolver`;
6. propagate branches and domain restrictions; verify final candidates.

**Feasibility against current dispatcher/solver:** a **capability-first dispatch
with optional sub-delegation** is achievable without turning every capability into
a global rule pool. The dispatcher continues to classify the *top-level* task; a
new narrow "mixed orchestrator" would be added *alongside* (not replacing) the
existing three solvers, and would itself delegate downward. This is a future
capability, not a refactor of the current three.

---

## F. Phase-by-Phase Implementation Roadmap

| Phase | Scope | Invariants | New tests |
|-------|-------|------------|-----------|
| 35.6 | Introduce transformation-execution/presentation boundary (a tiny adapter: rule calls transformation, builds own Step). No solver rewrite. | Phase 32 linear `kind`/`\div` contract unchanged; final_answer byte-identical. | boundary contract test. |
| 35.7 | Re-integrate **one** universal transform (e.g. `AddSubtractBothSides`) into `MoveConstantRule`/`MoveVariableRule` *with presentation adapter*. | `isolate`/`move_variable` kinds + LaTeX identical to Phase 32. | Phase 28/32 + targeted. |
| 35.8 | Re-integrate remaining linear transforms (`MultiplyDivideBothSides`, `DistributiveLaw`) with adapters. | byte-identical `multiply_both_sides`/`expand`/`divide` steps. | Phase 28/32/34 + HTTP parity. |
| 35.9 | Integrate shared transforms into Quadratic where genuinely universal (e.g. `DistributiveLaw` in normalization is already quadratic-internal; defer). | Phase 31 quadratic contract unchanged. | Phase 31. |
| 35.10 | Branch orchestration (square-root / zero-product) above `EquationSolver`/`QuadraticSolver` for `x²=a`, factored products. | Quadratic 5-step contract unchanged. | branch/equivalence tests. |
| 35.11 | Verification + domain propagation wiring for squaring/square-root. | no false "valid". | Phase 35.4 + extraneous tests. |
| 35.12+ | Mixed-problem orchestrator (new, additive) + future integration/limits. | existing three frozen. | new mixed tests. |

Each phase: narrow, regression-gated, no unrelated cleanup.

---

## G. Regression / Invariant Checklist

- Phase 28 (linear/quadratic end-to-end) unchanged.
- Phase 29 (3-capability + juxtaposition) unchanged.
- Phase 31 (quadratic educational 5-step contract) unchanged.
- Phase 32 (linear educational kinds/descriptions/`\div`) unchanged.
- Phase 33 (derivative educational) unchanged.
- Phase 34 (full `/solve` integration + task/verification metadata) unchanged.
- transformation-specific + branch-equivalence tests (Phase 35.3/35.4) still pass.
- exact `final_answer` byte-preservation for frozen capabilities.
- HTTP parity (adapter JSON contract) unchanged.
- integration 6 pre-existing `dbl_backslash` failures remain exactly that.

---

## H. Explicit Confirmation

Production behavior is **unchanged** this phase. No solver, rule, parser,
dispatcher, adapter, or frontend file was modified. The only artifact is this
report. The transformation layer remains unimported by production code.

---

## Final Verdict

**READY FOR INTEGRATION**

The architecture is sound and the safest path is established: begin integration
incrementally at Phase 35.6 (presentation boundary) and Phase 35.7 (first
transformation with an educational adapter), gated by the Phase 32 contract that
Phase 35.2 violated. Blockers: none structural; the single prerequisite is that
each integration step retain a per-capability presentation adapter so educational
output and `Step` contracts never regress.