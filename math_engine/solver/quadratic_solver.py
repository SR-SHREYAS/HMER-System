"""Concrete solver for quadratic equations.

:class:`QuadraticSolver` solves quadratic equations in two stages. It first
applies the :class:`NormalizeQuadraticRule` to rearrange the equation into the
standard quadratic form ``ax**2 + bx + c = 0``, then applies the
:class:`ExtractQuadraticCoefficientsRule` to read the coefficients ``a``,
``b`` and ``c`` off the normalized form, then applies the
:class:`ComputeDiscriminantRule` to calculate ``Delta = b**2 - 4*a*c``, applies
the :class:`ClassifyQuadraticRootsRule` to determine how many real roots the
equation has, applies the :class:`QuadraticFormulaRule` to compute the raw
symbolic roots with the quadratic formula, and simplifies them with the
:class:`SimplifyQuadraticRootsRule`. The solver then assembles the final answer
-- ``x1``/``x2`` for two distinct or complex roots, ``x`` for a repeated root --
from the simplified roots in the solution metadata. No additional mathematics
is performed after simplification. The solver registers against the
process-wide factory under the :class:`TaskType.QUADRATIC_EQUATION` task.

The solution carries five educational steps: standard form, coefficients,
discriminant (formula, substitution, result), root classification (all three
discriminant cases plus the applicable one) and the quadratic formula
(formula, substitution, evaluation, simplified roots). The root
simplification is presented as part of the formula step rather than as a
separate step.
"""

from __future__ import annotations

from dataclasses import replace

from sympy import Basic, latex

from ..models import Expression, Solution, Step, TaskType
from ..reasoning.rules import (
    ClassifyQuadraticRootsRule,
    ComputeDiscriminantRule,
    ExtractQuadraticCoefficientsRule,
    NormalizeQuadraticRule,
    QuadraticFormulaRule,
    SimplifyQuadraticRootsRule,
)
from .base_solver import BaseSolver
from .solver_factory import default_factory


