"""OCR -> LaTeX -> API integration test.

Simulates imperfect OCR output by starting from the same token vocabulary
and formatter the HMER model uses (``mtl.datamodule.vocab`` +
``latex_formatter.format_sequence_as_latex``), then pushes the resulting
LaTeX through the ``/solve`` API endpoint exactly like a real recognition
pipeline would.

This is an exposure/triage script, not a formal test suite. It intentionally
does NOT aim for 100% success -- it exists to collect representative
real-world failures so the adapter/parser can be improved next.

Run from the repo root:

    PYTHONPATH=. .venv/bin/python integration/test_ocr_to_api.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent

#: LaTeX that mirrors what the OCR formatter emits from token sequences.
#: Each entry is a space-joined token sequence (the ``indices2label`` form).
OCR_TOKEN_SEQUENCES: list[str] = [
    # clean, single-token-per-symbol expressions
    "x ^ { 2 }",
    "\\sin ( x )",
    "x + \\sin ( x )",
    "\\cos ( x ^ { 2 } )",
    "x ^ { 3 } - x",
    # nested compositions
    "\\sin ( x ^ { 2 } + x )",
    "\\frac { x } { x ^ { 2 } + 1 }",
    "( x ^ { 2 } + 1 ) \\sin ( x )",
    "\\tan ( x + 1 )",
    # e / powers of e
    "e ^ { x }",
    "e ^ { x ^ { 2 } }",
    # radical
    "\\sqrt { x }",
    # general power
    "x ^ { x }",
    "\\sin ( x ) ^ { 2 }",
    "2 \\sin ( x ) \\cos ( x )",
]


#: Imperfect-OCR mutations applied to the token sequence before formatting.
NOISE_VARIANTS: dict[str, callable] = {
    "no_backslash": lambda s: s.replace("\\", ""),
    "dbl_backslash": lambda s: s.replace("\\", "\\\\"),
    "no_spaces": lambda s: s.replace(" ", ""),
}


def print_results(failures: dict[str, list[dict]]) -> None:
    for category, hits in sorted(failures.items()):
        if not hits:
            continue
        print(f"\n### {category.upper()} ({len(hits)})")
        for hit in hits[:5]:
            print(
                f"  input={hit['input']!r} "
                f"error={hit.get('error')!r} result={hit.get('result')!r}"
            )


def summarize(failures: dict[str, list[dict]]) -> None:
    print("\n================ FAILURE SUMMARY ================")
    total = sum(len(v) for v in failures.values())
    for cat, hits in sorted(failures.items()):
        print(f"  {cat:<15} {len(hits):>3}")
    print(f"  {'TOTAL':<15} {total:>3}")


def main() -> None:
    import sys as _sys

    if str(ROOT) not in _sys.path:
        _sys.path.insert(0, str(ROOT))

    from api.main import app

    client = TestClient(app)
    failures: dict[str, list[dict]] = {
        "parsing": [],
        "normalization": [],
        "unsupported": [],
        "engine": [],
        "timeout": [],
        "verification": [],
    }

    print("================ OCR -> API INTEGRATION ================")
    print(f"clean sequences: {len(OCR_TOKEN_SEQUENCES)}")

    print("-------------------- CLEAN -----------------------------------")
    for seq in OCR_TOKEN_SEQUENCES:
        latex = _formatter_latex(seq)
        _dispatch(client, latex, failures, variant="clean")

    print("\n-------------------- NOISE VARIANTS ---------------------------")
    for variant_name, mutate in NOISE_VARIANTS.items():
        for seq in OCR_TOKEN_SEQUENCES[:8]:  # subset keeps runtime bounded
            latex = _formatter_latex(mutate(seq))
            _dispatch(client, latex, failures, variant=variant_name)

    print_results(failures)
    summarize(failures)


def _formatter_latex(seq: str) -> str:
    """Run a token sequence through the real OCR latex formatter."""
    from latex_formatter import format_sequence_as_latex
    return format_sequence_as_latex(seq)


def _dispatch(client, latex: str, failures, variant: str) -> None:
    response = client.post("/solve", json={"input": latex, "type": "derivative"})
    body = response.json()
    ver = body.get("verification", {})
    passed = ver.get("passed", False)
    method = ver.get("method", "-")
    error = body.get("error")

    print("---------------------------------")
    print(f"VARIANT: {variant}")
    print(f"INPUT:   {latex}")
    print(f"RESULT:  {body.get('result')!r}")
    print(f"PASSED:  {passed}")
    print(f"METHOD:  {method}")
    if error:
        print(f"ERROR:   {error}")

    if error:
        category = _classify_error(error)
        failures[category].append({"input": latex, "error": error})
    elif not passed:
        failures["verification"].append({"input": latex, "result": body.get("result")})


def _classify_error(error: str) -> str:
    lowered = error.lower()
    if "timeout" in lowered:
        return "timeout"
    # The adapter reports parser exceptions by their engine name.
    if "parse" in lowered or "parser" in lowered:
        return "parsing"
    if "unsupported" in lowered:
        return "unsupported"
    if "timed" in lowered:
        return "timeout"
    return "engine"


if __name__ == "__main__":
    main()