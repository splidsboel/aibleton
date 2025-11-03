from __future__ import annotations

import math
import socket
import select
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from ..bridge.config import OSCBridgeConfig
from ..bridge.osc_transport import (
    OSCArg,
    decode_osc_packet,
    encode_osc_message,
)
from .provider import ContextProvider
from .state import Clip, Device, DeviceParameter, LiveContext, Track


class OSCQueryError(RuntimeError):
    """Raised when AbletonOSC does not return the expected response."""


class OSCQueryTimeout(OSCQueryError):
    """Raised when AbletonOSC fails to respond within the timeout."""


class AbletonOSCClient:
    """Thin synchronous client for AbletonOSC queries."""

    def __init__(
        self,
        host: str,
        send_port: int = 11000,
        listen_port: int | None = None,
        timeout: float = 1.0,
    ) -> None:
        self._host = host
        self._port = send_port
        self._timeout = timeout
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.settimeout(timeout)
        if listen_port and listen_port > 0:
            try:
                self._socket.bind(("0.0.0.0", listen_port))
            except OSError:
                pass

    def close(self) -> None:
        self._socket.close()

    def query(self, address: str, *args: OSCArg) -> Tuple[OSCArg, ...]:
        payload = encode_osc_message(address, args)
        try:
            self._socket.sendto(payload, (self._host, self._port))
        except OSError as exc:
            raise OSCQueryError(
                f"Unable to send OSC message to {self._host}:{self._port}: {exc}"
            ) from exc

        deadline = time.time() + self._timeout
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise OSCQueryTimeout(f"Timeout waiting for response to {address}")

            ready, _, _ = select.select([self._socket], [], [], remaining)
            if not ready:
                continue

            data, _ = self._socket.recvfrom(65536)
            messages = decode_osc_packet(data)
            for msg_address, msg_args in messages:
                if msg_address == address:
                    return msg_args
        # Unreachable, but keeps type-checkers happy.
        raise OSCQueryTimeout(f"No response for {address}")


def gain_to_db(value: float) -> float:
    if value <= 0:
        return float("-inf")
    return 20.0 * math.log10(value)


@dataclass
class AbletonOSCContextProvider(ContextProvider):
    """Context provider that queries AbletonOSC for live state."""

    config: OSCBridgeConfig
    _client: Optional[AbletonOSCClient] = None

    def _ensure_client(self) -> AbletonOSCClient:
        if self._client is None:
            self._client = AbletonOSCClient(
                host=self.config.host,
                send_port=self.config.port,
                listen_port=self.config.listen_port,
                timeout=self.config.timeout,
            )
        return self._client

    def snapshot(self) -> LiveContext:
        client = self._ensure_client()

        tempo = float(self._last_value(client.query("/live/song/get/tempo")))
        num_tracks = int(self._last_value(client.query("/live/song/get/num_tracks")))
        num_scenes = int(self._last_value(client.query("/live/song/get/num_scenes")))

        tracks: List[Track] = []
        for track_index in range(num_tracks):
            tracks.append(self._build_track(client, track_index, num_scenes))

        return LiveContext(
            tempo_bpm=tempo,
            tracks=tracks,
            scene_count=num_scenes,
        )

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    # --- internal helpers -------------------------------------------------

    def _build_track(
        self,
        client: AbletonOSCClient,
        track_index: int,
        scene_count: int,
    ) -> Track:
        name_resp = client.query("/live/track/get/name", track_index)
        name = str(self._last_value(name_resp))

        volume_resp = client.query("/live/track/get/volume", track_index)
        volume_linear = float(self._last_value(volume_resp))
        volume_db = gain_to_db(volume_linear)

        clips = self._collect_clips(client, track_index, scene_count)
        devices = self._collect_devices(client, track_index)

        return Track(
            name=name,
            track_index=track_index,
            volume_db=volume_db,
            volume_linear=volume_linear,
            clips=clips,
            devices=devices,
        )

    def _collect_clips(
        self,
        client: AbletonOSCClient,
        track_index: int,
        scene_count: int,
    ) -> List[Clip]:
        clips: List[Clip] = []
        for scene_index in range(scene_count):
            has_clip_resp = client.query(
                "/live/clip_slot/get/has_clip", track_index, scene_index
            )
            has_clip = bool(self._last_value(has_clip_resp))
            if not has_clip:
                continue

            name_resp = client.query("/live/clip/get/name", track_index, scene_index)
            clip_name = str(self._last_value(name_resp))

            is_midi_resp = client.query(
                "/live/clip/get/is_midi_clip", track_index, scene_index
            )
            is_midi = bool(self._last_value(is_midi_resp))

            clips.append(
                Clip(
                    name=clip_name,
                    scene_index=scene_index,
                    slot_index=scene_index,
                    is_midi=is_midi,
                )
            )
        return clips

    def _collect_devices(
        self,
        client: AbletonOSCClient,
        track_index: int,
    ) -> List[Device]:
        devices: List[Device] = []

        num_devices_resp = client.query("/live/track/get/num_devices", track_index)
        num_devices = int(self._last_value(num_devices_resp))

        names_resp = client.query("/live/track/get/devices/name", track_index)
        device_names = self._tail_as_list(names_resp)

        for device_index in range(num_devices):
            device_name = (
                str(device_names[device_index])
                if device_index < len(device_names)
                else f"Device {device_index}"
            )

            parameters = self._collect_device_parameters(client, track_index, device_index)

            devices.append(
                Device(
                    name=device_name,
                    device_index=device_index,
                    parameters=parameters,
                )
            )
        return devices

    def _collect_device_parameters(
        self,
        client: AbletonOSCClient,
        track_index: int,
        device_index: int,
    ) -> List[DeviceParameter]:
        param_names = self._tail_as_list(
            client.query("/live/device/get/parameters/name", track_index, device_index),
            offset=2,
        )
        param_values = self._tail_as_list(
            client.query("/live/device/get/parameters/value", track_index, device_index),
            offset=2,
        )
        param_mins = self._tail_as_list(
            client.query("/live/device/get/parameters/min", track_index, device_index),
            offset=2,
        )
        param_maxs = self._tail_as_list(
            client.query("/live/device/get/parameters/max", track_index, device_index),
            offset=2,
        )

        parameters: List[DeviceParameter] = []
        for idx, name in enumerate(param_names):
            min_value = float(param_mins[idx]) if idx < len(param_mins) else 0.0
            max_value = float(param_maxs[idx]) if idx < len(param_maxs) else 1.0
            value = float(param_values[idx]) if idx < len(param_values) else 0.0
            parameters.append(
                DeviceParameter(
                    name=str(name),
                    parameter_index=idx,
                    min_value=min_value,
                    max_value=max_value,
                    value=value,
                )
            )
        return parameters

    @staticmethod
    def _last_value(response: Tuple[OSCArg, ...]) -> OSCArg:
        if not response:
            raise OSCQueryError("OSC response was empty")
        return response[-1]

    @staticmethod
    def _tail_as_list(response: Tuple[OSCArg, ...], offset: int = 1) -> List[OSCArg]:
        if len(response) <= offset:
            return []
        return list(response[offset:])
