from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from aibleton.bridge.config import OSCBridgeConfig
from aibleton.context.live_provider import AbletonOSCContextProvider


OSCKey = Tuple[str, Tuple[int, ...]]


@dataclass
class FakeOSCClient:
    responses: Dict[OSCKey, Tuple]

    def query(self, address: str, *args: int) -> Tuple:
        key = (address, tuple(int(arg) for arg in args))
        if key not in self.responses:
            raise AssertionError(f"Unexpected OSC query: {key}")
        return self.responses[key]

    def close(self) -> None:  # pragma: no cover - not used in tests
        return


def build_provider(responses: Dict[OSCKey, Tuple]) -> AbletonOSCContextProvider:
    config = OSCBridgeConfig(send=False)
    client = FakeOSCClient(responses)
    return AbletonOSCContextProvider(config=config, _client=client)


def test_snapshot_collects_tracks_devices_and_clips() -> None:
    responses: Dict[OSCKey, Tuple] = {
        ("/live/song/get/tempo", ()): (120.0,),
        ("/live/song/get/num_tracks", ()): (2,),
        ("/live/song/get/num_scenes", ()): (2,),
        ("/live/track/get/name", (0,)): (0, "Drums"),
        ("/live/track/get/volume", (0,)): (0, 0.5),
        ("/live/clip_slot/get/has_clip", (0, 0)): (0, 0, 1),
        ("/live/clip/get/name", (0, 0)): (0, 0, "Intro"),
        ("/live/clip/get/is_midi_clip", (0, 0)): (0, 0, 1),
        ("/live/clip_slot/get/has_clip", (0, 1)): (0, 1, 0),
        ("/live/track/get/num_devices", (0,)): (0, 1),
        ("/live/track/get/devices/name", (0,)): (0, "Saturator"),
        ("/live/device/get/parameters/name", (0, 0)): (0, 0, "Drive", "Dry/Wet"),
        ("/live/device/get/parameters/value", (0, 0)): (0, 0, 0.5, 0.25),
        ("/live/device/get/parameters/min", (0, 0)): (0, 0, 0.0, 0.0),
        ("/live/device/get/parameters/max", (0, 0)): (0, 0, 36.0, 1.0),
        ("/live/track/get/name", (1,)): (1, "Bass"),
        ("/live/track/get/volume", (1,)): (1, 0.25),
        ("/live/clip_slot/get/has_clip", (1, 0)): (1, 0, 0),
        ("/live/clip_slot/get/has_clip", (1, 1)): (1, 1, 0),
        ("/live/track/get/num_devices", (1,)): (1, 0),
        ("/live/track/get/devices/name", (1,)): (1,),
    }

    provider = build_provider(responses)
    context = provider.snapshot()

    assert context.tempo_bpm == 120.0
    assert context.scene_count == 2
    assert len(context.tracks) == 2

    drums = context.tracks[0]
    assert drums.name == "Drums"
    assert drums.clips[0].name == "Intro"
    assert drums.devices[0].name == "Saturator"
    assert drums.devices[0].parameters[0].name == "Drive"

    bass = context.tracks[1]
    assert bass.name == "Bass"
    assert len(bass.devices) == 0
