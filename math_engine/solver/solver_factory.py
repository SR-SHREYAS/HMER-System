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
from .subproblem import SubproblemRequest, SubproblemResult, MAX_DELEGATION_DEPTH

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

    def solve_subproblem(self, request: "SubproblemRequest") -> "SubproblemResult":
        """Solve a subproblem by delegating to the appropriate capability solver.

        This method validates the request, constructs the appropriate child
        solver, executes it, and returns the result wrapped in a
        :class:`SubproblemResult`.

        Parameters
        ----------
        request :
            The subproblem request containing the capability to invoke,
            the expression to solve, and optional context/depth.

        Returns
        -------
        SubproblemResult
            The child solver's complete solution plus metadata.

        Raises
        ------
        ValueError
            If the request's capability does not match the expression's task,
            if depth is negative, or if depth exceeds the maximum allowed.
        UnknownTaskError
            If the expression's task is unknown.
        SolverNotImplementedError
            If no solver is registered for the expression's task.
        """
        if request.depth < 0:
            raise ValueError("Subproblem depth cannot be negative")
        if request.depth > MAX_DELEGATION_DEPTH:
            raise ValueError(
                f"Subproblem depth {request.depth} exceeds maximum "
                f"delegation depth of {MAX_DELEGATION_DEPTH}"
            )

        # Validate that the requested capability matches the expression's task
        expr_task = request.expression.task
        if expr_task is None:
            raise ValueError("Expression task is not classified")
        if request.capability != expr_task:
            raise ValueError(
                f"Subproblem capability {request.capability.value!r} does not "
                f"match expression task {expr_task.value!r}"
            )

        # Build the appropriate solver for the subproblem
        solver = self.build(request.expression)

        # Solve the subproblem
        solution = solver.solve(request.expression)

        # Wrap the result
        subproblem_kind = f"{request.capability.value}_subproblem"
        return SubproblemResult(
            solution=solution,
            subproblem_kind=subproblem_kind,
            conditions=(),
        )


#: A process-wide factory that future solvers can register against.
default_factory = SolverFactory()