"""Parsing layer: convert LaTeX strings into SymPy expressions.

Responsible for interpreting LaTeX token output and constructing an internal
representation ready for the solver stage. The only public entry point is
:func:`latex_to_expression`; nothing outside this package should call SymPy's
LaTeX parser directly.
"""

from .latex_parser import latex_to_expression
from .parser_exceptions import (
    EmptyLatexError,
    InvalidLatexError,
    LatexParserError,
    UnsupportedLatexError,
)

__all__ = [
    "latex_to_expression",
    "LatexParserError",
    "EmptyLatexError",
    "InvalidLatexError",
    "UnsupportedLatexError",
]
