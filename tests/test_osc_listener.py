from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from aibleton.bridge.osc_listener import AbletonOSCSubscriptionManager, OSCListener
from aibleton.bridge.osc_transport import encode_osc_message


def test_osc_listener_dispatch() -> None:
    listener = OSCListener(auto_start=False, bind_socket=False)
    events: List[Tuple] = []
    listener.register("/foo/bar", lambda args: events.append(args))
    payload = encode_osc_message("/foo/bar", [1, "hello"])
    listener.feed(payload)

    assert events == [(1, "hello")]


def test_subscription_manager_records_start_and_stop_commands() -> None:
    class FakeListener:
        def __init__(self) -> None:
            self.sent: List[Tuple[str, Tuple]] = []
            self.registry: dict[str, List] = {}

        def register(self, address: str, handler) -> None:
            self.registry.setdefault(address, []).append(handler)

        def unregister(self, address: str, handler) -> None:
            handlers = self.registry.get(address, [])
            if handler in handlers:
                handlers.remove(handler)

        def send(self, host: str, port: int, address: str, *args) -> None:
            self.sent.append((address, args))

    listener = FakeListener()
    manager = AbletonOSCSubscriptionManager(listener, "127.0.0.1", 11000)

    captured: List[Tuple] = []

    manager.subscribe_song_property("tempo", lambda args: captured.append(args))
    manager.subscribe_track_property(0, "volume", lambda args: captured.append(args))

    tempo_handler = listener.registry["/live/song/get/tempo"][0]
    volume_handler = listener.registry["/live/track/get/volume"][0]

    tempo_handler((120.0,))
    volume_handler((0, 0.5))

    assert captured == [(120.0,), (0, 0.5)]

    manager.close()

    assert ("/live/song/start_listen/tempo", ()) in listener.sent
    assert ("/live/track/start_listen/volume", (0,)) in listener.sent
    assert ("/live/song/stop_listen/tempo", ()) in listener.sent
    assert ("/live/track/stop_listen/volume", (0,)) in listener.sent
