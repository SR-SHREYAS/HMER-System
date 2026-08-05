"""Factory that selects a solver for a classified expression.

The factory holds a registry mapping each :class:`TaskType` to the solver class
that handles it. New solvers register themselves against the registry rather
than being hard-wired into branching logic, so adding support for a task is a
minimal, localized change.
"""

from __future__ import annotations

from typing import TypeVar

from ..models import Expression, TaskType
from .base_solver import BaseSolver
from .solver_exceptions import SolverNotImplementedError, UnknownTaskError

T = TypeVar("T", bound="BaseSolver")


class SolverFactory:
    """Registry-backed builder of concrete solver instances.

    A single factory can be shared across the engine, or a new one can be
    created and populated per context.
    """

    def __init__(self) -> None:
        self._builders: dict[TaskType, type[BaseSolver]] = {}

    def register(self, solver_cls: type[T]) -> type[T]:
        """Register a solver class for its declared task type.

        Suitable for use as a method call or as a class decorator.

        Parameters
        ----------
        solver_cls :
            A :class:`BaseSolver` subclass whose :attr:`~BaseSolver.task_type`
            is used as the registry key.

        Returns
        -------
        type[T]
            The registered solver class, enabling decorator usage.
        """
        self._builders[solver_cls.task_type] = solver_cls
        return solver_cls

    def build(self, problem: Expression) -> BaseSolver:
        """Return a solver instance able to handle the given expression.

        Parameters
        ----------
        problem :
            The expression whose ``task`` has already been classified.

        Returns
        -------
        BaseSolver
            An instantiated solver matching the expression's task.

        Raises
        ------
        UnknownTaskError
            If the expression has no task or its task is unknown.
        SolverNotImplementedError
            If the task is known but no solver has been registered for it.
        """
        task = problem.task
        if task is None or task is TaskType.UNKNOWN:
            raise UnknownTaskError(
                f"Cannot select a solver for an unknown task (task={task!r})."
            )

        solver_cls = self._builders.get(task)
        if solver_cls is None:
            raise SolverNotImplementedError(
                f"No solver has been implemented for task {task.value!r} yet."
            )
        return solver_cls()


#: A process-wide factory that future solvers can register against.
default_factory = SolverFactory()