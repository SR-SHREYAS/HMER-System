"""Abstract base class for every mathematical solver.

This module defines the contract every concrete solver must honour. It contains
no mathematical logic; it only fixes the interface used by the rest of the math
engine to invoke a solver.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from ..models import Expression, Solution, TaskType


class BaseSolver(ABC):
    """Interface every mathematical solver implements.

    Subclasses declare the task they handle through :attr:`task_type` and
    implement :meth:`solve`.

    Attributes
    ----------
    task_type:
        The :class:`TaskType` this solver is responsible for.
    """

    task_type: ClassVar[TaskType] = TaskType.UNKNOWN

    @abstractmethod
    def solve(self, problem: Expression) -> Solution:
        """Solve a classified expression.

        Parameters
        ----------
        problem :
            The expression to solve; its ``task`` is expected to already be
            classified.

        Returns
        -------
        Solution
            The complete solution produced by the solver.

        Raises
        ------
        SolverError
            If the expression cannot be solved by this solver.
        """
        ...