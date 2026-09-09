"""FastAPI entry point exposing the math engine over HTTP.

Exposes a minimal API around the stable math engine. The engine itself is a
black box: this module only wires request decoding to :mod:`api.adapter` and
request encoding of its response.

To run locally:

    PYTHONPATH=. uvicorn api.main:app --reload

The ``/solve`` endpoint accepts:

.. code-block:: json

    {"input": "x^2", "type": "derivative"}
"""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .adapter import solve

app = FastAPI(
    title="HMER Math Engine API",
    version="0.1.0",
    description="Symbolic differentiation over HTTP.",
)


class SolveRequest(BaseModel):
    """JSON body accepted by ``POST /solve``."""

    input: str = Field(description="Raw LaTeX string describing the problem.")
    type: Literal["derivative", "equation"] = Field(
        default="derivative",
        description=(
            "Requested problem type. ``derivative`` is kept for backward "
            "compatibility, but routing is structural: an equality input is "
            "always solved as an equation."
        ),
    )


@app.post("/solve")
def solve_endpoint(request: SolveRequest) -> dict:
    """Solve a LaTeX math problem and return the API contract response."""
    return solve(request.input, request.type)


@app.get("/health")
def health() -> dict:
    """Simple liveness probe."""
    return {"status": "ok"}


__all__ = ["app"]