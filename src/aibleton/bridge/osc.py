from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence, Tuple

from ..context.provider import MutableContextProvider
from ..context.state import Clip, LiveContext, Track
from ..orchestrator.schema import (
    ActionPlan,
    BaseAction,
    CreateMidiClipAction,
    LaunchClipAction,
    SetTempoAction,
    SetTrackVolumeAction,
)
from .config import OSCBridgeConfig
from .logging import BridgeError
from .osc_transport import (
    OSCMessage,
    OSCTransport,
    RecordingOSCTransport,
    UDPOSCTransport,
)


def db_to_linear(volume_db: float) -> float:
    """Convert a dB value to linear gain, clamped to a reasonable range."""
    gain = 10 ** (volume_db / 20.0)
    return max(0.0, min(gain, 2.0))


@dataclass
class AbletonOSCBridge:
    """Bridge that translates actions into AbletonOSC-compatible messages."""

    config: OSCBridgeConfig = field(default_factory=OSCBridgeConfig)
    context_provider: Optional[MutableContextProvider] = None
    transport: Optional[OSCTransport] = None
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("aibleton.bridge.osc")
    )
    dry_run_recorder: Optional[RecordingOSCTransport] = field(init=False, default=None)

    def __post_init__(self) -> None:
        if self.transport is None:
            if self.config.send:
                self.transport = UDPOSCTransport(
                    host=self.config.host,
                    port=self.config.port,
                    timeout=self.config.timeout,
                )
                self.logger.debug(
                    "OSC transport enabled for %s:%s",
                    self.config.host,
                    self.config.port,
                )
            else:
                self.dry_run_recorder = RecordingOSCTransport()
                self.logger.debug(
                    "OSC dry-run mode: messages will be logged but not sent."
                )

    def execute(self, plan: ActionPlan) -> None:
        self.logger.debug("Dispatching plan: %s", plan.dump())
        context = self.context_provider.snapshot() if self.context_provider else None

        for action in plan.actions:
            messages = tuple(self._messages_for_action(action, context))
            for address, args in messages:
                if self.transport:
                    self.transport.send(address, args)
                else:
                    assert self.dry_run_recorder is not None
                    self.dry_run_recorder.send(address, args)
                self.logger.info("OSC %s %s", address, args)

            if self.context_provider:
                self.context_provider.apply_action(action)
                context = self.context_provider.snapshot()

    def _messages_for_action(
        self, action: BaseAction, context: Optional[LiveContext]
    ) -> Iterable[OSCMessage]:
        if isinstance(action, SetTempoAction):
            yield "/live/song/set/tempo", [float(action.tempo_bpm)]
        elif isinstance(action, SetTrackVolumeAction):
            if not context:
                raise BridgeError("Track volume change requires context.")
            track = self._track_for_action(action.track_name, context)
            gain = db_to_linear(action.volume_db)
            yield "/live/track/set/volume", [int(track.track_index), float(gain)]
        elif isinstance(action, LaunchClipAction):
            if not context:
                raise BridgeError("Launching a clip requires context.")
            track, clip = self._clip_for_action(
                action.track_name, action.clip_name, context
            )
            yield "/live/clip/fire", [int(track.track_index), int(clip.slot_index)]
        elif isinstance(action, CreateMidiClipAction):
            if not context:
                raise BridgeError("Creating a clip requires context.")
            track = self._track_for_action(action.track_name, context)
            slot_index = self._next_empty_slot(track)
            length_beats = action.length_bars * 4
            yield "/live/clip/create", [
                int(track.track_index),
                int(slot_index),
                float(length_beats),
            ]
        else:
            raise BridgeError(f"Unsupported action type: {action.action_type}")

    def _track_for_action(self, track_name: str, context: LiveContext) -> Track:
        track = context.find_track(track_name)
        if not track:
            raise BridgeError(f"Track '{track_name}' not found.")
        return track

    def _clip_for_action(
        self, track_name: str, clip_name: str, context: LiveContext
    ) -> Tuple[Track, Clip]:
        track = self._track_for_action(track_name, context)
        clip = track.find_clip(clip_name)
        if not clip:
            raise BridgeError(
                f"Clip '{clip_name}' not found on track '{track.name}'."
            )
        return track, clip

    def _next_empty_slot(self, track: Track) -> int:
        if not track.clips:
            return 0
        used = {clip.slot_index for clip in track.clips}
        slot = 0
        while slot in used:
            slot += 1
        return slot

    def recorded_messages(self) -> Optional[Sequence[OSCMessage]]:
        if not self.dry_run_recorder:
            return None
        return tuple(self.dry_run_recorder.messages)
