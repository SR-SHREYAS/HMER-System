"""Solver layer for the math engine.

Defines the architecture every mathematical solver follows. Concrete solvers
inherit :class:`BaseSolver`, declare the task they handle, and are obtained
through :class:`SolverFactory`.
"""

from .base_solver import BaseSolver
from .derivative_solver import DerivativeSolver
from .equation_solver import EquationSolver
from .quadratic_solver import QuadraticSolver
from .solver_exceptions import (
    SolverError,
    SolverNotImplementedError,
    UnknownTaskError,
)
from .solver_factory import SolverFactory, default_factory

__all__ = [
    "BaseSolver",
    "DerivativeSolver",
    "EquationSolver",
    "QuadraticSolver",
    "SolverFactory",
    "default_factory",
    "SolverError",
    "UnknownTaskError",
    "SolverNotImplementedError",
]