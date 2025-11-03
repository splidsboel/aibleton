from __future__ import annotations

import select
import socket
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple

from .osc_transport import OSCArg, decode_osc_packet, encode_osc_message


Handler = Callable[[Tuple[OSCArg, ...]], None]


@dataclass
class OSCListener:
    """Receives OSC datagrams and dispatches them to registered handlers."""

    host: str = "0.0.0.0"
    port: int = 0
    auto_start: bool = True
    bind_socket: bool = True
    _socket: socket.socket | None = field(init=False, default=None)
    _thread: threading.Thread | None = field(init=False, default=None)
    _stop_event: threading.Event = field(init=False, default_factory=threading.Event)
    _handlers: Dict[str, List[Handler]] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        if self.bind_socket:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(False)
            try:
                sock.bind((self.host, self.port))
            except OSError as exc:  # pragma: no cover - depends on environment
                sock.close()
                raise
            self._socket = sock
            self.port = sock.getsockname()[1]
        if self.auto_start and self._socket is not None:
            self.start()

    def start(self) -> None:
        if self._thread is not None or not self._socket:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._socket:
            self._socket.close()
            self._socket = None

    def register(self, address: str, handler: Handler) -> None:
        self._handlers.setdefault(address, []).append(handler)

    def unregister(self, address: str, handler: Handler) -> None:
        handlers = self._handlers.get(address)
        if not handlers:
            return
        try:
            handlers.remove(handler)
        except ValueError:
            pass
        if not handlers:
            self._handlers.pop(address, None)

    def send(
        self, host: str, port: int, address: str, *args: OSCArg
    ) -> None:  # pragma: no cover - network
        if not self._socket:  # pragma: no cover - used in tests with fake listener
            raise RuntimeError("OSCListener socket is not bound")
        payload = encode_osc_message(address, args)
        self._socket.sendto(payload, (host, port))

    def feed(self, data: bytes) -> None:
        for address, args in decode_osc_packet(data):
            self._dispatch(address, args)

    def _run(self) -> None:  # pragma: no cover - requires network
        if not self._socket:
            return
        while not self._stop_event.is_set():
            ready, _, _ = select.select([self._socket], [], [], 0.25)
            if not ready:
                continue
            try:
                data, _ = self._socket.recvfrom(65536)
            except OSError:
                continue
            self.feed(data)

    def _dispatch(self, address: str, args: Tuple[OSCArg, ...]) -> None:
        for handler in list(self._handlers.get(address, [])):
            try:
                handler(args)
            except Exception:  # pragma: no cover - defensive
                continue


@dataclass
class AbletonOSCSubscriptionManager:
    """Helper that manages AbletonOSC start_listen/stop_listen subscriptions."""

    listener: OSCListener
    host: str
    port: int
    _subscriptions: List[Tuple[str, Tuple, Handler]] = field(default_factory=list)

    def subscribe_song_property(self, property_name: str, handler: Handler) -> None:
        listen_address = f"/live/song/get/{property_name}"
        self.listener.register(listen_address, handler)
        self.listener.send(self.host, self.port, f"/live/song/start_listen/{property_name}")
        self._subscriptions.append(("song", (property_name,), handler))

    def subscribe_track_property(
        self, track_index: int, property_name: str, handler: Handler
    ) -> None:
        listen_address = f"/live/track/get/{property_name}"
        self.listener.register(listen_address, handler)
        self.listener.send(
            self.host,
            self.port,
            f"/live/track/start_listen/{property_name}",
            track_index,
        )
        self._subscriptions.append(("track", (track_index, property_name), handler))

    def subscribe_device_parameter(
        self,
        track_index: int,
        device_index: int,
        parameter_index: int,
        handler: Handler,
    ) -> None:
        listen_address = \
            "/live/device/get/parameter/value"
        self.listener.register(listen_address, handler)
        self.listener.send(
            self.host,
            self.port,
            "/live/device/start_listen/parameter/value",
            track_index,
            device_index,
            parameter_index,
        )
        self._subscriptions.append(
            (
                "device",
                (track_index, device_index, parameter_index, listen_address),
                handler,
            )
        )

    def close(self) -> None:
        for category, payload, handler in self._subscriptions:
            if category == "song":
                (property_name,) = payload
                self.listener.send(
                    self.host,
                    self.port,
                    f"/live/song/stop_listen/{property_name}",
                )
                self.listener.unregister(f"/live/song/get/{property_name}", handler)
            elif category == "track":
                track_index, property_name = payload
                self.listener.send(
                    self.host,
                    self.port,
                    f"/live/track/stop_listen/{property_name}",
                    track_index,
                )
                self.listener.unregister(
                    f"/live/track/get/{property_name}", handler
                )
            elif category == "device":
                track_index, device_index, parameter_index, listen_address = payload
                self.listener.send(
                    self.host,
                    self.port,
                    "/live/device/stop_listen/parameter/value",
                    track_index,
                    device_index,
                    parameter_index,
                )
                self.listener.unregister(listen_address, handler)
        self._subscriptions.clear()
