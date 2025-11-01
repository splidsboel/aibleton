from __future__ import annotations

from dataclasses import dataclass

from .rule_based import RuleBasedOrchestrator
from .schema import ActionPlan, OrchestrationError
from .structured import StructuredPlanParser


@dataclass
class HybridOrchestrator:
    """Tries structured parsing first, then falls back to rule-based heuristics."""

    structured_parser: StructuredPlanParser
    fallback: RuleBasedOrchestrator

    def plan(self, command: str) -> ActionPlan:
        try:
            structured_plan = self.structured_parser.parse(command)
        except OrchestrationError:
            # Propagate structured errors directly; they already explain the issue.
            raise

        if structured_plan:
            return structured_plan
        return self.fallback.plan(command)
