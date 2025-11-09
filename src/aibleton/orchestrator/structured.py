from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .schema import (
    ActionPlan,
    CreateMidiClipAction,
    LaunchClipAction,
    OrchestrationError,
    SetDeviceParameterAction,
    SetTempoAction,
    SetTrackVolumeAction,
)


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
            validated_payload = self._validate_payload(payload)
            return ActionPlan.from_dict(validated_payload)
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

    def _validate_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if "actions" not in data:
            raise OrchestrationError("Structured plan missing 'actions'.")

        validated_actions: List[Dict[str, Any]] = []
        for raw in data["actions"]:
            if not isinstance(raw, dict):
                raise OrchestrationError("Action entries must be objects.")
            action_type = raw.get("type")
            if not action_type:
                raise OrchestrationError("Action missing 'type'.")
            validator = self._action_validators().get(action_type)
            if not validator:
                raise OrchestrationError(f"Unsupported action type '{action_type}'.")
            validated_actions.append(validator(raw))

        data["actions"] = validated_actions
        return data

    def _action_validators(self):
        return {
            SetTempoAction.action_type: self._validate_set_tempo,
            SetTrackVolumeAction.action_type: self._validate_set_track_volume,
            CreateMidiClipAction.action_type: self._validate_create_midi_clip,
            LaunchClipAction.action_type: self._validate_launch_clip,
            SetDeviceParameterAction.action_type: self._validate_set_device_parameter,
        }

    def _validate_set_tempo(self, action: Dict[str, Any]) -> Dict[str, Any]:
        tempo = action.get("tempo_bpm")
        if tempo is None:
            raise OrchestrationError("set_tempo requires 'tempo_bpm'.")
        if not (20 <= float(tempo) <= 300):
            raise OrchestrationError("tempo_bpm must be between 20 and 300.")
        action["tempo_bpm"] = float(tempo)
        return action

    def _validate_set_track_volume(self, action: Dict[str, Any]) -> Dict[str, Any]:
        if "track_name" not in action:
            raise OrchestrationError("set_track_volume requires 'track_name'.")
        if "volume_db" not in action:
            raise OrchestrationError("set_track_volume requires 'volume_db'.")
        action["volume_db"] = float(action["volume_db"])
        return action

    def _validate_create_midi_clip(self, action: Dict[str, Any]) -> Dict[str, Any]:
        required = ["track_name", "clip_name", "length_bars"]
        for key in required:
            if key not in action:
                raise OrchestrationError(f"create_midi_clip requires '{key}'.")
        length = int(action["length_bars"])
        if length <= 0:
            raise OrchestrationError("length_bars must be > 0.")
        action["length_bars"] = length
        notes = action.get("notes")
        if notes is not None:
            if not isinstance(notes, list):
                raise OrchestrationError("'notes' must be a list.")
            action["notes"] = [self._validate_note_tuple(entry) for entry in notes]
        return action

    def _validate_launch_clip(self, action: Dict[str, Any]) -> Dict[str, Any]:
        if "track_name" not in action or "clip_name" not in action:
            raise OrchestrationError("launch_clip requires 'track_name' and 'clip_name'.")
        return action

    def _validate_set_device_parameter(self, action: Dict[str, Any]) -> Dict[str, Any]:
        required = ["track_name", "device_name", "parameter_name", "value"]
        for key in required:
            if key not in action:
                raise OrchestrationError(f"set_device_parameter requires '{key}'.")
        action["value"] = float(action["value"])
        return action

    def _validate_note_tuple(self, entry: List[Any]) -> List[float]:
        if len(entry) != 5:
            raise OrchestrationError(
                "Notes must be [pitch, start_beat, duration_beats, velocity, mute]."
            )
        pitch, start, duration, velocity, mute = entry
        pitch = int(pitch)
        if not (0 <= pitch <= 127):
            raise OrchestrationError("Note pitch must be 0–127.")
        start = float(start)
        duration = float(duration)
        if duration <= 0:
            raise OrchestrationError("Note duration must be > 0.")
        velocity = int(velocity)
        if not (0 <= velocity <= 127):
            raise OrchestrationError("Velocity must be 0–127.")
        mute = int(mute)
        if mute not in (0, 1):
            raise OrchestrationError("Mute must be 0 or 1.")
        return [pitch, start, duration, velocity, mute]
