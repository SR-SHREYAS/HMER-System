"""Reusable mathematical rule engine.

This package provides the foundation for every future reasoning system. A rule
owns a single mathematical transformation (:class:`BaseRule`), and a
:class:`RuleEngine` sequences an ordered collection of rules over an expression
to produce reasoning steps. The initial rules (:class:`MoveConstantRule`,
:class:`DivideCoefficientRule`) reproduce the reasoning previously embedded in
:class:`EquationReasoner`.
"""

from .base_rule import BaseRule, linear_components, make_step
from .divide_coefficient_rule import DivideCoefficientRule
from .expand_rule import ExpandRule
from .extract_quadratic_coefficients_rule import ExtractQuadraticCoefficientsRule
from .move_constant_rule import MoveConstantRule
from .move_variable_rule import MoveVariableRule
from .multiply_both_sides_rule import MultiplyBothSidesRule
from .normalize_quadratic_rule import NormalizeQuadraticRule
from .rule_engine import RuleEngine
from .rule_exceptions import (
    RuleEngineError,
    RuleError,
    RuleNotApplicableError,
    UnsupportedExpressionError,
)

__all__ = [
    "BaseRule",
    "linear_components",
    "make_step",
    "DivideCoefficientRule",
    "ExpandRule",
    "ExtractQuadraticCoefficientsRule",
    "MoveConstantRule",
    "MoveVariableRule",
    "MultiplyBothSidesRule",
    "NormalizeQuadraticRule",
    "RuleEngine",
    "RuleEngineError",
    "RuleError",
    "RuleNotApplicableError",
    "UnsupportedExpressionError",
]