"""Reasoning step model for the math engine.

Represents one discrete step of a solution. This is a pure data structure; it
holds no solving or display logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Step:
    """A single reasoning step in a solution.

    Attributes
    ----------
    title:
        A short heading describing the step.
    description:
        A human-readable explanation of what the step does.
    latex:
        The LaTeX rendering associated with the step's result.
    metadata:
        Arbitrary auxiliary information attached to the step.
    """

    title: str
    description: str
    latex: str
    metadata: dict[str, Any] = field(default_factory=dict)