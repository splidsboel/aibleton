from __future__ import annotations

import socket
import struct
from dataclasses import dataclass, field
from typing import Iterable, List, Sequence, Tuple, Union


OSCArg = Union[int, float, str]
OSCMessage = Tuple[str, Sequence[OSCArg]]


def _pad(data: bytes) -> bytes:
    padding = (4 - (len(data) % 4)) % 4
    return data + (b"\x00" * padding)


def encode_osc_message(address: str, args: Sequence[OSCArg]) -> bytes:
    if not address.startswith("/"):
        raise ValueError(f"OSC address must start with '/': {address}")

    encoded_address = _pad(address.encode("utf-8") + b"\x00")
    type_tags = [","]
    encoded_args: List[bytes] = []

    for arg in args:
        if isinstance(arg, int):
            type_tags.append("i")
            encoded_args.append(struct.pack(">i", arg))
        elif isinstance(arg, float):
            type_tags.append("f")
            encoded_args.append(struct.pack(">f", arg))
        elif isinstance(arg, str):
            type_tags.append("s")
            encoded_args.append(_pad(arg.encode("utf-8") + b"\x00"))
        else:
            raise TypeError(f"Unsupported OSC argument type: {type(arg)!r}")

    encoded_types = _pad("".join(type_tags).encode("utf-8") + b"\x00")
    return b"".join([encoded_address, encoded_types, *encoded_args])


class OSCTransport:
    """Abstract transport for sending OSC messages."""

    def send(self, address: str, args: Sequence[OSCArg]) -> None:
        raise NotImplementedError


@dataclass
class UDPOSCTransport(OSCTransport):
    """UDP-based OSC transport."""

    host: str
    port: int
    timeout: float = 1.0
    _socket: socket.socket = field(init=False)

    def __post_init__(self) -> None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.settimeout(self.timeout)

    def send(self, address: str, args: Sequence[OSCArg]) -> None:
        payload = encode_osc_message(address, args)
        self._socket.sendto(payload, (self.host, self.port))


@dataclass
class RecordingOSCTransport(OSCTransport):
    """Transport that records messages for later inspection (testing)."""

    messages: List[OSCMessage] = field(default_factory=list)

    def send(self, address: str, args: Sequence[OSCArg]) -> None:
        self.messages.append((address, tuple(args)))

    def __iter__(self) -> Iterable[OSCMessage]:
        return iter(self.messages)
