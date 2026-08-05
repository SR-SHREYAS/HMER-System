"""Factory that selects a reasoner for a classified solution.

The factory holds a registry mapping each :class:`TaskType` to the reasoner
class that handles it. New reasoners register themselves against the registry
rather than being hard-wired into branching logic, so adding support for a task
is a minimal, localized change.
"""

from __future__ import annotations

from typing import TypeVar

from ..models import TaskType
from .base_reasoner import BaseReasoner
from .reasoning_exceptions import ReasonerNotFoundError

T = TypeVar("T", bound="BaseReasoner")


class ReasonerFactory:
    """Registry-backed builder of concrete reasoner instances.

    A single factory can be shared across the engine, or a new one can be
    created and populated per context.
    """

    def __init__(self) -> None:
        self._builders: dict[TaskType, type[BaseReasoner]] = {}

    def register(self, reasoner_cls: type[T]) -> type[T]:
        """Register a reasoner class for its declared task type.

        Suitable for use as a method call or as a class decorator.

        Parameters
        ----------
        reasoner_cls :
            A :class:`BaseReasoner` subclass whose :attr:`~BaseReasoner.task_type`
            is used as the registry key.

        Returns
        -------
        type[T]
            The registered reasoner class, enabling decorator usage.
        """
        self._builders[reasoner_cls.task_type] = reasoner_cls
        return reasoner_cls

    def build(self, task: TaskType | None) -> BaseReasoner:
        """Return a reasoner instance able to handle the given task.

        Parameters
        ----------
        task :
            The classified task of the solution to reason about.

        Returns
        -------
        BaseReasoner
            An instantiated reasoner matching the task.

        Raises
        ------
        ReasonerNotFoundError
            If no reasoner is registered for the task.
        """
        if task is None:
            raise ReasonerNotFoundError(
                "Cannot select a reasoner for an unclassified task."
            )

        reasoner_cls = self._builders.get(task)
        if reasoner_cls is None:
            raise ReasonerNotFoundError(
                f"No reasoner has been registered for task {task.value!r} yet."
            )
        return reasoner_cls()


#: A process-wide factory that future reasoners can register against.
default_reasoner_factory = ReasonerFactory()