from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Protocol

from .state import Clip, Device, DeviceParameter, LiveContext, Track
from ..orchestrator.schema import (
    ActionPlan,
    BaseAction,
    CreateMidiClipAction,
    LaunchClipAction,
    SetDeviceParameterAction,
    SetTempoAction,
    SetTrackVolumeAction,
)


class ContextProvider(Protocol):
    """Protocol for components that expose the current Live set state."""

    def snapshot(self) -> LiveContext:
        ...


@dataclass
class InMemoryContextProvider:
    """Loads context from a JSON fixture on disk."""

    fixture_path: Path

    def snapshot(self) -> LiveContext:
        data = json.loads(self.fixture_path.read_text())
        tracks: list[Track] = []
        for item in data.get("tracks", []):
            track = Track(
                name=item["name"],
                track_index=item["track_index"],
                volume_db=item.get("volume_db", 0.0),
                clips=[
                    Clip(
                        name=clip["name"],
                        scene_index=clip["scene_index"],
                        slot_index=clip["slot_index"],
                        is_midi=clip.get("is_midi", True),
                    )
                    for clip in item.get("clips", [])
                ],
            )
            devices = []
            for device in item.get("devices", []):
                devices.append(
                    Device(
                        name=device["name"],
                        device_index=device["device_index"],
                        parameters=[
                            DeviceParameter(
                                name=param["name"],
                                parameter_index=param["parameter_index"],
                                min_value=float(param.get("min_value", 0.0)),
                                max_value=float(param.get("max_value", 1.0)),
                                value=float(param.get("value", 0.0)),
                            )
                            for param in device.get("parameters", [])
                        ],
                    )
                )
            track.devices = devices
            tracks.append(track)
        max_slot = max(
            (clip.slot_index for track in tracks for clip in track.clips),
            default=-1,
        )
        scene_count = data.get("scene_count")
        if scene_count is None:
            scene_count = max_slot + 1 if max_slot >= 0 else 0
        return LiveContext(
            tempo_bpm=data.get("tempo_bpm", 120.0),
            tracks=tracks,
            scene_count=scene_count,
        )


@dataclass
class MutableContextProvider(ContextProvider):
    """Mutable in-memory context that evolves as actions execute."""

    fixture_path: Optional[Path] = None
    initial_context: Optional[LiveContext] = None
    _context: LiveContext = field(init=False)

    def __post_init__(self) -> None:
        if self.initial_context is not None:
            self._context = self.initial_context
        elif self.fixture_path is not None:
            loader = InMemoryContextProvider(fixture_path=self.fixture_path)
            self._context = loader.snapshot()
        else:
            raise ValueError("MutableContextProvider requires fixture_path or initial_context")

    def snapshot(self) -> LiveContext:
        return self._context

    def apply_plan(self, plan: ActionPlan) -> None:
        for action in plan.actions:
            self.apply_action(action)

    def apply_action(self, action: BaseAction) -> None:
        if isinstance(action, SetTempoAction):
            self._context.tempo_bpm = action.tempo_bpm
        elif isinstance(action, SetTrackVolumeAction):
            track = self._context.find_track(action.track_name)
            if track:
                track.volume_db = action.volume_db
        elif isinstance(action, CreateMidiClipAction):
            track = self._context.find_track(action.track_name)
            if not track:
                return
            if track.find_clip(action.clip_name):
                return
            next_slot = max((clip.slot_index for clip in track.clips), default=-1) + 1
            track.clips.append(
                Clip(
                    name=action.clip_name,
                    scene_index=0,
                    slot_index=next_slot,
                    is_midi=True,
                )
            )
            if next_slot + 1 > self._context.scene_count:
                self._context.scene_count = next_slot + 1
        elif isinstance(action, LaunchClipAction):
            # Launching a clip does not alter context in this MVP.
            return
        elif isinstance(action, SetDeviceParameterAction):
            track = self._context.find_track(action.track_name)
            if not track:
                return
            device = next(
                (d for d in track.devices if d.name.lower() == action.device_name.lower()),
                None,
            )
            if not device:
                return
            parameter = device.find_parameter(action.parameter_name)
            if not parameter:
                return
            clamped = max(parameter.min_value, min(parameter.max_value, action.value))
            parameter.value = clamped
