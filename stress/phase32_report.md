# Phase 32 — Educational Linear Equation Step Redesign Report

Branch: `feature/expression-solver`
Date: 2026-08-29

## Objective

Redesign the **linear equation** solution steps on the canonical `/solve`
path from generic one-line descriptions into genuinely educational steps that
teach the actual mathematical operations performed at each stage, without
changing any mathematical behavior.

## Existing Behavior (before)

Four to six steps, generic descriptions, result-only LaTeX (`3x-4=2`):

```
Step 1 [present]        latex: 3 x - 4 = 2
Step 2 [isolate]        latex: 3 x = 6        (no operation shown)
    desc: "Move the constant term -4 to the right-hand side..."
Step 3 [divide]         latex: x = 2          (no operation shown)
    desc: "Divide both sides by the coefficient..."
Step 4 [answer]         latex: x = 2
```

Missing: expansion, fraction clearing, variable moving — no operations shown,
just results.

## New Behavior (after)

Educational steps showing the actual operation applied to **both sides** at
each stage. Only rules that actually apply are displayed.

### Example 1: `3x - 4 = 2` (simple linear)

```
Step 1 [present]        3 x - 4 = 2
Step 2 [isolate]        aligned: 3 x - 4 = 2
                                          + 4
                                          3 x = 6
    desc: "Add 4 to both sides to isolate the variable term on the left."
Step 3 [divide]         aligned: 3 x = 6
                                          ÷ 3
                                          x = 2
    desc: "Divide both sides by the coefficient 3 to isolate the variable."
Step 4 [answer]         x = 2
```

### Example 2: `2(x + 3) = 10` (expansion + linear)

```
Step 1 [present]        2(x + 3) = 10
Step 2 [expand]         aligned: 2(x + 3) = 10
                                          2x + 6 = 10
    desc: "Distribute the multiplier across each term inside the parentheses
           using the distributive law: a(b + c) = ab + ac."
Step 3 [isolate]        aligned: 2x + 6 = 10
                                          - 6
                                          2x = 4
    desc: "Subtract 6 from both sides to isolate the variable term on the left."
Step 4 [divide]         aligned: 2x = 4
                                          ÷ 2
                                          x = 2
    desc: "Divide both sides by the coefficient 2 to isolate the variable."
Step 5 [answer]         x = 2
```

### Example 3: `x/3 + 2 = 5` (fraction clearing)

```
Step 1 [present]        x/3 + 2 = 5
Step 2 [multiply_both_sides]
    aligned: x/3 + 2 = 5
                 × 3
                 x + 6 = 15
    desc: "Multiply both sides by the least common denominator (3) to
           eliminate fractions."
Step 3 [isolate]
    aligned: x + 6 = 15
                 - 6
                 x = 9
    desc: "Subtract 6 from both sides to isolate the variable term on the left."
Step 5 [answer]         x = 9
```

### Example 4: `5 = 2x + 3` (variable on right)

```
Step 1 [present]        5 = 2x + 3
Step 2 [move_variable]
    aligned: 5 = 2x + 3
                 - 2x
                 5 - 2x = 3
    desc: "Subtract 2x from both sides to collect variable terms
           on the left-hand side."
Step 3 [isolate]
    aligned: 5 - 2x = 3
                 - 5
                 -2x = -2
    desc: "Subtract 5 from both sides to isolate the variable term on the left."
Step 4 [divide]
    aligned: -2x = -2
                 ÷ -2
                 x = 1
    desc: "Divide both sides by the coefficient -2 to isolate the variable."
Step 5 [answer]         x = 1
```

### Example 5: `-3x + 4 = 10` (negative coefficient)

```
Step 1 [present]        4 - 3x = 10
Step 2 [isolate]        aligned: 4 - 3x = 10
                                          - 4
                                          -3x = 6
    desc: "Subtract 4 from both sides to isolate the variable term on the left."
Step 3 [divide]
    aligned: -3x = 6
                 ÷ -3
                 x = -2
    desc: "Divide both sides by the coefficient -3 to isolate the variable."
Step 3 [answer]         x = -2
```

### Example 6: `x/2 - 3 = 5` (negative constant after fraction clearing)

```
Step 1 [present]        x/2 - 3 = 5
Step 2 [multiply_both_sides]
    aligned: x/2 - 3 = 5
                 × 2
                 x - 6 = 10
    desc: "Multiply both sides by the least common denominator (2) to
           eliminate fractions."
Step 3 [isolate]
    aligned: x - 6 = 10
                 + 6
                 x = 16
    desc: "Add 6 to both sides to isolate the variable term on the left."
Step 4 [answer]         x = 16
```

Note: When the constant is negative, the step correctly shows **addition** of
its absolute value (not `- -6`).

## Files Changed

| File | Change |
|------|--------|
| `math_engine/reasoning/rules/expand_rule.py` | Added `_format_expansion_latex` showing before/after with aligned environment; description now teaches distributive law. |
| `math_engine/reasoning/rules/multiply_both_sides_rule.py` | Added `_format_multiplication_latex` showing `× LCD` on both sides; description explains LCD. |
| `math_engine/reasoning/rules/move_variable_rule.py` | Added `_format_move_variable_latex` showing `± term` on both sides; handles negative coefficients with `+ |term|`. |
| `math_engine/reasoning/rules/move_constant_rule.py` | Added `_format_move_constant_latex` showing `± constant` on both sides; negative constants display as `+ |constant|`. |
| `math_engine/reasoning/rules/divide_coefficient_rule.py` | Added `_format_divide_latex` showing `÷ coefficient` on both sides; description names the coefficient. |
| `stress/phase32_stress.py` | New step-content + equivalence stress harness. |
| `stress/phase32_report.md` | This report. |

