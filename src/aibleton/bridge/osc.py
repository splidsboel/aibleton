from __future__ import annotations

import json
import logging
import socket
from dataclasses import dataclass, field
from typing import Optional

from ..context.provider import MutableContextProvider
from ..orchestrator.schema import ActionPlan, BaseAction


@dataclass
class AbletonOSCBridge:
    """Sends actions to Ableton Live via a simple OSC-like UDP protocol."""

    host: str = "127.0.0.1"
    port: int = 11000
    enable_transport: bool = False
    context_provider: Optional[MutableContextProvider] = None
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("aibleton.bridge.osc")
    )
    _socket: Optional[socket.socket] = field(init=False, default=None)

    def __post_init__(self) -> None:
        if self.enable_transport:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.logger.debug(
                "OSC transport enabled for %s:%s", self.host, self.port
            )
        else:
            self.logger.debug("OSC transport disabled; operating in dry-run mode.")

    def execute(self, plan: ActionPlan) -> None:
        self.logger.debug("Dispatching plan: %s", plan.dump())
        for action in plan.actions:
            payload = self._serialize_action(action)
            self.logger.info("Sending action: %s", payload)
            if self._socket:
                try:
                    self._socket.sendto(payload.encode("utf-8"), (self.host, self.port))
                except OSError as exc:
                    self.logger.error("Failed to send OSC payload: %s", exc)
            if self.context_provider:
                self.context_provider.apply_action(action)

    def _serialize_action(self, action: BaseAction) -> str:
        """Map an action to a wire payload."""
        data = action.dump()
        address = f"/aibleton/{data.pop('type')}"
        return json.dumps({"address": address, "args": data})