@default_factory.register
class QuadraticSolver(BaseSolver):
    """Solver for quadratic equations.

    Given a classified ``QUADRATIC_EQUATION`` expression, runs the full
    rule-based pipeline -- normalizing the equation, extracting the
    coefficients, computing the discriminant, classifying the roots, applying
    the quadratic formula and simplifying the roots -- and assembles the final
    :class:`Solution`. The reasoning steps produced by each rule are preserved
    in order, and the final answer is built from the simplified roots. The
    intermediate values and the simplified roots are stored in the solution
    metadata.
    """

    task_type = TaskType.QUADRATIC_EQUATION

    def solve(self, problem: Expression) -> Solution:
        """Run the full quadratic pipeline and build the final solution.

        Parameters
        ----------
        problem :
            The classified quadratic equation expression to solve.

        Returns
        -------
        Solution
            The complete solution: the ordered reasoning steps from every rule,
            a ``final_answer`` built from the simplified roots, and metadata
            carrying all the intermediate values and the simplified roots.

        Raises
        ------
        SolverError
            If the equation cannot be reduced to a polynomial in one variable.
        """
        expr = self._extract_expression(problem)
        normalized, normalize_step = NormalizeQuadraticRule().apply(expr)
        _, extract_step = ExtractQuadraticCoefficientsRule().apply(normalized)
        coefficients = extract_step.metadata["coefficients"]
        variable = extract_step.metadata["variable"]
        _, discriminant_step = ComputeDiscriminantRule().apply(coefficients)
        discriminant = discriminant_step.metadata["discriminant"]
        _, classify_step = ClassifyQuadraticRootsRule().apply(discriminant)

        a, b, _ = coefficients
        formula_values = {"a": a, "b": b, "discriminant": discriminant}
        _, formula_step = QuadraticFormulaRule().apply(formula_values)
        simplified_roots, simplify_step = SimplifyQuadraticRootsRule().apply(
            formula_step.metadata["roots"]
        )
        classification = classify_step.metadata["classification"]

        steps = (
            normalize_step,
            extract_step,
            discriminant_step,
            classify_step,
            self._merge_formula_step(
                formula_step,
                simplify_step,
                variable,
                simplified_roots,
                classification,
            ),
        )
        metadata = {
            "normalized": normalized,
            "coefficients": coefficients,
            "variable": variable,
            "discriminant": discriminant,
            "classification": classification,
            "root_count": classify_step.metadata["root_count"],
            "roots": formula_step.metadata["roots"],
            "simplified_roots": simplified_roots,
        }
        return Solution(
            expression=problem,
            steps=steps,
            final_answer=self._render_answer(
                variable, simplified_roots, classification
            ),
            metadata=metadata,
        )

    @staticmethod
    def _merge_formula_step(
        formula_step: Step,
        simplify_step: Step,
        variable,
        simplified_roots,
        classification,
    ) -> Step:
        """Fold the simplified roots into the quadratic-formula step.

        The formula rule already renders the general formula, the substituted
        values and the evaluated expression; this only appends the resulting
        simplified roots as the final line of the same step so the learner can
        follow formula -> substitution -> simplification -> roots in one place.

        Parameters
        ----------
        formula_step :
            The step produced by :class:`QuadraticFormulaRule`.
        simplify_step :
            The step produced by :class:`SimplifyQuadraticRootsRule`, consumed
            for its simplified-roots metadata only.
        variable :
            The unknown symbol of the equation.
        simplified_roots :
            The simplified ``(root_1, root_2)`` symbolic roots.
        classification :
            The root classification produced earlier.

        Returns
        -------
        Step
            A copy of the formula step whose rendered math ends with the
            individual simplified roots and whose metadata carries the
            simplified roots.
        """
        roots_line = QuadraticSolver._roots_latex(
            variable, simplified_roots, classification
        )
        rendered = formula_step.latex
        closing = "\\end{aligned}"
        if rendered.endswith("\n" + closing):
            rendered = (
                rendered[: -len(closing) - 1]
                + f"\\\\\n{roots_line}\n{closing}"
            )
        elif closing in rendered:
            rendered = rendered.replace(
                closing, f"\\\\\n{roots_line}\n{closing}", 1
            )
        else:
            rendered = f"{rendered} \\;\\; {roots_line}"
        metadata = dict(formula_step.metadata)
        metadata["simplified_roots"] = simplify_step.metadata["roots"]
        return replace(formula_step, latex=rendered, metadata=metadata)

    @staticmethod
    def _roots_latex(variable, roots, classification) -> str:
        """Render the simplified roots as the closing line of the formula step.

        Two distinct or complex roots are listed as ``x_1`` and ``x_2``; a
        repeated root is listed once as ``x``. Presentation only -- the final
        answer is rendered separately by :meth:`_render_answer`.
        """
        if classification == "one_repeated_real":
            return f"{latex(variable)} = {latex(roots[0])}"
        return (
            f"{latex(variable)}_{{1}} = {latex(roots[0])}, \\quad "
            f"{latex(variable)}_{{2}} = {latex(roots[1])}"
        )

    def _extract_expression(self, problem: Expression) -> Basic:
        """Return the SymPy expression from the model."""
        return problem.sympy_expression

    @staticmethod
    def _render_answer(variable, roots, classification) -> str:
        """Build the final answer from the simplified roots.

        Two distinct or two complex roots are presented as ``x1 = ...`` and
        ``x2 = ...``; a repeated root is presented once as ``x = ...``. Symbolic
        SymPy expressions are preserved exactly (no decimal conversion).

        Parameters
        ----------
        variable :
            The unknown symbol of the equation.
        roots :
            The simplified ``(root_1, root_2)`` symbolic roots.
        classification :
            The root classification produced earlier.

        Returns
        -------
        str
            The formatted final answer.
        """
        if classification == "one_repeated_real":
            return f"{latex(variable)} = {latex(roots[0])}"
        return (
            f"{latex(variable)}_1 = {latex(roots[0])}, "
            f"{latex(variable)}_2 = {latex(roots[1])}"
        )


__all__ = ["QuadraticSolver"]