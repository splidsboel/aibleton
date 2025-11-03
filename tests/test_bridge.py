from __future__ import annotations

import unittest
from math import isclose
from pathlib import Path

from aibleton.bridge.config import OSCBridgeConfig
from aibleton.bridge.logging import LoggingBridge
from aibleton.bridge.osc import AbletonOSCBridge, db_to_linear
from aibleton.context.provider import MutableContextProvider
from aibleton.orchestrator.schema import (
    ActionPlan,
    CreateMidiClipAction,
    LaunchClipAction,
    SetDeviceParameterAction,
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

    def test_osc_bridge_records_messages(self) -> None:
        provider = MutableContextProvider(fixture_path=FIXTURE_PATH)
        config = OSCBridgeConfig(send=False)
        bridge = AbletonOSCBridge(config=config, context_provider=provider)

        plan = ActionPlan(
            intent="smoke",
            summary="",
            actions=[
                SetTempoAction(tempo_bpm=125),
                SetTrackVolumeAction(track_name="Drums", volume_db=-6.0),
                LaunchClipAction(track_name="Drums", clip_name="Intro Beat"),
            ],
        )
        bridge.execute(plan)
        messages = bridge.recorded_messages()
        self.assertIsNotNone(messages)
        assert messages is not None
        self.assertEqual(
            messages[0], ("/live/song/set/tempo", (125.0,))
        )
        expected_gain = db_to_linear(-6.0)
        self.assertEqual(messages[1][0], "/live/track/set/volume")
        self.assertEqual(messages[1][1][0], 0)  # Drums track index
        self.assertTrue(isclose(messages[1][1][1], expected_gain, rel_tol=1e-6))
        self.assertEqual(messages[2], ("/live/clip/fire", (0, 0)))

    def test_create_clip_message(self) -> None:
        provider = MutableContextProvider(fixture_path=FIXTURE_PATH)
        config = OSCBridgeConfig(send=False)
        bridge = AbletonOSCBridge(config=config, context_provider=provider)

        plan = ActionPlan(
            intent="create_midi_clip",
            summary="",
            actions=[
                CreateMidiClipAction(
                    track_name="Drums",
                    clip_name="Bridge Clip",
                    length_bars=2,
                    pattern="test",
                )
            ],
        )
        bridge.execute(plan)
        messages = bridge.recorded_messages()
        self.assertIsNotNone(messages)
        assert messages is not None
        self.assertEqual(
            messages[0], ("/live/song/create_scene", (1,))
        )
        self.assertEqual(
            messages[1], ("/live/clip_slot/create_clip", (0, 1, 8.0))
        )


if __name__ == "__main__":
    unittest.main()
