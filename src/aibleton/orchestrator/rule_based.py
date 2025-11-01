from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional

from ..context.provider import ContextProvider
from ..context.state import LiveContext, Track
from .schema import (
    ActionPlan,
    CreateMidiClipAction,
    LaunchClipAction,
    OrchestrationError,
    SetDeviceParameterAction,
    SetTempoAction,
    SetTrackVolumeAction,
)


Handler = Callable[[str, LiveContext], Optional[ActionPlan]]


@dataclass
class RuleBasedOrchestrator:
    """Minimal deterministic orchestrator for the MVP."""

    context_provider: ContextProvider

    def plan(self, command: str) -> ActionPlan:
        command = command.strip()
        if not command:
            raise OrchestrationError("Command is empty.")

        context = self.context_provider.snapshot()
        for handler in (
            self._handle_set_tempo,
            self._handle_set_track_volume,
            self._handle_set_device_parameter,
            self._handle_create_midi_clip,
            self._handle_launch_clip,
        ):
            plan = handler(command, context)
            if plan:
                return plan
        raise OrchestrationError("I do not recognise that command yet.")

    def _handle_set_tempo(self, text: str, context: LiveContext) -> Optional[ActionPlan]:
        match = re.search(r"(?:set|change)\s+tempo(?:\s+to)?\s+(?P<tempo>\d{2,3})", text, flags=re.IGNORECASE)
        if not match:
            return None
        tempo = float(match.group("tempo"))
        action = SetTempoAction(tempo_bpm=tempo)
        summary = f"Change tempo from {context.tempo_bpm:.1f} BPM to {tempo:.1f} BPM."
        return ActionPlan(
            intent="set_tempo",
            summary=summary,
            actions=[action],
            confidence=0.85,
        )

    def _handle_set_track_volume(self, text: str, context: LiveContext) -> Optional[ActionPlan]:
        match = re.search(
            r"(?:set|adjust|change)\s+(?P<track>[a-z0-9\s]+?)\s+volume(?:\s+to)?\s+(?P<value>-?\d{1,2})",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            match = re.search(
                r"(?:turn\s+(?P<track2>[a-z0-9\s]+?)\s+(?:track\s+)?(?:down|up)\s+by\s+(?P<delta>\d{1,2}))",
                text,
                flags=re.IGNORECASE,
            )
            if not match:
                return None
            track_name = match.group("track2").strip()
            delta = float(match.group("delta"))
            sign = -1.0 if "down" in match.group(0).lower() else 1.0
            target_volume = self._volume_for_track(context, track_name) + (sign * delta)
        else:
            track_name = match.group("track").strip()
            target_volume = float(match.group("value"))

        track = self._locate_track(context, track_name)
        if not track:
            raise OrchestrationError(f"Track '{track_name}' does not exist.")

        action = SetTrackVolumeAction(track_name=track.name, volume_db=target_volume)
        summary = f"Set volume of '{track.name}' to {target_volume:.1f} dB."
        return ActionPlan(
            intent="set_track_volume",
            summary=summary,
            actions=[action],
            confidence=0.75,
        )

    def _handle_set_device_parameter(self, text: str, context: LiveContext) -> Optional[ActionPlan]:
        match = re.search(
            r"set\s+(?P<track>[a-z0-9\s]+?)\s+(?P<device>[a-z0-9\s]+?)\s+(?P<parameter>[a-z0-9\s\/]+?)\s+to\s+(?P<value>-?\d+(?:\.\d+)?)",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            return None

        track_name = match.group("track").strip()
        device_name = match.group("device").strip()
        parameter_name = match.group("parameter").strip()
        value = float(match.group("value"))

        track = self._locate_track(context, track_name)
        if not track:
            return None

        device = next(
            (d for d in track.devices if d.name.lower() == device_name.lower()),
            None,
        )
        if not device:
            return None

        parameter = device.find_parameter(parameter_name)
        if not parameter:
            return None

        action = SetDeviceParameterAction(
            track_name=track.name,
            device_name=device.name,
            parameter_name=parameter.name,
            value=value,
        )
        summary = (
            f"Set '{device.name}' parameter '{parameter.name}' on '{track.name}' to {value:.2f}."
        )
        return ActionPlan(
            intent="set_device_parameter",
            summary=summary,
            actions=[action],
            confidence=0.65,
        )

    def _handle_create_midi_clip(self, text: str, context: LiveContext) -> Optional[ActionPlan]:
        match = re.search(
            r"(?:create|add)\s+(?P<length>\d{1,2})\s*-?\s*bar\s+(?:midi\s+)?clip\s+(?:named\s+|called\s+)?"
            r"(?P<name>['\"]?[a-z0-9\s]+['\"]?)\s+(?:on|for)\s+(?P<track>[a-z0-9\s]+)",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            return None

        length = int(match.group("length"))
        clip_name = match.group("name").strip(" '\"")
        track_name = match.group("track").strip()

        track = self._locate_track(context, track_name)
        if not track:
            raise OrchestrationError(f"Track '{track_name}' does not exist.")

        pattern = "kick-snare" if "drum" in track.name.lower() else "basic-arpeggio"
        action = CreateMidiClipAction(
            track_name=track.name,
            clip_name=clip_name,
            length_bars=length,
            pattern=pattern,
        )
        summary = f"Create a {length}-bar clip '{clip_name}' on '{track.name}' using pattern '{pattern}'."
        return ActionPlan(
            intent="create_midi_clip",
            summary=summary,
            actions=[action],
            confidence=0.7,
        )

    def _handle_launch_clip(self, text: str, context: LiveContext) -> Optional[ActionPlan]:
        match = re.search(
            r"(?:launch|fire|play)\s+(?P<clip>[a-z0-9\s]+)\s+(?:clip\s+)?(?:on|from)\s+(?P<track>[a-z0-9\s]+)",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            return None

        clip_name = match.group("clip").strip()
        track_name = match.group("track").strip()

        track = self._locate_track(context, track_name)
        if not track:
            raise OrchestrationError(f"Track '{track_name}' does not exist.")
        clip = track.find_clip(clip_name)
        if not clip:
            raise OrchestrationError(f"Track '{track_name}' has no clip named '{clip_name}'.")

        action = LaunchClipAction(track_name=track.name, clip_name=clip.name)
        summary = f"Launch clip '{clip.name}' on '{track.name}'."
        return ActionPlan(
            intent="launch_clip",
            summary=summary,
            actions=[action],
            confidence=0.6,
        )

    def _locate_track(self, context: LiveContext, track_name: str) -> Optional[Track]:
        track = context.find_track(track_name)
        if track:
            return track
        # Fallback: allow numeric referencing "track 1"
        numeric_match = re.match(r"track\s*(?P<index>\d+)", track_name.lower())
        if numeric_match:
            index = int(numeric_match.group("index")) - 1
            if 0 <= index < len(context.tracks):
                return context.tracks[index]
        return None

    def _volume_for_track(self, context: LiveContext, track_name: str) -> float:
        track = self._locate_track(context, track_name)
        if not track:
            raise OrchestrationError(f"Track '{track_name}' does not exist.")
        return track.volume_db