**Frontend: unchanged.** `buildStepNodes` already renders title, kind badge,
description and `$$latex$$`; multi-line content uses standard AMS
`aligned`/`gathered` environments that MathJax renders natively.

## Architectural Reasoning

- **Rules own their explanations.** Each rule's enriched step is generated by
  the rule that performed the operation, from the values it already computed —
  no second calculation layer, no frontend-hardcoded math, no per-equation
  canned text.
- **Pipeline preserved.** All five rules still run in the same order
  (expand → multiply → move_variable → isolate → divide); only the
  *presentation* is enriched. The solver's `_linear_steps` is unchanged.
- **Step model untouched.** Everything fits the existing
  `title/description/latex/metadata` contract; no new fields required.
- **Final answer untouched.** `_solve_equation` → `_render_result` is
  byte-identical; verified by byte-comparison across all Phase 32 cases and
  by the full P28/P29/P31 suites.
- **Only applicable rules fire.** The RuleEngine already skips rules whose
  `can_apply` returns false, so only relevant operations appear in the steps.

## Step Kinds (in order)

1. **present** — opening: "Solve the linear equation …"
2. **expand** — distributive law (only when parentheses exist)
3. **multiply_both_sides** — LCD multiplication (only when fractions exist)
4. **move_variable** — collect variable terms (only when variable on RHS)
5. **isolate** — move constant to RHS (only when constant on LHS)
6. **divide** — divide by coefficient (only when coefficient ≠ 1)
7. **answer** — closing: "The solution of the equation is …"

## Educational-Content Verification

`stress/phase32_stress.py` (structural assertions, not prose-matching):

| Suite | Passed | Total |
|-------|--------|-------|
| Representative cases (10 forms) | 10 | 10 |
| Phase 28 deterministic linear set | 22 | 22 |
| Randomized linear families | 100 | 100 |
| HTTP parity | 4 | 4 |
| **Total** | **136** | **136** |

Every case asserts: correct step kinds for the equation's structure; no
irrelevant rule steps; each step's latex contains the operation symbol
(`+`, `-`, `×`, `÷`) and shows both sides; descriptions mention "both sides"
and the specific value/coefficient; `final_answer` byte-equal to pre-phase
implementation and mathematically equivalent to independent SymPy reference.

Representative forms covered: basic (`3x-4=2`), expansion (`2(x+3)=10`),
fraction clearing (`x/3+2=5`), variable on RHS (`5=2x+3`), negative
coefficient (`-3x+4=10`), parenthesized fraction (`(2x+4)/3=8`), negative
constant after clearing (`x/2-3=5`), zero root (`2x=0`), simple fraction
(`x/2=5`).

## Mathematical Regression Results

| Suite | Result |
|-------|--------|
| Phase 28 linear | 147/147 (engine / adapter / reasoning / HTTP) |
| Phase 28 quadratic | 149/149 (all layers) |
| Phase 29 linear | 97/97 (all layers) |
| Phase 29 quadratic | 99/99 (all layers) |
| Phase 29 differentiation | 100/100 (all layers) |
| Phase 29 juxtaposition | 8/8 |
| Phase 31 quadratic educational | 139/139 |
| Phase 32 linear educational | 136/136 |
| `api.test_api` | exit 0 |
| `integration/test_ocr_to_api.py` | 6 pre-existing `dbl_backslash` parse failures only (unchanged) |
| Doctests (changed modules) | 0 failed |
| `py_compile` changed files | OK |
| `node --check` script.js / animation.js | OK |

## Edge Cases

- **Zero root (`2x = 0`):** Only `present → divide → answer` (no isolate,
  since constant is already zero).
- **Simple fraction (`x/2 = 5`):** Only `present → multiply_both_sides →
  answer` (variable isolated after clearing).
- **Negative coefficient (`-3x + 4 = 10`):** Division shows `÷ -3`; final
  answer `x = -2`.
- **Variable on RHS (`5 = 2x + 3`):** `move_variable` fires first,
  subtracting `2x` from both sides.
- **Negative constant after clearing (`x/2 - 3 = 5`):** After `× 2`,
  constant is `-6`; isolate step correctly shows `+ 6` (not `- -6`).
- **Repeated variable on both sides:** `move_variable` correctly subtracts
  the RHS variable term from both sides.
- **Large coefficients / rationals:** All substitutions render exact
  Rationals (`\frac{1}{2}`), no decimal drift.

## Known Limitations

- The division symbol `÷` is used (matching the product spec); `\div` in
  LaTeX renders correctly in MathJax.
- Negative coefficient division shows `÷ -3` (literal); could be improved to
  "multiply by -1/3" but literal division is deliberate for teaching the
  inverse operation.
- Variable moving when coefficient is negative shows `+ |term|` (addition of
  absolute value) — this is mathematically correct and pedagogically clearer
  than `- -2x`.
- The `present` and `answer` steps remain simple (no aligned environment) as
  they are bookends only.
- No separate "simplify" step for linear (unlike quadratic Phase 31) — the
  division step directly yields the final simplified result.

## Final Verdict

**Phase 32: SUCCESS.** Linear final answers are byte-identical to the
pre-phase implementation across all regression suites; the step sequence now
shows the actual mathematical operation applied to both sides at every stage;
only applicable rules produce steps; no architectural duplication; no
unrelated capability modified.