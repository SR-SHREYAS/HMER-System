"""Reusable mathematical rule engine.

This package provides the foundation for every future reasoning system. A rule
owns a single mathematical transformation (:class:`BaseRule`), and a
:class:`RuleEngine` sequences an ordered collection of rules over an expression
to produce reasoning steps. The initial rules (:class:`MoveConstantRule`,
:class:`DivideCoefficientRule`) reproduce the reasoning previously embedded in
:class:`EquationReasoner`.
"""

from .base_rule import BaseRule, linear_components, make_step
from .classify_quadratic_roots_rule import ClassifyQuadraticRootsRule
from .compute_discriminant_rule import ComputeDiscriminantRule
from .constant_derivative_rule import ConstantDerivativeRule
from .divide_coefficient_rule import DivideCoefficientRule
from .expand_rule import ExpandRule
from .extract_derivative_structure_rule import ExtractDerivativeStructureRule
from .extract_quadratic_coefficients_rule import ExtractQuadraticCoefficientsRule
from .move_constant_rule import MoveConstantRule
from .move_variable_rule import MoveVariableRule
from .multiply_both_sides_rule import MultiplyBothSidesRule
from .normalize_quadratic_rule import NormalizeQuadraticRule
from .quadratic_formula_rule import QuadraticFormulaRule
from .power_rule import PowerRule
from .product_rule import ProductRule
from .quotient_rule import QuotientRule
from .rule_engine import RuleEngine
from .rule_exceptions import (
    RuleEngineError,
    RuleError,
    RuleNotApplicableError,
    UnsupportedExpressionError,
)
from .simplify_quadratic_roots_rule import SimplifyQuadraticRootsRule
from .sum_rule import SumRule

__all__ = [
    "BaseRule",
    "linear_components",
    "make_step",
    "ClassifyQuadraticRootsRule",
    "ComputeDiscriminantRule",
    "ConstantDerivativeRule",
    "DivideCoefficientRule",
    "ExpandRule",
    "ExtractDerivativeStructureRule",
    "ExtractQuadraticCoefficientsRule",
    "MoveConstantRule",
    "MoveVariableRule",
    "MultiplyBothSidesRule",
    "NormalizeQuadraticRule",
    "QuadraticFormulaRule",
    "PowerRule",
    "ProductRule",
    "QuotientRule",
    "RuleEngine",
    "RuleEngineError",
    "RuleError",
    "RuleNotApplicableError",
    "UnsupportedExpressionError",
    "SimplifyQuadraticRootsRule",
    "SumRule",
]