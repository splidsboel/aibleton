from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import ClassVar, Dict, List, Type


@dataclass
class BaseAction:
    """Base class for orchestration actions."""

    action_type: ClassVar[str] = "base"

    def dump(self) -> dict:
        payload = asdict(self)
        payload["type"] = self.action_type
        return payload


@dataclass
class SetTempoAction(BaseAction):
    action_type: ClassVar[str] = "set_tempo"
    tempo_bpm: float


@dataclass
class SetTrackVolumeAction(BaseAction):
    action_type: ClassVar[str] = "set_track_volume"
    track_name: str
    volume_db: float


@dataclass
class CreateMidiClipAction(BaseAction):
    action_type: ClassVar[str] = "create_midi_clip"
    track_name: str
    clip_name: str
    length_bars: int
    pattern: str


@dataclass
class LaunchClipAction(BaseAction):
    action_type: ClassVar[str] = "launch_clip"
    track_name: str
    clip_name: str


@dataclass
class ActionPlan:
    """Container returned by the orchestrator."""

    intent: str
    summary: str
    actions: List[BaseAction]
    confidence: float = 0.0
    requires_confirmation: bool = False

    def dump(self) -> dict:
        return {
            "intent": self.intent,
            "summary": self.summary,
            "confidence": self.confidence,
            "requires_confirmation": self.requires_confirmation,
            "actions": [action.dump() for action in self.actions],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ActionPlan":
        if "actions" not in data:
            raise OrchestrationError("Structured plan missing 'actions' field.")
        actions = [action_from_dict(item) for item in data["actions"]]
        return cls(
            intent=data.get("intent", "unknown"),
            summary=data.get("summary", ""),
            actions=actions,
            confidence=float(data.get("confidence", 0.0)),
            requires_confirmation=bool(data.get("requires_confirmation", False)),
        )


@dataclass
class OrchestrationError(Exception):
    """Lightweight error for unsupported requests."""

    message: str

    def __str__(self) -> str:
        return self.message


ActionRegistry = Dict[str, Type[BaseAction]]

ACTION_REGISTRY: ActionRegistry = {
    SetTempoAction.action_type: SetTempoAction,
    SetTrackVolumeAction.action_type: SetTrackVolumeAction,
    CreateMidiClipAction.action_type: CreateMidiClipAction,
    LaunchClipAction.action_type: LaunchClipAction,
}


def action_from_dict(data: Dict) -> BaseAction:
    if "type" not in data:
        raise OrchestrationError("Structured action missing 'type' field.")
    action_type = data["type"]
    action_cls = ACTION_REGISTRY.get(action_type)
    if not action_cls:
        raise OrchestrationError(f"Unsupported action type '{action_type}'.")
    payload = {k: v for k, v in data.items() if k != "type"}
    try:
        return action_cls(**payload)
    except TypeError as exc:
        raise OrchestrationError(f"Invalid parameters for action '{action_type}': {exc}") from exc
