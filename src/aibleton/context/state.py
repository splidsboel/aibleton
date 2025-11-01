from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional


@dataclass
class Clip:
    """Minimal representation of a Live clip for context grounding."""

    name: str
    scene_index: int
    slot_index: int
    is_midi: bool = True


@dataclass
class Track:
    """Track metadata used for MVP planning."""

    name: str
    track_index: int
    volume_db: float = 0.0
    clips: List[Clip] = field(default_factory=list)
    devices: List["Device"] = field(default_factory=list)

    def find_clip(self, name: str) -> Optional[Clip]:
        lname = name.strip().lower()
        for clip in self.clips:
            if clip.name.lower() == lname:
                return clip
        return None


@dataclass
class LiveContext:
    """Snapshot of the Live set used during planning."""

    tempo_bpm: float
    tracks: List[Track] = field(default_factory=list)
    scene_count: int = 0

    def find_track(self, name: str) -> Optional[Track]:
        lname = name.strip().lower()
        for track in self.tracks:
            if track.name.lower() == lname:
                return track
        return None

    def list_track_names(self) -> Iterable[str]:
        for track in self.tracks:
            yield track.name

    def max_clip_slot_index(self) -> int:
        max_index = -1
        for track in self.tracks:
            for clip in track.clips:
                max_index = max(max_index, clip.slot_index)
        return max_index

    def ensure_scene_count(self, minimum: int) -> None:
        if minimum > self.scene_count:
            self.scene_count = minimum


@dataclass
class DeviceParameter:
    """Represents a device parameter (e.g., Dry/Wet)."""

    name: str
    parameter_index: int
    min_value: float
    max_value: float
    value: float


@dataclass
class Device:
    """Device metadata associated with a track."""

    name: str
    device_index: int
    parameters: List[DeviceParameter] = field(default_factory=list)

    def find_parameter(self, name: str) -> Optional[DeviceParameter]:
        lname = name.strip().lower()
        for parameter in self.parameters:
            if parameter.name.lower() == lname:
                return parameter
        return None
