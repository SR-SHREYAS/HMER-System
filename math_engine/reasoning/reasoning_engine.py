"""Reasoning engine orchestrating solution-to-steps conversion.

The engine receives a completed :class:`Solution`, selects the reasoner that
matches the solution's task, generates an immutable sequence of :class:`Step`
objects, and returns a *new* solution carrying those steps. The input solution
is never modified.
"""

from __future__ import annotations

from dataclasses import replace

from ..models import Solution
from .base_reasoner import BaseReasoner
from .reasoning_exceptions import (
    ReasonerNotFoundError,
    ReasoningGenerationError,
)
from .reasoning_factory import ReasonerFactory, default_reasoner_factory


class ReasoningEngine:
    """Converts solved expressions into educational explanations.

    Parameters
    ----------
    factory :
        The reasoner registry to use, or the default process-wide factory when
        omitted.
    """

    def __init__(self, factory: ReasonerFactory | None = None) -> None:
        self._factory = (
            factory if factory is not None else default_reasoner_factory
        )

    def generate(self, solution: Solution) -> Solution:
        """Generate reasoning steps for a solved expression.

        Parameters
        ----------
        solution :
            A completed solution whose expression task has been classified.

        Returns
        -------
        Solution
            A new solution equal to the input but with ``steps`` populated.

        Raises
        ------
        ReasonerNotFoundError
            If no reasoner is registered for the solution's task.
        ReasoningGenerationError
            If the selected reasoner fails to produce reasoning.
        """
        reasoner = self._select_reasoner(solution)
        steps = self._generate_steps(reasoner, solution)
        return replace(solution, steps=steps)

    def _select_reasoner(self, solution: Solution) -> BaseReasoner:
        """Resolve the reasoner responsible for the solution's task.

        Parameters
        ----------
        solution :
            The solution to reason about.

        Returns
        -------
        BaseReasoner
            A reasoner matching the solution's task.

        Raises
        ------
        ReasonerNotFoundError
            If no reasoner is registered for the task.
        """
        return self._factory.build(solution.expression.task)

    def _generate_steps(
        self, reasoner: BaseReasoner, solution: Solution
    ) -> tuple:
        """Run the reasoner and translate failures.

        Parameters
        ----------
        reasoner :
            The reasoner to invoke.
        solution :
            The solution passed to the reasoner.

        Returns
        -------
        tuple
            The generated sequence of reasoning steps.

        Raises
        ------
        ReasoningGenerationError
            If the reasoner raises while generating.
        """
        try:
            return reasoner.generate(solution)
        except ReasonerNotFoundError:
            raise
        except Exception as exc:  # noqa: BLE001 - propagate any failure
            raise ReasoningGenerationError(
                f"Reasoning generation failed for task "
                f"{solution.expression.task!r}: {exc}"
            ) from exc


#: A process-wide reasoning engine built on the default reasoner factory.
default_engine = ReasoningEngine()