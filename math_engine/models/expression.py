"""Core expression model for the math engine.

Defines the immutable object every later module receives instead of raw SymPy
objects. Holding the raw LaTeX alongside the parsed SymPy form and its task
classification keeps a single, well-typed contract between pipeline stages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sympy import Basic

from .task import TaskType


@dataclass(frozen=True, slots=True)
class Expression:
    """A parsed mathematical expression.

    Instances are immutable: raw_latex, the SymPy form, and the task
    classification are fixed once created.

    Attributes
    ----------
    raw_latex:
        The original LaTeX string the expression was parsed from.
    sympy_expression:
        The parsed SymPy expression object.
    task:
        The classification of the expression, or ``None`` if not yet known.
    metadata:
        Arbitrary auxiliary information attached to the expression.
    """

    raw_latex: str
    sympy_expression: Basic
    task: TaskType | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
