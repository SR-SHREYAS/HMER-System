"""Component that converts raw symbolic output into a clean human-readable form.

:class:`Simplifier` transforms a SymPy expression produced by the
differentiation rule pipeline into an equivalent but simpler expression using a
fixed set of small, predictable rewrites:

* constant folding (``0 + 1 -> 1``, ``2 * 3 -> 6``),
* identity removal (``x * 1 -> x``, ``x + 0 -> x``, ``0 * x -> 0``),
* power cleanup (``x^1 -> x``, ``x^0 -> 1``),
* basic combination of like terms (``x + x -> 2 x``).

Only these mechanical rewrites are applied. The component deliberately does not
call :func:`sympy.simplify` and never expands products of sums, so groupings
such as ``2*(x + 1)`` survive unchanged.
"""

from __future__ import annotations

from sympy import Add, Mul, Pow, Rational


class Simplifier:
    """Apply minimal, predictable rewrites to a SymPy expression.

    The simplifications are applied bottom-up over the expression tree and the
    exact rules above; nothing else is touched.
    """

    def simplify(self, expression):
        """Return a minimal, predictable form of ``expression``.

        Parameters
        ----------
        expression :
            The raw SymPy expression to clean up.

        Returns
        -------
        A SymPy expression with constants folded, identity terms removed,
        trivial powers cleaned and like terms combined.
        """
        return self._simplify(expression)

    def _simplify(self, expression):
        """Recursively rewrite ``expression`` using the simplification rules."""
        if isinstance(expression, Pow):
            return self._simplify_pow(expression)
        if isinstance(expression, Mul):
            return self._simplify_mul(expression)
        if isinstance(expression, Add):
            return self._simplify_add(expression)
        return expression

    def _simplify_pow(self, expression):
        """Collapse trivial exponents (``x^1 -> x``, ``x^0 -> 1``)."""
        base = self._simplify(expression.base)
        exponent = expression.exp
        if exponent == 1:
            return base
        if exponent == 0:
            return Rational(1)
        return Pow(base, exponent)

    def _simplify_mul(self, expression):
        """Fold numeric coefficients and identities inside a product.

        Numeric factors are multiplied into a single coefficient, factors equal
        to one are dropped and a zero factor collapses the product to zero.
        Repeated factors are combined into powers (``x * x -> x**2``). When a
        factor is itself a sum, the product is kept grouped so that
        ``2 * (x + 1)`` never expands to ``2*x + 2``.
        """
        coefficient = Rational(1)
        factors = []
        for factor in expression.args:
            cleaned = self._simplify(factor)
            if cleaned == 0:
                return Rational(0)
            if cleaned.is_Number:
                coefficient = coefficient * cleaned
            elif cleaned != 1:
                factors.append(cleaned)

        if not factors:
            return coefficient

        if any(factor.is_Add for factor in factors):
            if coefficient == 1:
                return Mul(*factors, evaluate=False)
            return Mul(coefficient, *factors, evaluate=False)

        product = Mul(*factors, evaluate=True)
        return Mul(coefficient, product, evaluate=True)

    def _simplify_add(self, expression):
        """Fold numeric constants and like terms in a sum.

        Zero terms are dropped, numeric terms are combined into one constant
        and terms that are ``x*x``-style like terms are merged (``x + x``
        becomes ``2*x``).
        """
        terms = [self._simplify(term) for term in expression.args]
        numeric = Rational(0)
        kept = []
        for term in terms:
            if term == 0:
                continue
            if term.is_Number:
                numeric = numeric + term
            else:
                kept.append(term)
        if numeric != 0:
            kept.append(numeric)
        if not kept:
            return Rational(0)
        return Add(*kept, evaluate=True)


__all__ = ["Simplifier"]