"""Convert LaTeX strings into SymPy mathematical expressions.

This module is the only public entry point for mathematical parsing within the
math engine. It wraps SymPy's own LaTeX parser with input normalization and
structured error handling so that no other package talks to the SymPy parser
directly.

The single public function is :func:`latex_to_expression`.
"""

from __future__ import annotations

import re

from sympy import Basic
from sympy.parsing.latex import parse_latex
from sympy.parsing.latex.errors import LaTeXParsingError

from .parser_exceptions import (
    EmptyLatexError,
    InvalidLatexError,
    UnsupportedLatexError,
)

#: Pairs of surrounding math-mode delimiters that may wrap a bare expression.
_MATH_DELIMITERS: tuple[tuple[str, str], ...] = (
    (r"\[", r"\]"),
    (r"\(", r"\)"),
    ("$$", "$$"),
    ("$", "$"),
)

#: Reduces any run of whitespace to a single space.
_WHITESPACE_PATTERN = re.compile(r"\s+")


def latex_to_expression(latex: str) -> Basic:
    """Parse a LaTeX string into a SymPy expression.

    Parameters
    ----------
    latex : str
        The LaTeX source to convert, optionally wrapped in math-mode
        delimiters (``$...$``, ``$$...$$``, ``\\(...\\)`` or ``\\[...\\]``).

    Returns
    -------
    Basic
        A SymPy expression such as ``Eq``, ``Derivative`` or ``Integral``
        representing the parsed mathematics.

    Raises
    ------
    EmptyLatexError
        If the input is empty or becomes empty after normalization.
    InvalidLatexError
        If the input cannot be parsed by the underlying SymPy parser.
    UnsupportedLatexError
        If the parsed result is not a valid SymPy expression.
    """
    normalized = _normalize_latex(latex)
    parsed = _parse_expression(normalized)
    return _validate_expression(parsed)


def _normalize_latex(latex: str) -> str:
    """Strip delimiters and whitespace from a raw LaTeX string.

    Returns a single-line LaTeX body free of surrounding math-mode delimiters,
    raising :class:`EmptyLatexError` when nothing meaningful remains.
    """
    text = latex.strip()
    for start, end in _MATH_DELIMITERS:
        if text.startswith(start) and text.endswith(end):
            if len(text) >= len(start) + len(end):
                text = text[len(start) : -len(end)]
                break

    text = _WHITESPACE_PATTERN.sub(" ", text).strip()
    if not text:
        raise EmptyLatexError("Cannot parse an empty or whitespace-only LaTeX string.")
    return text


def _parse_expression(normalized: str) -> Basic:
    """Delegate to SymPy's LaTeX parser with error translation.

    Args:
        normalized: A whitespace-normalized LaTeX string.

    Returns:
        The raw SymPy object produced by the parser.

    Raises:
        InvalidLatexError: When the underlying parser rejects the input.
    """
    try:
        return parse_latex(normalized)
    except LaTeXParsingError as exc:
        raise InvalidLatexError(
            f"Could not parse LaTeX {normalized!r}: {exc}"
        ) from exc
    except Exception as exc:  # noqa: BLE001 - parser may raise varied ANTLR errors
        raise InvalidLatexError(
            f"Unexpected failure while parsing LaTeX {normalized!r}: {exc}"
        ) from exc


def _validate_expression(parsed: object) -> Basic:
    """Ensure the parser output is a valid SymPy expression.

    Args:
        parsed: The object returned by the SymPy LaTeX parser.

    Returns:
        The same object, confirmed as a SymPy :class:`Basic` expression.

    Raises:
        UnsupportedLatexError: If the result is not a SymPy expression.
    """
    if not isinstance(parsed, Basic):
        raise UnsupportedLatexError(
            f"Parsing produced a non-expression result of type {type(parsed).__name__}."
        )
    return parsed