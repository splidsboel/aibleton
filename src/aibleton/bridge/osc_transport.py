from __future__ import annotations

import socket
import struct
from dataclasses import dataclass, field
from typing import Iterable, List, Sequence, Tuple, Union


OSCArg = Union[int, float, str]
OSCMessage = Tuple[str, Tuple[OSCArg, ...]]


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


def decode_osc_packet(data: bytes) -> List[OSCMessage]:
    """Decode a raw OSC packet into a list of messages."""

    def _decode_message(payload: bytes) -> OSCMessage:
        idx = 0

        def read_string(offset: int) -> Tuple[str, int]:
            end = payload.find(b"\x00", offset)
            if end == -1:
                raise ValueError("Malformed OSC string")
            raw = payload[offset:end].decode("utf-8")
            offset = end + 1
            offset = (offset + 3) & ~0x03
            return raw, offset

        address, idx = read_string(idx)
        type_tags, idx = read_string(idx)
        if not type_tags.startswith(","):
            raise ValueError("OSC message missing type tag prefix")

        args: List[OSCArg] = []
        for tag in type_tags[1:]:
            if tag == "i":
                args.append(struct.unpack_from(">i", payload, idx)[0])
                idx += 4
            elif tag == "f":
                args.append(struct.unpack_from(">f", payload, idx)[0])
                idx += 4
            elif tag == "s":
                value, idx = read_string(idx)
                args.append(value)
            else:
                raise ValueError(f"Unsupported OSC type tag '{tag}'")
        return address, tuple(args)

    if data.startswith(b"#bundle"):
        idx = 16  # '#bundle' + 8-byte timetag
        messages: List[OSCMessage] = []
        while idx < len(data):
            size = struct.unpack_from(">i", data, idx)[0]
            idx += 4
            payload = data[idx : idx + size]
            idx += size
            messages.extend(decode_osc_packet(payload))
        return messages
    return [_decode_message(data)]


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
