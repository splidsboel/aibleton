#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import List

from aibleton.bridge.config import OSCBridgeConfig
from aibleton.bridge.osc import AbletonOSCBridge
from aibleton.context.provider import MutableContextProvider
from aibleton.orchestrator.schema import (
    ActionPlan,
    CreateMidiClipAction,
    LaunchClipAction,
    SetTempoAction,
    SetTrackVolumeAction,
)


@dataclass
class SmokeOptions:
    tempo: float | None
    volumes: List[str]
    launches: List[str]
    clips: List[str]
    config: Path | None
    fixture: Path


def build_plan(options: SmokeOptions, context_provider: MutableContextProvider) -> ActionPlan:
    actions = []
    summary_parts = []
    if options.tempo is not None:
        actions.append(SetTempoAction(tempo_bpm=options.tempo))
        summary_parts.append(f"tempo {options.tempo}")

    for spec in options.volumes:
        try:
            track, value = spec.split(":")
        except ValueError as exc:
            raise SystemExit(f"Invalid volume spec '{spec}', use TrackName:-6") from exc
        actions.append(SetTrackVolumeAction(track_name=track, volume_db=float(value)))
        summary_parts.append(f"volume {track}={value}dB")

    for spec in options.launches:
        try:
            track, clip = spec.split(":")
        except ValueError as exc:
            raise SystemExit(f"Invalid launch spec '{spec}', use TrackName:ClipName") from exc
        actions.append(LaunchClipAction(track_name=track, clip_name=clip))
        summary_parts.append(f"launch {track}:{clip}")

    for spec in options.clips:
        try:
            track, name, bars = spec.split(":")
        except ValueError as exc:
            raise SystemExit(f"Invalid clip spec '{spec}', use Track:ClipName:Bars") from exc
        actions.append(
            CreateMidiClipAction(
                track_name=track,
                clip_name=name,
                length_bars=int(bars),
                pattern="smoke",
            )
        )
        summary_parts.append(f"clip {track}:{name} ({bars} bars)")

    if not actions:
        raise SystemExit("No actions requested. Specify --tempo/--volume/--launch/--clip.")

    summary = "Smoke plan: " + ", ".join(summary_parts)
    plan = ActionPlan(
        intent="smoke_test",
        summary=summary,
        actions=actions,
        confidence=1.0,
    )
    # Ensure context provider sees future clip creations.
    context_provider.apply_plan(plan)
    return plan


def parse_args() -> SmokeOptions:
    parser = argparse.ArgumentParser(
        description="Send quick OSC smoke commands to Ableton Live."
    )
    parser.add_argument("--tempo", type=float, help="Set project tempo (BPM).")
    parser.add_argument(
        "--volume",
        action="append",
        default=[],
        help="Adjust track volume in dB, e.g. --volume 'Drums:-6'.",
    )
    parser.add_argument(
        "--launch",
        action="append",
        default=[],
        help="Launch a clip, e.g. --launch 'Drums:Intro Beat'.",
    )
    parser.add_argument(
        "--clip",
        action="append",
        default=[],
        help="Create a clip, e.g. --clip 'Drums:New Fill:4'.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to aibleton TOML config (defaults to discovery).",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "src"
        / "aibleton"
        / "context"
        / "fixtures"
        / "default_set.json",
        help="Fixture describing the Live set for track/clip resolution.",
    )
    args = parser.parse_args()
    return SmokeOptions(
        tempo=args.tempo,
        volumes=args.volume,
        launches=args.launch,
        clips=args.clip,
        config=args.config,
        fixture=args.fixture,
    )


def load_config(options: SmokeOptions) -> OSCBridgeConfig:
    if options.config:
        return OSCBridgeConfig.from_toml(options.config)
    discovered = OSCBridgeConfig.discover(Path.cwd())
    if discovered:
        return discovered
    return OSCBridgeConfig()


def main() -> None:
    options = parse_args()
    config = load_config(options)
    context_provider = MutableContextProvider(fixture_path=options.fixture)
    plan = build_plan(options, context_provider)

    bridge = AbletonOSCBridge(config=config, context_provider=context_provider)
    bridge.execute(plan)

    print(plan.summary)
    if not config.send:
        messages = bridge.recorded_messages()
        assert messages is not None
        print("Dry-run messages:")
        for address, args in messages:
            print(f"  {address} {list(args)}")


if __name__ == "__main__":
    main()
