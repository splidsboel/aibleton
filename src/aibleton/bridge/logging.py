from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

from ..context.provider import MutableContextProvider
from ..orchestrator.schema import ActionPlan, BaseAction


class BridgeError(Exception):
    """Raised when an action cannot be executed."""


@dataclass
class LoggingBridge:
    """Bridge that logs actions instead of touching Ableton Live."""

    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("aibleton.bridge")
    )
    executed_actions: List[BaseAction] = field(default_factory=list)
    context_provider: MutableContextProvider | None = None

    def execute(self, plan: ActionPlan) -> None:
        self.logger.debug("Executing plan: %s", plan.dump())
        for action in plan.actions:
            self.logger.info("Executing action: %s", action.dump())
            self.executed_actions.append(action)
        if self.context_provider:
            self.context_provider.apply_plan(plan)
