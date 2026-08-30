"""Phase 35.6 -- transformation-to-step presentation boundary tests.

These tests establish, *without* wiring any transformation into a production
solver, that:

1. a transformation produces mathematical data (`TransformationResult`),
2. a presentation adapter (`payload` / `step_from_result`) lets a rule consume
   that data while remaining the owner of the educational ``Step``,
3. two different capability wordings can consume the *same* transformation
   result and produce different (correct) Steps,
4. transformation metadata is preserved without forcing a Step representation,
5. branch-bearing results cross the boundary without being collapsed.

Run from the repo root:

    PYTHONPATH=. .venv/bin/python stress/phase35_6_stress.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from importlib import import_module

from sympy import Eq, latex, symbols

from math_engine.models import Step
from math_engine.transformations.algebraic import (
    AddSubtractBothSides,
    SquareRootTransformation,
)
from math_engine.transformations.presentation import (
    TransformationPayload,
    payload,
    step_from_result,
)
from math_engine.transformations import TransformationResult

x = symbols("x")


def _check(name, fn):
    try:
        fn()
        return name, True, None
    except AssertionError as exc:
        return name, False, str(exc)
    except Exception as exc:  # noqa: BLE001
        return name, False, f"{type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# 1. Transformation produces mathematical data.
# ---------------------------------------------------------------------------

def t_produces_math_data():
    result = AddSubtractBothSides().apply(Eq(x + 4, 9), -4)
    assert result.transformed_expression == Eq(x, 5), result.transformed_expression
    assert result.reversibility == "reversible"
    assert result.verification_required == "none"
    assert result.extraneous_risk is False


# ---------------------------------------------------------------------------
# 2. A presentation adapter lets the caller own the Step.
# ---------------------------------------------------------------------------

def t_payload_drops_default_step():
    result = AddSubtractBothSides().apply(Eq(x + 4, 9), -4)
    p = payload(result)
    # The payload must not carry the transformation's generic step wording.
    assert not hasattr(p, "step")
    assert p.transformed_expression == Eq(x, 5)


def t_step_owned_by_caller():
    result = AddSubtractBothSides().apply(Eq(x + 4, 9), -4)
    step = step_from_result(
        result,
        title="Isolate the variable term",
        description="Subtract 4 from both sides to isolate the variable term.",
        latex="\\begin{aligned}x + 4 = 9 \\\\ x = 5\\end{aligned}",
        kind="isolate",
    )
    assert step.metadata["kind"] == "isolate"
    assert "Subtract 4 from both sides" in step.description
    # transformation metadata survives (amount was preserved)
    assert step.metadata.get("amount") == result.metadata.get("amount")


# ---------------------------------------------------------------------------
# 3. Two capabilities consume the same result with different wording.
# ---------------------------------------------------------------------------

def t_capability_specific_wording():
    result = AddSubtractBothSides().apply(Eq(3 * x - 4, 2), 4)

    # A "linear" presentation.
    linear = step_from_result(
        result,
        title="Isolate the variable term",
        description="Add 4 to both sides to isolate the variable term.",
        latex=latex(Eq(3 * x, 6)),
        kind="isolate",
    )

    # A "generic/canonical" presentation of the same mathematics.
    generic = step_from_result(
        result,
        title="Add to both sides",
        description="Add the same quantity to both sides.",
        latex=latex(Eq(3 * x, 6)),
        kind="add_subtract_both_sides",
    )

    # Same underlying math, different (both) caller-owned presentation.
    assert result.transformed_expression == Eq(3 * x, 6)
    assert linear.metadata["kind"] == "isolate"
    assert generic.metadata["kind"] == "add_subtract_both_sides"
    assert linear.title != generic.title


# ---------------------------------------------------------------------------
# 4. Metadata preserved without forcing a Step representation.
# ---------------------------------------------------------------------------

def t_metadata_without_forced_step():
    result = AddSubtractBothSides().apply(Eq(x + 4, 9), -4)
    p = payload(result)
    assert p.metadata.get("amount") == result.metadata.get("amount")
    # The payload is presentation-free: no Step to inherit.
    assert not hasattr(p, "step")


# ---------------------------------------------------------------------------
# 5. Branch-bearing results cross the boundary without collapse.
# ---------------------------------------------------------------------------

def t_branch_preserved():
    result = SquareRootTransformation().apply(Eq(x**2, 25))
    p = payload(result)
    assert p.has_branches is True
    assert len(p.branches) == 2
    branch_vals = sorted(str(b) for b in p.branches)
    assert branch_vals == ["x = -5", "x = 5"], branch_vals


# ---------------------------------------------------------------------------
# 6. Separation / inversion checks (import inspection).
# ---------------------------------------------------------------------------

def _module_imports(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def t_transformations_do_not_import_rules():
    root = Path(__file__).resolve().parent.parent / "math_engine" / "transformations"
    for name in ("algebraic.py", "base.py", "verification.py", "presentation.py",
                 "conditions.py", "branches.py"):
        text = _module_imports(root / name)
        assert "solver" not in text or "import" not in _relevant_imports(text), name
        # Specifically: no transformation module may import solver or reasoning.rules.
        assert ".solver" not in text, f"{name} imports solver"
        assert "reasoning.rules" not in text, f"{name} imports reasoning.rules"


def _relevant_imports(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln.strip().startswith(("from ", "import "))]


def t_presentation_does_no_math():
    # The presentation module itself must not import sympy's solve/expand and
    # must not define any transformation arithmetic.
    root = Path(__file__).resolve().parent.parent / "math_engine" / "transformations"
    text = _module_imports(root / "presentation.py")
    assert "solve" not in text
    assert "expand(" not in text
    assert "simplify(" not in text


def t_no_solver_depends_on_transformations():
    # No capability solver may import the transformation layer.
    root = Path(__file__).resolve().parent.parent / "math_engine" / "solver"
    for name in ("equation_solver.py", "quadratic_solver.py", "derivative_solver.py"):
        text = _module_imports(root / name)
        assert "transformations" not in text, f"{name} imports transformations"


# ---------------------------------------------------------------------------

_COLLECTION = {
    "transformation_math": {
        "produces math data": t_produces_math_data,
    },
    "presentation_boundary": {
        "payload drops default step": t_payload_drops_default_step,
        "step owned by caller": t_step_owned_by_caller,
        "capability-specific wording": t_capability_specific_wording,
        "metadata without forced step": t_metadata_without_forced_step,
    },
    "branches": {
        "branch preserved": t_branch_preserved,
    },
    "separation": {
        "transformations don't import rules": t_transformations_do_not_import_rules,
        "presentation does no math": t_presentation_does_no_math,
        "no solver depends on transformations": t_no_solver_depends_on_transformations,
    },
}


def main() -> int:
    print("================ PHASE 35.6: PRESENTATION BOUNDARY ================")
    total = total_pass = total_fail = 0
    failures = []
    for section, cases in _COLLECTION.items():
        print(f"== {section} ==")
        sec_pass = sec_total = 0
        for label, fn in cases.items():
            sec_total += 1
            name, ok, msg = _check(f"{section}: {label}", fn)
            if ok:
                sec_pass += 1
            else:
                failures.append(f"{name} -> {msg}")
                print(f"  FAIL {label}: {msg}")
        total += sec_total
        total_pass += sec_pass
        total_fail += sec_total - sec_pass
        print(f"  {sec_pass}/{sec_total}\n")

    print("================ SUMMARY ================")
    print(f"  {total_pass}/{total} passed")
    if total_fail:
        for f in failures:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())