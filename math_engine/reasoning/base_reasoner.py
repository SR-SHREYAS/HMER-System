"""Abstract base class for every reasoner.

This module defines the contract every concrete reasoner must honour. It
contains no reasoning logic; it only fixes the interface used by the reasoning
engine to turn a completed solution into educational steps.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from ..models import Solution, Step, TaskType


class BaseReasoner(ABC):
    """Interface every reasoner implements.

    Subclasses declare the task they handle through :attr:`task_type` and
    implement :meth:`generate`.

    Attributes
    ----------
    task_type:
        The :class:`TaskType` this reasoner is responsible for.
    """

    task_type: ClassVar[TaskType] = TaskType.UNKNOWN

    @abstractmethod
    def generate(self, solution: Solution) -> tuple[Step, ...]:
        """Turn a completed solution into reasoning steps.

        Parameters
        ----------
        solution :
            A solved expression produced by the solver layer.

        Returns
        -------
        tuple[Step, ...]
            An immutable sequence of explanation steps.

        Raises
        ------
        ReasoningError
            If reasoning cannot be generated for the solution.
        """
        ...