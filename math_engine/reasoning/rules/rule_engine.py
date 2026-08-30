"""Iterative execution engine for the mathematical rule layer.

:class:`RuleEngine` owns the execution loop that drives a set of rules. It
maintains an ordered registry whose order defines the reasoning order: rules
are tried in registration order, the first rule that can apply is executed, and
iteration restarts from the first rule. Execution stops when no registered rule
can apply to the current expression.

The engine is deliberately free of any mathematical logic; it only decides how
to sequence the transformations that the registered rules already provide.
"""

from __future__ import annotations

from ...models import Expression, Step
from .base_rule import BaseRule
from .rule_exceptions import RuleEngineError

# Defensive ceiling that prevents a faulty rule from looping forever.
_MAX_RULE_PASSES = 1000


class RuleEngine:
    """Drives an ordered set of rules over an expression.

    Attributes
    ----------
    final_expression:
        The last expression reached once execution finished, or ``None`` before
        the engine has run.
    """

    def __init__(self, rules: list[BaseRule] | None = None) -> None:
        self._rules: list[BaseRule] = []
        self._final_expression = None
        if rules:
            for rule in rules:
                self.register(rule)

    def register(self, rule: BaseRule) -> RuleEngine:
        """Append a rule to the ordered registry.

        The order of registration is the order in which rules are attempted on
        each pass over the expression.
        """
        if not isinstance(rule, BaseRule):
            raise TypeError(
                f"RuleEngine expects BaseRule instances, got "
                f"{type(rule).__name__}."
            )
        self._rules.append(rule)
        return self

    @property
    def final_expression(self):
        """The expression produced when execution stopped."""
        return self._final_expression

    def run(self, expression: Expression | object) -> tuple[Step, ...]:
        """Iteratively apply rules until no rule can apply any more.

        Each successful application produces the next expression state and a
        reasoning step. Iteration restarts from the first registered rule after
        every application, and stops on the first pass where no rule applies.

        Parameters
        ----------
        expression :
            The initial expression the rules operate on.

        Returns
        -------
        tuple[Step, ...]
            The reasoning steps, one per successful rule application, in the
            order they were applied.

        Raises
        ------
        RuleEngineError
            If the rules keep applying without converging.
        """
        current = expression
        steps: list[Step] = []
        passes = 0

        while True:
            applied_any = False
            for rule in self._rules:
                if rule.can_apply(current):
                    current, step = rule.apply(current)
                    steps.append(step)
                    passes += 1
                    if passes > _MAX_RULE_PASSES:
                        raise RuleEngineError(
                            "RuleEngine did not converge after "
                            f"{_MAX_RULE_PASSES} applications; aborting to "
                            "prevent an infinite loop."
                        )
                    applied_any = True
                    break
            if not applied_any:
                break

        self._final_expression = current
        return tuple(steps)