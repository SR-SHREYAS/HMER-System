"""Complete solution model for the math engine.

Defines the immutable object returned at the end of the engine pipeline,
binding the original expression to its ordered reasoning steps and the final
answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .expression import Expression
from .step import Step


@dataclass(frozen=True, slots=True)
class Solution:
    """A complete solution produced by the mathematical engine.

    Instances are immutable. The ordered sequence of steps is stored as a tuple
    to preserve immutability and stable ordering.

    Attributes
    ----------
    expression:
        The expression the solution addresses.
    steps:
        The ordered reasoning steps that lead to the answer.
    final_answer:
        The finished result as a string.
    metadata:
        Arbitrary auxiliary information attached to the solution.
    """

    expression: Expression
    steps: tuple[Step, ...]
    final_answer: str
    metadata: dict[str, Any] = field(default_factory=dict)