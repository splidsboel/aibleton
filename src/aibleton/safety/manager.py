from __future__ import annotations

from typing import List, Optional

from ..orchestrator.schema import (
    ActionPlan,
    BaseAction,
    CreateMidiClipAction,
    SetTrackVolumeAction,
)


class SafetyManager:
    """Very small heuristic safety layer for the MVP."""

    def requires_confirmation(self, plan: ActionPlan) -> bool:
        return any(self._action_requires_confirmation(action) for action in plan.actions)

    def explanation(self, plan: ActionPlan) -> Optional[str]:
        flagged: List[str] = []
        for action in plan.actions:
            reason = self._explain_action(action)
            if reason:
                flagged.append(reason)
        if not flagged:
            return None
        return "; ".join(flagged)

    def _action_requires_confirmation(self, action: BaseAction) -> bool:
        if isinstance(action, CreateMidiClipAction):
            return True
        if isinstance(action, SetTrackVolumeAction):
            if action.volume_db <= -12 or action.volume_db >= 6:
                return True
        return False

    def _explain_action(self, action: BaseAction) -> Optional[str]:
        if isinstance(action, CreateMidiClipAction):
            return f"Creating clip '{action.clip_name}' on '{action.track_name}'"
        if isinstance(action, SetTrackVolumeAction):
            if action.volume_db <= -12 or action.volume_db >= 6:
                return f"Setting '{action.track_name}' volume to {action.volume_db} dB"
        return None
