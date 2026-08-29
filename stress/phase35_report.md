# Phase 35 — Common Mathematical Transformation Architecture Audit

**Branch:** `feature/expression-solver`  
**Date:** 2026-08-29  
**Status:** Audit/Design Phase (No Implementation)

---

## 1. Current Architecture Overview

### 1.1 Pipeline Flow
```
User Input (LaTeX)
    ↓
LaTeX Parser (latex_parser.py) → SymPy Expression
    ↓
Dispatcher (dispatcher.py) → TaskType Classification
    ↓
SolverFactory → Concrete Solver (EquationSolver / QuadraticSolver / DerivativeSolver)
    ↓
Solver.run() → Rule Pipeline (RuleEngine + Rules) → Solution (steps + final_answer)
    ↓
API Adapter → JSON Response → Frontend (MathJax rendering)
```

### 1.2 Core Models
- **Expression**: Raw LaTeX + SymPy expression + TaskType + metadata
- **Step**: title, description, latex, metadata (kind)
- **Solution**: expression, steps (tuple[Step]), final_answer, metadata
- **TaskType**: UNKNOWN, EQUATION, QUADRATIC_EQUATION, DERIVATIVE, INTEGRAL, LIMIT, MATRIX, SIMPLIFY, EXPAND, FACTOR, SERIES

### 1.3 Solver Architecture
| Solver | TaskType | Rule Pipeline |
|--------|----------|---------------|
| EquationSolver | EQUATION (linear) | ExpandRule → MultiplyBothSidesRule → MoveVariableRule → MoveConstantRule → DivideCoefficientRule |
| EquationSolver (quadratic) | QUADRATIC_EQUATION | NormalizeQuadraticRule → ExtractQuadraticCoefficientsRule → ComputeDiscriminantRule → ClassifyQuadraticRootsRule → QuadraticFormulaRule → SimplifyQuadraticRootsRule |
| DerivativeSolver | DERIVATIVE | ExtractDerivativeStructureRule → [ImplicitDerivativeRule, ConstantDerivativeRule, PowerRule, SumRule, ProductRule, QuotientRule, ChainRule, GeneralPowerRule, TrigRule, ExpLogRule] |

### 1.4 Rule Engine
- `RuleEngine` runs an ordered list of `BaseRule` instances
- Each rule implements `can_apply(expression) -> bool` and `apply(expression) -> (new_expr, Step)`
- Rules are tried in registration order; first applicable rule fires, then iteration restarts
- Maximum 1000 passes prevents infinite loops

---

## 2. Rule Catalogue & Classification

### 2.1 Universal Transformation Candidates (Used Across Multiple Capabilities)

| Rule | Purpose | Used In | Mathematical Operation |
|------|---------|---------|------------------------|
| **ExpandRule** | Distribute multiplication over addition | Linear (EquationSolver) | Distributive law: a(b+c) = ab+ac |
| **MultiplyBothSidesRule** | Clear fractions by multiplying by LCD | Linear (EquationSolver) | Multiply both sides by LCD |
| **MoveConstantRule** | Move constant term to RHS | Linear (EquationSolver) | Add/subtract constant from both sides |
| **MoveVariableRule** | Collect variable terms on LHS | Linear (EquationSolver) | Add/subtract variable term from both sides |
| **DivideCoefficientRule** | Divide by coefficient to isolate variable | Linear (EquationSolver) | Divide both sides by coefficient |
| **SumRule** | Differentiate sum term-by-term | Derivative | d/dx(f+g) = f' + g' |
| **ProductRule** | Differentiate products | Derivative | (fg)' = f'g + fg' |
| **QuotientRule** | Differentiate quotients | Derivative | (f/g)' = (f'g - fg')/g² |
| **ChainRule** | Differentiate compositions | Derivative | (f∘g)' = f'(g)·g' |

**Observation**: The linear equation rules (ExpandRule, MultiplyBothSidesRule, MoveConstantRule, MoveVariableRule, DivideCoefficientRule) are **currently only used in EquationSolver** for linear equations. They are mathematically universal algebraic transformations that could apply to quadratic equations during normalization or to derivative inner functions.

### 2.2 Linear-Specific Rules (EquationSolver Pipeline)

