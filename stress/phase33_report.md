# Phase 33 -- Educational Derivative Step Report

Structured content checks over the canonical `/solve` adapter path for derivatives.

| Suite | Passed | Total |
|-------|--------|-------|
| Representative cases | 15 | 15 |
| Randomized derivative families | 50 | 50 |
| HTTP parity | 6 | 6 |
| **Total** | **81** | **81** |

Every case asserts: step structure matches the applicable rules; each step
shows the mathematical formula, the actual substitution with concrete values,
and the evaluated result. Final answers remain byte-equal to the pre-phase
implementation and mathematically equivalent to an independent SymPy reference.

_No failures._
