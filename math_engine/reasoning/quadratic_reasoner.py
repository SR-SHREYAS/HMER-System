"""Concrete reasoner for quadratic equations.

:class:`QuadraticReasoner` explains solutions to quadratic equations. The
mathematical steps -- normalization, coefficient extraction, discriminant
calculation, root classification, quadratic formula and simplification -- are
all produced by the :class:`QuadraticSolver` during its rule pipeline, so this
reasoner only reuses those already-generated steps in order. It performs no
additional mathematics and never modifies a step; it simply returns the steps
carried on the completed solution.
"""

from __future__ import annotations

from ..models import Solution, Step, TaskType
from .base_reasoner import BaseReasoner
from .reasoning_exceptions import ReasoningGenerationError
from .reasoning_factory import default_reasoner_factory


@default_reasoner_factory.register
class QuadraticReasoner(BaseReasoner):
    """Reasoner that relays the steps produced by the quadratic solver.

    The solver already generates the complete, ordered reasoning chain. This
    reasoner validates that the solution is a quadratic solution and returns
    the already-produced steps unchanged, so the reasoning engine can present
    them to the frontend.
    """

    task_type = TaskType.QUADRATIC_EQUATION

    def generate(self, solution: Solution) -> tuple[Step, ...]:
        """Return the reasoning steps already computed by the solver.

        Parameters
        ----------
        solution :
            A completed quadratic solution.

        Returns
        -------
        tuple[Step, ...]
            The steps already stored on the solution, unchanged.

        Raises
        ------
        ReasoningGenerationError
            If the solution carries no steps (an unexpected state).
        """
        steps = solution.steps
        if not steps:
            raise ReasoningGenerationError(
                "QuadraticReasoner expects a solution with solver-generated "
                "steps, but none were present."
            )
        return steps