| Rule | Purpose | Applicability |
|------|---------|---------------|
| ExpandRule | Distribute products over sums in linear equations | Linear equations with parentheses |
| MultiplyBothSidesRule | Clear fractions by multiplying by LCD | Linear equations with fractions |
| MoveVariableRule | Collect variable terms on LHS | Linear equations with variable on both sides |
| MoveConstantRule | Move constant term to RHS | Linear equations with constant on LHS |
| DivideCoefficientRule | Divide by coefficient to isolate variable | Linear equations with coefficient ≠ 1 |

**Note**: These rules operate on `Equality` objects with a single variable and degree ≤ 1. They are **linear-specific** because they assume the equation is linear (degree 1) and use `linear_components()` which asserts degree ≤ 1.

### 2.3 Quadratic-Specific Rules

| Rule | Purpose | Coupling |
|------|---------|----------|
| NormalizeQuadraticRule | Rearrange to ax²+bx+c=0 | QuadraticSolver only; uses Poly degree check |
| ExtractQuadraticCoefficientsRule | Extract a,b,c from ax²+bx+c=0 | Quadratic-specific; uses Poly.coeff_monomial |
| ComputeDiscriminantRule | Compute Δ = b²-4ac | Quadratic-specific; operates on (a,b,c) tuple |
| ClassifyQuadraticRootsRule | Classify roots by discriminant sign | Quadratic-specific; returns classification enum |
| QuadraticFormulaRule | Apply quadratic formula | Quadratic-specific; uses a,b,Δ |
| SimplifyQuadraticRootsRule | Simplify radical expressions | Quadratic-specific; uses sympy.simplify |

**Observation**: These rules are **properly quadratic-specific** — they operate on the quadratic form (a,b,c,Δ) and have no meaningful application outside quadratic equations.

### 2.4 Derivative-Specific Rules

| Rule | Purpose | Coupling |
|------|---------|----------|
| ExtractDerivativeStructureRule | Parse Derivative object | Derivative-specific; parses Derivative AST |
| ConstantDerivativeRule | d/dx(c) = 0 | Derivative-specific |
| PowerRule | d/dx(xⁿ) = nxⁿ⁻¹ | Derivative-specific |
| SumRule | (f+g)' = f'+g' | Derivative-specific; delegates to solver |
| ProductRule | (fg)' = f'g+fg' | Derivative-specific |
| QuotientRule | (f/g)' = (f'g-fg')/g² | Derivative-specific |
| ChainRule | (f∘g)' = f'(g)·g' | Derivative-specific; reuses PowerRule for outer |
| GeneralPowerRule | d/dx(f^g) = f^g·(g'ln f + g·f'/f) | Derivative-specific |
| TrigRule | sin/cos/tan/etc derivatives | Derivative-specific |
| ExpLogRule | d/dx(e^u)=e^u·u', d/dx(ln u)=u'/u | Derivative-specific |
| ImplicitDerivativeRule | Implicit diff of F(x,y)=0 | Derivative-specific; handles Eq with x,y |

**Observation**: Derivative rules are **properly derivative-specific** — they operate on derivative structures and mathematical functions, not on equations.

### 2.5 Parser/Normalization Infrastructure

| Component | Purpose | Reusability |
|-----------|---------|-------------|
| latex_parser.py | LaTeX → SymPy | Universal; used by all capabilities |
| dispatcher.py | SymPy type → TaskType | Universal; structural classification only |
| latex_formatter.py | Token sequence → LaTeX | Frontend-specific; recognition only |
| _to_problem (adapter) | Wrap bare expr as Derivative | Derivative-specific routing |

### 2.6 Verification Infrastructure

| Component | Purpose | Reusability |
|-----------|---------|-------------|
| DerivativeSolver._verify | Symbolic/numeric derivative check | Derivative-specific |
| DerivativeSolver._equivalent | Symbolic ratio + numeric fallback | Derivative-specific |
| QuadraticSolver has no verification | N/A | Quadratic-specific gap |
| Linear has no verification | N/A | Linear-specific gap |

---

## 3. Duplication & Coupling Analysis

### 3.1 Identified Duplications

