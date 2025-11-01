from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .schema import ActionPlan, OrchestrationError


@dataclass
class StructuredPlanParser:
    """Parses JSON action plans (LLM-style) into ActionPlan instances."""

    def parse(self, command: str) -> Optional["ActionPlan"]:
        command = command.strip()
        if not command:
            return None
        try:
            payload = self._extract_payload(command)
        except ValueError:
            return None

        try:
            return ActionPlan.from_dict(payload)
        except OrchestrationError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise OrchestrationError(f"Invalid structured command: {exc}") from exc

    def _extract_payload(self, text: str) -> Dict[str, Any]:
        if text[0] == "{":
            return json.loads(text)

        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start == -1 or brace_end == -1 or brace_end <= brace_start:
            raise ValueError("No JSON object found")
        snippet = text[brace_start : brace_end + 1]
        return json.loads(snippet)
