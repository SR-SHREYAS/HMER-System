"""Convert LaTeX strings into SymPy mathematical expressions.

This module is the only public entry point for mathematical parsing within the
math engine. It wraps SymPy's own LaTeX parser with input normalization and
structured error handling so that no other package talks to the SymPy parser
directly.

The single public function is :func:`latex_to_expression`.
"""

from __future__ import annotations

import re

from sympy import Basic, Mul, Symbol
from sympy.core.function import AppliedUndef
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
    parsed = _resolve_implicit_multiplication(parsed)
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


def _resolve_implicit_multiplication(parsed: Basic) -> Basic:
    """Rewrite juxtaposed multiplication that SymPy misparses as a call.

    SymPy's LaTeX parser reads ``x(x - 2)`` as the undefined function call
    ``Function('x')(x - 2)`` instead of the product ``x*(x - 2)``. A bare
    symbol directly followed by a parenthesis is far more likely to mean
    implicit multiplication in handwritten math, so every ``AppliedUndef``
    whose name is also a free symbol of the expression is rewritten into a
    product.

    Real mathematical functions (``\\sin``, ``\\cos``, ``\\log``, ...) are
    parsed as concrete SymPy ``Function`` objects, never as ``AppliedUndef``,
    so they are left untouched. Undefined function names that never appear as
    free symbols (for example ``f`` in ``f(x)``) are also preserved, so an
    ordinary function call keeps its meaning.
    """
    if not parsed.has(AppliedUndef):
        return parsed
    free_names = {symbol.name for symbol in parsed.free_symbols}

    def _is_juxtaposed(node: Basic) -> bool:
        return (
            isinstance(node, AppliedUndef) and node.func.name in free_names
        )

    def _to_product(node: AppliedUndef) -> Basic:
        return Mul(Symbol(node.func.name), *node.args)

    return parsed.replace(_is_juxtaposed, _to_product)


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