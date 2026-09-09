# Phase 31 -- Educational Quadratic Step Report

Structured content checks over the canonical `/solve` adapter path.

| Suite | Passed | Total |
|-------|--------|-------|
| Representative cases | 11 | 11 |
| Phase 28 deterministic quadratic set | 24 | 24 |
| Randomized quadratic families | 100 | 100 |
| HTTP parity | 4 | 4 |

Every case asserts: exactly 5 steps with kinds `normalize_quadratic -> extract_coefficients -> compute_discriminant -> classify_roots -> quadratic_formula`; no separate `simplify_roots` step; coefficients `a, b, c` rendered explicitly; discriminant formula + substitution + result; classification showing all three discriminant cases plus the applicable one; quadratic formula with general form, substitution, evaluation and simplified roots; final_answer byte-equal to the Phase 28/30 implementation and mathematically equivalent to an independent SymPy reference.

_No failures._
