"""Routing parsed expressions to the correct solver.

Responsible for inspecting an expression's type and selecting the appropriate
solver module. The only public entry point is :func:`dispatch`.
"""

from .dispatcher import dispatch
from .dispatcher_exceptions import DispatcherError, InvalidExpressionError

__all__ = [
    "dispatch",
    "DispatcherError",
    "InvalidExpressionError",
]