"""Public API layer for the HMER math engine.

This package is a thin adapter between external HTTP inputs (LaTeX strings)
and the stable :mod:`math_engine` black box. It owns all request
normalization, serialization and error handling; it contains no mathematical
logic and never modifies the engine itself.
"""

from .adapter import solve, solve_to_dict

__all__ = ["solve", "solve_to_dict"]