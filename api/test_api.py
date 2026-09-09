"""Minimal offline test harness for the API layer.

Runs a handful of hardcoded inputs through the full bridge
(LaTeX -> Parser -> Expression -> Engine -> Response) via the adapter and,
optionally, over the HTTP endpoint using FastAPI's TestClient. This is a
throwaway smoke script, not a formal test suite.

Usage:
    PYTHONPATH=. .venv/bin/python api/test_api.py
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from .adapter import solve
from .main import app


TEST_CASES: list[tuple[str, str]] = [
    ("x^2", "derivative"),
    ("sin(x^2)", "derivative"),
    ("x^x", "derivative"),
    ("3x-4=2", "derivative"),
    ("2x+5=13", "derivative"),
    ("x^2=25", "equation"),
    ("x^2+5x+6=0", "equation"),
    ("2(x+3)=10", "equation"),
    ("5=x^2+4x", "equation"),
]

EDGE_CASES: list[str] = [
    "",
    "   ",
    "\\frac{d}{dx}(x^3)",
    "unsupported_math !!!",
    "x^2 + y^2 = ",
]


def _fmt(response: dict) -> str:
    ver = response.get("verification", {})
    passed = ver.get("passed", False)
    method = ver.get("method", "?")
    return (
        f"success={response.get('success')} "
        f"passed={passed} method={method} "
        f"result={response.get('result')!r}"
    )


def run_adapter_tests() -> None:
    print("== Adapter (offline) tests ==")
    for latex, problem_type in TEST_CASES:
        response = solve(latex, problem_type)
        print(f"input: {latex!r}")
        print(f"  -> {_fmt(response)}")
        print(f"  -> steps: {len(response.get('steps', []))}, "
              f"error: {response.get('error')}")


def run_http_tests() -> None:
    print("== HTTP (FastAPI TestClient) tests ==")
    client = TestClient(app)
    for latex, problem_type in TEST_CASES:
        payload = {"input": latex, "type": problem_type}
        resp = client.post("/solve", json=payload)
        body = resp.json()
        print(f"POST /solve {json.dumps(payload)}")
        print(f"  -> status={resp.status_code} {_fmt(body)}")


def run_edge_tests() -> None:
    print("== Edge cases ==")
    client = TestClient(app)
    for latex in EDGE_CASES:
        resp = client.post("/solve", json={"input": latex, "type": "derivative"})
        body = resp.json()
        print(f"POST /solve {latex!r} status={resp.status_code} "
              f"success={body.get('success')} error={body.get('error')!r}")


def main() -> None:
    run_adapter_tests()
    print()
    run_http_tests()
    print()
    run_edge_tests()


if __name__ == "__main__":
    main()