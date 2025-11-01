from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


try:  # pragma: no cover - Python 3.11 ships tomllib
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback for <3.11
    import tomli as tomllib  # type: ignore


DEFAULT_CONFIG_FILENAMES = (
    "aibleton.toml",
    ".aibleton.toml",
    "config/aibleton.toml",
)


@dataclass(frozen=True)
class OSCBridgeConfig:
    """Configuration for the Ableton OSC bridge."""

    host: str = "127.0.0.1"
    port: int = 11000
    send: bool = False
    timeout: float = 1.0

    @classmethod
    def from_toml(cls, path: Path) -> "OSCBridgeConfig":
        data = tomllib.loads(path.read_text())
        return cls.from_dict(data.get("bridge", {}))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OSCBridgeConfig":
        return cls(
            host=data.get("host", cls.host),
            port=int(data.get("port", cls.port)),
            send=bool(data.get("send", cls.send)),
            timeout=float(data.get("timeout", cls.timeout)),
        )

    @classmethod
    def discover(cls, cwd: Path) -> Optional["OSCBridgeConfig"]:
        for name in DEFAULT_CONFIG_FILENAMES:
            candidate = cwd / name
            if candidate.exists():
                return cls.from_toml(candidate)
        return None
