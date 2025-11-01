from __future__ import annotations

import json
import unittest
from pathlib import Path

from aibleton.bridge.logging import LoggingBridge
from aibleton.bridge.osc import AbletonOSCBridge
from aibleton.context.provider import MutableContextProvider
from aibleton.orchestrator.schema import (
    ActionPlan,
    CreateMidiClipAction,
    SetTempoAction,
    SetTrackVolumeAction,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "aibleton"
    / "context"
    / "fixtures"
    / "default_set.json"
)


class BridgeTests(unittest.TestCase):
    def test_logging_bridge_updates_context(self) -> None:
        provider = MutableContextProvider(fixture_path=FIXTURE_PATH)
        bridge = LoggingBridge(context_provider=provider)
        plan = ActionPlan(
            intent="set_tempo",
            summary="",
            actions=[SetTempoAction(tempo_bpm=132)],
        )

        bridge.execute(plan)
        self.assertEqual(provider.snapshot().tempo_bpm, 132)

    def test_logging_bridge_appends_clip(self) -> None:
        provider = MutableContextProvider(fixture_path=FIXTURE_PATH)
        bridge = LoggingBridge(context_provider=provider)
        plan = ActionPlan(
            intent="create_midi_clip",
            summary="",
            actions=[
                CreateMidiClipAction(
                    track_name="Drums",
                    clip_name="New Clip",
                    length_bars=4,
                    pattern="kick-snare",
                )
            ],
        )
        bridge.execute(plan)
        drums = provider.snapshot().find_track("Drums")
        self.assertIsNotNone(drums)
        assert drums  # hint for type-checkers
        self.assertTrue(any(clip.name == "New Clip" for clip in drums.clips))

    def test_osc_bridge_serializes_payload(self) -> None:
        provider = MutableContextProvider(fixture_path=FIXTURE_PATH)
        bridge = AbletonOSCBridge(enable_transport=False, context_provider=provider)
        action = SetTrackVolumeAction(track_name="Drums", volume_db=-6.0)
        payload = bridge._serialize_action(action)  # type: ignore[attr-defined]
        decoded = json.loads(payload)
        self.assertEqual(decoded["address"], "/aibleton/set_track_volume")
        self.assertEqual(decoded["args"]["track_name"], "Drums")


if __name__ == "__main__":
    unittest.main()
