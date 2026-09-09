"""Public data models shared across the math engine.

Exposes the internal language of the engine: the parsed :class:`Expression`,
its :class:`TaskType` classification, individual :class:`Step` entries, and the
final :class:`Solution`. Later modules communicate exclusively through these
objects rather than raw SymPy values.
"""

from .expression import Expression
from .solution import Solution
from .step import Step
from .task import TaskType

__all__ = ["Expression", "Step", "Solution", "TaskType"]