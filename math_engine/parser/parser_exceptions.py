"""Parser-specific exceptions for the math engine.

These exceptions signal that a LaTeX string could not be converted into a
SymPy expression. They form a small hierarchy rooted at
:class:`LatexParserError` so callers can catch either a specific failure
mode or any parsing failure with a single handler.
"""


class LatexParserError(Exception):
    """Base class for every error raised by the parser layer."""


class EmptyLatexError(LatexParserError):
    """Raised when the input LaTeX string is empty or only whitespace."""


class InvalidLatexError(LatexParserError):
    """Raised when the input LaTeX string cannot be parsed into an expression."""


class UnsupportedLatexError(LatexParserError):
    """Raised when the input parses to a result the parser does not support."""
