from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .state import Clip, LiveContext, Track
from ..orchestrator.schema import (
    ActionPlan,
    BaseAction,
    CreateMidiClipAction,
    LaunchClipAction,
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
        tracks: list[Track] = [
            Track(
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
            for item in data.get("tracks", [])
        ]
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

    fixture_path: Path
    _context: LiveContext = field(init=False)

    def __post_init__(self) -> None:
        loader = InMemoryContextProvider(fixture_path=self.fixture_path)
        self._context = loader.snapshot()

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
