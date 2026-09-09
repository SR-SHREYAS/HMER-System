"""Reasoning layer for the math engine.

Defines the architecture every future reasoning implementation follows.
Concrete reasoners inherit :class:`BaseReasoner`, declare the task they handle,
and are obtained through :class:`ReasonerFactory`. The :class:`ReasoningEngine`
turns completed solutions into step-by-step explanations.
"""

from .base_reasoner import BaseReasoner
from .equation_reasoner import EquationReasoner
from .quadratic_reasoner import QuadraticReasoner
from .reasoning_engine import ReasoningEngine, default_engine
from .reasoning_exceptions import (
    ReasoningError,
    ReasoningGenerationError,
    ReasonerNotFoundError,
)
from .reasoning_factory import ReasonerFactory, default_reasoner_factory

__all__ = [
    "BaseReasoner",
    "EquationReasoner",
    "QuadraticReasoner",
    "ReasoningEngine",
    "default_engine",
    "ReasonerFactory",
    "default_reasoner_factory",
    "ReasoningError",
    "ReasonerNotFoundError",
    "ReasoningGenerationError",
]