| Transformation | Current Locations | Notes |
|----------------|-------------------|-------|
| **Expansion (distributive law)** | ExpandRule (linear only) | Could apply to quadratic normalization (e.g., (x+1)² = 9) |
| **Multiply both sides by LCD** | MultiplyBothSidesRule (linear only) | Could apply to rational equations in general |
| **Add/subtract same quantity both sides** | MoveConstantRule, MoveVariableRule (linear only) | Core algebraic principle; universal |
| **Divide both sides by non-zero** | DivideCoefficientRule (linear) | Universal when divisor ≠ 0 |
| **Add/subtract same term both sides** | MoveConstantRule, MoveVariableRule | Core algebraic principle |

**Key Finding**: The linear equation rules implement **universal algebraic transformations** (add/subtract/multiply/divide both sides, distributive law) but are **coupled to linear equations only** via:
- `linear_components()` which asserts degree ≤ 1
- `RuleEngine` in `EquationSolver._linear_steps()` which only runs for degree ≠ 2
- `EquationSolver._polynomial_degree()` check that routes degree=2 to QuadraticSolver

### 3.2 Incorrect Coupling

| Rule | Current Coupling | Issue |
|------|------------------|-------|
| ExpandRule | Only in EquationSolver linear pipeline | Could normalize (x+1)²=9 → x²+2x+1=9 |
| MultiplyBothSidesRule | Only in EquationSolver linear pipeline | Could clear fractions in any rational equation |
| MoveConstantRule / MoveVariableRule | Linear-specific via linear_components() | Core algebraic ops work for any equation |
| DivideCoefficientRule | Linear-specific via linear_components() | Division by non-zero is universal |

### 3.3 Properly Scoped (No Action Needed)

| Rule | Scope | Justification |
|------|-------|---------------|
| Quadratic-specific rules (6 rules) | QuadraticSolver only | Intrinsically quadratic (Δ, quadratic formula) |
| Derivative rules (10 rules) | DerivativeSolver only | Intrinsically differential |
| ImplicitDerivativeRule | DerivativeSolver only | Requires Eq with x,y |
| ExtractDerivativeStructureRule | Derivative-specific | Parses Derivative AST |

---

## 4. Mathematical Case Analysis

### 4.1 Case-by-Case Transformation Requirements

| Case | Equation | Required Transformations | Solution-Set Preservation |
|------|----------|--------------------------|---------------------------|
| **x² = 25** | x² = 25 | Square root (with ±) | ✅ Preserves; creates 2 branches |
| **√x = 5** | √x = 5 | Square both sides | ⚠️ Domain restriction x≥0; creates extraneous if not checked |
| **x + 4 = 9** | x + 4 = 9 | Subtract 4 both sides | ✅ Reversible, 1 branch |
| **3x = 12** | 3x = 12 | Divide by 3 | ✅ Reversible (coeff ≠ 0) |
| **(x+1)/2 = 5** | (x+1)/2 = 5 | Multiply by 2, then subtract 1 | ✅ Reversible (mult by 2≠0) |
| **x(x-2)=0** | x(x-2)=0 | Factor → zero product property | ✅ Creates 2 branches |
| **(x-1)² = 9** | (x-1)² = 9 | Square root (±) or expand+solve | ✅ 2 branches if sqrt; expand→quadratic |
| **√(x+3) = x-1** | √(x+3) = x-1 | Square both sides | ⚠️ **Extraneous solutions**; must verify |

### 4.2 Critical Mathematical Hazards

| Hazard | Example | Mitigation Required |
|--------|---------|---------------------|
| **Square root loses ±** | x² = 25 → x = 5 (missing -5) | Must generate ± branches |
| **Squaring introduces extraneous** | √(x+3) = x-1 → x+3 = (x-1)² introduces x=1 (extraneous) | Must verify against original |
| **Division by zero** | 3x = 12 → divide by 3 (safe); x·y = 0 → divide by x loses y=0 | Must check divisor ≠ 0 |
| **Domain restrictions** | √x = 5 requires x ≥ 0 | Track domain constraints |
| **Squaring loses sign info** | x = -2 → x² = 4 loses sign | Track sign information |

### 4.3 Branch Creation Requirements

