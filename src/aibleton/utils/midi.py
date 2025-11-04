from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List


@dataclass(frozen=True)
class MidiNote:
    pitch: int
    start_beat: float
    duration_beats: float
    velocity: int = 100
    mute: bool = False

    def as_tuple(self) -> tuple:
        return (
            self.pitch,
            self.start_beat,
            self.duration_beats,
            self.velocity,
            int(self.mute),
        )


def generate_notes(generator: Callable[[int], Iterable[MidiNote]], bars: int) -> List[MidiNote]:
    notes: List[MidiNote] = []
    for bar in range(bars):
        bar_start = bar * 4.0
        for note in generator(bar):
            notes.append(
                MidiNote(
                    pitch=note.pitch,
                    start_beat=bar_start + note.start_beat,
                    duration_beats=note.duration_beats,
                    velocity=note.velocity,
                    mute=note.mute,
                )
            )
    return notes


def basic_drum_pattern(_: int) -> Iterable[MidiNote]:
    return (
        MidiNote(pitch=36, start_beat=0.0, duration_beats=0.5, velocity=110),
        MidiNote(pitch=38, start_beat=1.0, duration_beats=0.5, velocity=100),
        MidiNote(pitch=42, start_beat=0.5, duration_beats=0.25, velocity=90),
        MidiNote(pitch=42, start_beat=1.5, duration_beats=0.25, velocity=90),
        MidiNote(pitch=42, start_beat=2.5, duration_beats=0.25, velocity=90),
        MidiNote(pitch=42, start_beat=3.5, duration_beats=0.25, velocity=90),
    )


def simple_bassline(_: int) -> Iterable[MidiNote]:
    return (
        MidiNote(pitch=36, start_beat=0.0, duration_beats=1.0, velocity=100),
        MidiNote(pitch=36, start_beat=1.0, duration_beats=1.0, velocity=100),
        MidiNote(pitch=38, start_beat=2.0, duration_beats=1.0, velocity=100),
        MidiNote(pitch=38, start_beat=3.0, duration_beats=1.0, velocity=100),
    )
