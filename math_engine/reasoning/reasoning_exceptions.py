"""Reasoning-specific exceptions for the math engine.

These exceptions signal failures inside the reasoning layer only. They form a
small hierarchy rooted at :class:`ReasoningError` so callers can catch a
specific failure or any reasoning failure with a single handler.
"""


class ReasoningError(Exception):
    """Base class for every error raised by the reasoning layer."""


class ReasonerNotFoundError(ReasoningError):
    """Raised when no reasoner exists for a solution's task."""


class ReasoningGenerationError(ReasoningError):
    """Raised when a reasoner fails to produce reasoning for a solution."""