| Operation | Creates Branches? | Example |
|-----------|-------------------|---------|
| Square root (√) | Yes (±) | x² = 25 → x = ±5 |
| Zero product property | Yes (one per factor) | x(x-2)=0 → x=0, x=2 |
| Quadratic formula | Yes (Δ ≥ 0) | Δ = b²-4ac |
| Trigonometric (periodic) | Yes (infinite) | sin(x) = 0 → x = nπ |
| Logarithm | No (single-valued) | ln(x) = 2 → x = e² |

---

## 4. Current Model Assessment

### 5.1 Can Current Models Support Universal Transformations?

| Model | Current Capability | Gap for Universal Transforms |
|-------|-------------------|------------------------------|
| **Expression** | Raw LaTeX + SymPy + TaskType | ✅ Can hold any SymPy expression |
| **Step** | title, description, latex, metadata | ✅ Can hold transformation metadata |
| **Solution** | expression, steps, final_answer, metadata | ✅ Can hold multiple branches via metadata |
| **Step.metadata** | Arbitrary dict | ✅ Can store branch info, conditions |
| **Solution.metadata** | Arbitrary dict | ✅ Can store branches, conditions |
| **Step.kind** | String enum | ✅ Extensible |

**Gap**: `Step` and `Solution` don't have explicit `branches` field. Branches are currently implicit (quadratic returns both roots in one step). For universal transforms that create branches (square root, zero product), we need explicit branch representation.

### 5.2 Transformation Result Structure

Current: `Rule.apply() → (new_expression, Step)`

Needed for universal transforms:
```python
@dataclass
class TransformationResult:
    transformed_expression: Basic
    step: Step
    branches: list[Basic] = field(default_factory=list)  # New branches created
    conditions: dict[str, Any] = field(default_factory=dict)  # Domain restrictions
    reversibility: Reversibility = Reversibility.REVERSIBLE  # Enum: REVERSIBLE, CONDITIONAL, IRREVERSIBLE
    extraneous_risk: bool = False  # Whether extraneous solutions possible
```

### 4.3 Verification Model Gaps

| Capability | Verification | Gap |
|------------|--------------|-----|
| Derivative | Full (symbolic + numeric) | ✅ Complete |
| Quadratic | None | ❌ Missing |
| Linear | None | ❌ Missing |
| Universal transforms | None | ❌ Missing |

**Need**: Universal verification that checks solution against original problem (especially for operations that can introduce extraneous solutions).

---

## 5. Proposed Common Transformation Architecture

### 6.1 Design Principles

1. **Mathematical correctness first** — Never sacrifice correctness for reuse
2. **Domain separation** — Quadratic/derivative logic stays domain-specific
3. **Explicit branch handling** — Transformations that create branches must declare them
3. **Explicit safety metadata** — Reversibility, extraneous risk, domain restrictions
4. **Minimal common layer** — Only genuinely universal transformations
5. **Opt-in reuse** — Capabilities opt into shared transformations; no forced unification

### 5.2 Proposed Architecture

```
math_engine/
├── transformations/          # NEW: Universal transformation layer
│   ├── __init__.py
│   ├── base.py              # Transformation base class + result types
│   ├── algebraic.py         # Universal algebraic transformations
│   │   ├── add_subtract_both_sides.py
    │   ├── multiply_divide_both_sides.py
    │   ├── distributive_law.py
    │   ├── zero_product_property.py
    │   └── square_root.py
    │   └── square_both_sides.py  # with extraneous warning
    │   └── verification.py
    │
├── rules/                   # Existing capability-specific rules
│   ├── linear/              # Linear-specific (uses algebraic transformations)
│   ├── quadratic/           # Quadratic-specific
│   ├── derivative/          # Derivative-specific
│   └── base_rule.py
│
├── solvers/                 # Capability-specific solvers
│   ├── equation_solver.py   # Uses algebraic transformations
│   ├── quadratic_solver.py  # Uses quadratic-specific + algebraic
│   └── derivative_solver.py # Derivative-specific only
│
├── verification/            # NEW: Universal verification
│   ├── base.py
│   ├── derivative_verification.py
│   ├── equation_verification.py  # NEW: checks solutions against original
│   └── branch_verification.py    # NEW: handles multi-branch solutions
```

