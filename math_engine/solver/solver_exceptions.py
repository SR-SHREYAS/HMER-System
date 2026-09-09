"""Solver-specific exceptions for the math engine.

These exceptions signal failures inside the solver layer only. They form a small
hierarchy rooted at :class:`SolverError` so callers can catch a specific failure
or any solver failure with a single handler.
"""


class SolverError(Exception):
    """Base class for every error raised by the solver layer."""


class UnknownTaskError(SolverError):
    """Raised when a solver cannot be chosen because the task is unknown.

    This covers expressions whose task was never classified or was classified
    as :attr:`TaskType.UNKNOWN`.
    """


class SolverNotImplementedError(SolverError):
    """Raised when a known task has no solver registered yet."""