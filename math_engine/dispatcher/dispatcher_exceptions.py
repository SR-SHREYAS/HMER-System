"""Dispatcher-specific exceptions for the math engine.

These exceptions signal that an expression could not be passed through the
classification step. They form a small hierarchy rooted at
:class:`DispatcherError` so callers can catch a specific failure or any
dispatcher failure with one handler.
"""


class DispatcherError(Exception):
    """Base class for every error raised by the dispatcher layer."""


class InvalidExpressionError(DispatcherError):
    """Raised when :func:`dispatch` receives something other than an Expression."""