### 3.3 Transformation Base Design

```python
@dataclass(frozen=True)
class TransformationResult:
    transformed: Basic                           # Resulting expression/equation
    step: Step                                   # Educational step
    branches: tuple[Basic, ...] = ()             # New branches created
    conditions: frozenset[Condition] = frozenset()  # Domain restrictions
    reversibility: Reversibility = Reversibility.REVERSIBLE
    extraneous_risk: bool = False                # Can create extraneous solutions?
    domain_restrictions: frozenset[DomainRestriction] = frozenset()

class Reversibility(Enum):
    REVERSIBLE = "reversible"          # Bijective: x+4=9 ↔ x=5
    CONDITIONAL = "conditional"        # Reversible with conditions: x/2=5 (×2 safe, x≠0)
    IRREVERSIBLE = "irreversible"      # Loses information: squaring, sqrt without ±
```

### 3.4 Rule Pipeline Integration

```python
class TransformationPipeline:
    """Composes universal transformations with capability-specific rules."""
    
    def __init__(self, universal: list[UniversalTransformation], 
                 capability_specific: list[BaseRule]):
        self.universal = universal
        self.capability_specific = capability_specific
    
    def run(self, expression) -> tuple[Basic, tuple[Step, ...]]:
        # 1. Apply universal transformations (expand, clear fractions, etc.)
        # 2. Apply capability-specific rules (quadratic formula, chain rule, etc.)
        # 3. Handle branch creation and verification
        pass
```

---

## 6. Specific Transformation Designs

### 7.1 Add/Subtract Both Sides
- **Purpose**: Move terms across equality
- **Input**: Equation, term to move
- **Output**: New equation, step
- **Reversibility**: REVERSIBLE
- **Branches**: None
- **Conditions**: Term exists on source side

### 7.2 Multiply/Divide Both Sides
- **Purpose**: Clear fractions, isolate variable
- **Input**: Equation, multiplier/divisor
- **Output**: New equation, step
- **Reversibility**: CONDITIONAL (divisor ≠ 0)
- **Branches**: None
- **Conditions**: Divisor ≠ 0
- **Extraneous Risk**: No (if divisor ≠ 0)

### 7.3 Distributive Law (Expansion)
- **Purpose**: Expand products over sums
- **Input**: Expression with Mul(Add)
- **Output**: Expanded expression
- **Reversibility**: CONDITIONAL (factoring not always possible)
- **Branches**: None

### 7.3 Square Root (Zero Product / Square Root Property)
- **Purpose**: Solve x² = a or zero product
- **Input**: Equation x² = a or f(x)·g(x) = 0
- **Branches**: Multiple (±√a, or one per factor)
- **Reversibility**: IRREVERSIBLE (without ±)
- **Branches**: Multiple (±√a or one per factor)
- **Conditions**: a ≥ 0 for real roots; f(x)=0 ∨ g(x)=0

### 7.4 Square Both Sides
- **Purpose**: Eliminate radicals
- **Input**: Equation with √ or fractional powers
- **Output**: Squared equation
- **Reversibility**: IRREVERSIBLE
- **Extraneous Risk**: HIGH
- **Branches**: None (but may create extraneous)
- **Verification Required**: MANDATORY (check against original)

### 7.5 Square Root Property (Quadratic)
- **Purpose**: x² = a → x = ±√a
- **Input**: x² = a
- **Branches**: Two (±√a)
- **Conditions**: a ≥ 0 for real; complex otherwise

---

## 8. Proposed Implementation Plan

### Phase 35.1: Foundation (No Behavior Changes)
1. Create `math_engine/transformations/` package with base types
2. Define `TransformationResult`, `Reversibility`, `Condition` types
3. Create `AlgebraicTransformation` base class
4. Add `branches`, `conditions`, `reversibility` to `Step.metadata` schema
4. **No behavior changes** — only infrastructure

### Phase 35.2: Universal Algebraic Transformations
1. Implement `AddSubtractBothSides` (MoveConstantRule, MoveVariableRule refactor)
2. Implement `MultiplyDivideBothSides` (MultiplyBothSidesRule, DivideCoefficientRule refactor)
3. Implement `DistributiveLaw` (ExpandRule refactor)
3. Update `EquationSolver` to use new algebraic transformations
4. **Verify**: All Phase 28/29/32 tests pass

### Phase 35.3: Branch-Aware Transformations
1. Implement `SquareRootTransformation` (for x² = a, zero product)
2. Implement `SquareBothSides` with extraneous warning
2. Update `QuadraticSolver` to use `SquareRootTransformation`
2. Add `EquationVerification` for extraneous solution detection
2. **Verify**: Phase 31, 32, 33 tests pass

### Phase 35.4: Verification Infrastructure
1. Implement `EquationVerification` (check solutions against original)
1. Add branch verification for multi-branch solutions
1. Integrate into `QuadraticSolver` and `EquationSolver`
1. **Verify**: All regression suites pass

### Phase 35.5: Derivative Integration (Future)
1. Extract universal algebraic transformations used by derivative inner functions
1. Ensure `ChainRule`, `ProductRule`, etc. can use shared algebraic transformations
1. **Verify**: Phase 33 tests pass

---

## 9. Compatibility Impact Assessment

| Component | Change Type | Risk | Mitigation |
|-----------|-------------|------|------------|
| EquationSolver | Refactor to use AlgebraicTransformation | Low | Phase 35.2 validates |
| QuadraticSolver | Use SquareRootTransformation | Low | Phase 35.3 validates |
| DerivativeSolver | No change (Phase 35.5) | None | N/A |
| RuleEngine | Add branch/condition support | Low | Backward compatible |
| Step/Solution models | Add metadata fields | None | Backward compatible |
| API Adapter | No change | None | N/A |
| Frontend | No change | None | N/A |

---

## 10. Proposed Stress Test for Phase 35

New test cases for `stress/phase35_stress.py`:

```python
# Universal transformation cases
UNIVERSAL_TRANSFORMATIONS = [
    # Square root property
    ("x**2 = 25", {"x": {5, -5}}, {"sqrt_branch"}),
    ("x*(x-2) = 0", {"x": {0, 2}}, {"zero_product"}),
    
    # Extraneous solutions
    ("sqrt(x+3) = x-1", {"x": 2}, {"extraneous_check"}),  # x=1 is extraneous
    
    # Domain restrictions
    ("sqrt(x) = 5", {"x": 25}, {"domain": "x>=0"}),
    
    # Division by zero protection
    ("x*y = 0", {"x": 0, "y": 0}, {"zero_product"}),  # dividing by x would lose y=0
]
```

---

## 12. Final Verdict

### READY FOR IMPLEMENTATION ✅

**Justification:**
1. **Mathematically sound** — Architecture explicitly models solution-set preservation, branch creation, and extraneous solution hazards
2. **Minimal common layer** — Only genuinely universal algebraic transformations are shared
3. **Domain separation preserved** — Quadratic/derivative logic remains encapsulated
4. **Backward compatible** — All changes are additive; existing solvers refactor incrementally
5. **Regression safety** — Phased approach with full regression validation at each step
6. **Mathematically sound** — Explicit handling of branch creation, extraneous solutions, domain restrictions, reversibility

### Implementation Readiness

| Phase | Status | Blocker |
|-------|--------|---------|
| 35.1 Foundation | Ready | None |
| 35.2 Algebraic Transformations | Ready | None |
| 35.3 Branch-Aware Transforms | Ready | None |
| 35.4 Verification | Ready | None |
| 35.5 Derivative Integration | Ready | None |

### Remaining Questions (Non-Blocking)

1. **Complex root representation** — Current `latex()` handles complex; verify branch rendering
2. **Periodic solutions** — Trig equations need infinite branch handling (defer to later phase)
2. **Symbolic conditions** — How to represent `x ≠ 0` in metadata? (Use `Condition` objects)
2. **Performance** — RuleEngine passes limit (1000) sufficient for new transformations?

---

**Verdict: READY FOR IMPLEMENTATION** ✅

The architecture is mathematically sound, minimally invasive, and preserves all existing behavior while enabling future mixed-problem capabilities. Ready to begin Phase 35.1 implementation.