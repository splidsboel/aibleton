from __future__ import annotations

import argparse
import logging
from pathlib import Path

from dataclasses import replace

from ..bridge.config import OSCBridgeConfig
from ..bridge.logging import LoggingBridge
from ..bridge.osc import AbletonOSCBridge
from ..bridge.osc_listener import AbletonOSCSubscriptionManager, OSCListener
from ..context import AbletonOSCContextProvider, MutableContextProvider
from ..context.live_provider import OSCQueryError
from ..orchestrator.hybrid import HybridOrchestrator
from ..orchestrator.rule_based import RuleBasedOrchestrator
from ..orchestrator.structured import StructuredPlanParser
from ..orchestrator.schema import OrchestrationError
from ..safety.manager import SafetyManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Natural-language Ableton Live assistant (MVP scaffold)."
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "context"
        / "fixtures"
        / "default_set.json",
        help="Path to Live context fixture.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity.",
    )
    parser.add_argument(
        "--bridge",
        choices=["logging", "osc"],
        default="logging",
        help="Execution backend to use.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to aibleton TOML config (overrides defaults).",
    )
    parser.add_argument(
        "--osc-host",
        default="127.0.0.1",
        help="OSC host for Ableton bridge.",
    )
    parser.add_argument(
        "--osc-port",
        type=int,
        default=11000,
        help="OSC port for Ableton bridge.",
    )
    parser.add_argument(
        "--osc-send",
        action="store_true",
        help="Enable actual UDP transport for OSC bridge (otherwise dry-run).",
    )
    parser.add_argument(
        "--live-listen",
        action="store_true",
        help="Subscribe to AbletonOSC listeners (tempo, track volume) for live updates.",
    )
    parser.add_argument(
        "--inspect-limit",
        type=int,
        default=3,
        help="Number of device parameters to display per device during /inspect.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper()))

    parser_defaults = {
        "osc_host": parser.get_default("osc_host"),
        "osc_port": parser.get_default("osc_port"),
        "osc_send": parser.get_default("osc_send"),
    }
    config = None
    if args.config:
        config = OSCBridgeConfig.from_toml(args.config)
    else:
        discovered = OSCBridgeConfig.discover(Path.cwd())
        if discovered:
            config = discovered
    if config is None:
        config = OSCBridgeConfig(
            host=args.osc_host,
            port=args.osc_port,
            send=args.osc_send,
        )
    else:
        if args.osc_host != parser_defaults["osc_host"]:
            config = replace(config, host=args.osc_host)
        if args.osc_port != parser_defaults["osc_port"]:
            config = replace(config, port=args.osc_port)
        if args.osc_send != parser_defaults["osc_send"]:
            config = replace(config, send=args.osc_send)

    live_context = None
    if args.bridge == "osc":
        try:
            live_provider = AbletonOSCContextProvider(config=config)
            live_context = live_provider.snapshot()
            live_provider.close()
            print("[context] Loaded live snapshot via AbletonOSC.")
        except OSCQueryError as exc:
            print(f"[context] Live snapshot failed ({exc}); using fixture {args.fixture}.")

    if live_context is not None:
        context_provider = MutableContextProvider(initial_context=live_context)
    else:
        context_provider = MutableContextProvider(fixture_path=args.fixture)

    rule_based = RuleBasedOrchestrator(context_provider=context_provider)
    structured_parser = StructuredPlanParser()
    orchestrator = HybridOrchestrator(
        structured_parser=structured_parser, fallback=rule_based
    )
    safety = SafetyManager()

    listener: OSCListener | None = None
    subscription: AbletonOSCSubscriptionManager | None = None
    subscription_enabled = False

    if args.bridge == "osc":
        bridge = AbletonOSCBridge(
            config=config,
            context_provider=context_provider,
        )

        if args.live_listen and live_context is not None:
            try:
                listener = OSCListener(host="0.0.0.0", port=config.listen_port or 0)
                subscription = AbletonOSCSubscriptionManager(
                    listener=listener,
                    host=config.host,
                    port=config.port,
                )

                def _tempo_handler(args: tuple[float, ...]) -> None:
                    if not args:
                        return
                    tempo = float(args[-1])
                    context_provider.update_tempo(tempo)

                def _track_volume_handler(args: tuple[float, ...]) -> None:
                    if len(args) < 2:
                        return
                    track_index = int(args[0])
                    gain = float(args[1])
                    context_provider.update_track_volume_linear(track_index, gain)

                subscription.subscribe_song_property("tempo", _tempo_handler)
                snapshot = context_provider.snapshot()
                for track in snapshot.tracks:
                    subscription.subscribe_track_property(
                        track.track_index,
                        "volume",
                        _track_volume_handler,
                    )
                subscription_enabled = True
                print(
                    f"[context] Live listeners enabled (tempo, track volume) on port {listener.port}."
                )
            except Exception as exc:  # pragma: no cover - requires live OSC
                subscription = None
                if listener is not None:
                    listener.close()
                    listener = None
                print(f"[context] Unable to enable live listeners: {exc}")
    else:
        bridge = LoggingBridge(context_provider=context_provider)

    print("aibleton assistant MVP — type commands, 'help' for tips, 'quit' to exit.")
    print("Supported intents: set tempo, adjust volume, create clip, launch clip.")
    if args.bridge == "osc":
        if config.send:
            print(
                f"OSC bridge sending to {config.host}:{config.port} "
                f"(timeout {config.timeout:.1f}s)."
            )
        else:
            print(
                "OSC bridge dry-run mode; no UDP packets will be emitted. "
                "Use --osc-send or set send=true in config."
            )
        if args.live_listen and not subscription_enabled:
            print(
                "[context] Live listeners inactive; ensure AbletonOSC is reachable and listen_port is available."
            )

    try:
        while True:
            try:
                raw = input("aibleton> ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nBye.")
                break

            if not raw:
                continue
            if raw.lower() in {"quit", "exit"}:
                print("Bye.")
                break
            if raw.lower() in {"inspect", "/inspect"}:
                _print_context(context_provider, parameter_limit=args.inspect_limit)
                continue
            if raw.lower() == "help":
                _print_help()
                continue

            try:
                plan = orchestrator.plan(raw)
            except OrchestrationError as exc:
                print(f"[orchestrator] {exc}")
                continue

            explanation = None
            if safety.requires_confirmation(plan):
                explanation = safety.explanation(plan)
                print(f"[safety] Confirmation required: {explanation}")
                if not _confirm():
                    print("[safety] Cancelled.")
                    continue

            bridge.execute(plan)
            if explanation:
                print(f"[safety] Proceeded with: {explanation}")
            print(f"[ok] {plan.summary}")
    finally:
        if subscription is not None:
            subscription.close()
        if listener is not None:
            listener.close()


def _print_help() -> None:
    print("Examples:")
    print("  set tempo to 128")
    print("  set drums volume to -5")
    print("  turn hi hat down by 3")
    print("  create 4 bar clip named intro on drums")
    print("  launch intro beat clip on drums")
    print("  inspect  # prints current context snapshot")


def _confirm() -> bool:
    response = input("Proceed? [y/N] ").strip().lower()
    return response in {"y", "yes"}


def _print_context(provider: MutableContextProvider, parameter_limit: int = 3) -> None:
    context = provider.snapshot()
    print(
        f"[context] Tempo {context.tempo_bpm:.1f} BPM | scenes={context.scene_count} | tracks={len(context.tracks)}"
    )
    for track in context.tracks:
        print(
            f"  track {track.track_index}: {track.name} (vol ≈ {track.volume_db:.1f} dB, clips={len(track.clips)}, devices={len(track.devices)})"
        )
        for clip in track.clips:
            clip_type = "MIDI" if clip.is_midi else "Audio"
            print(
                f"    clip slot {clip.slot_index}: {clip.name} [{clip_type}] (scene {clip.scene_index})"
            )
        for device in track.devices:
            params = ", ".join(
                f"{param.name}={param.value:.3f}"
                for param in device.parameters[:parameter_limit]
            )
            extra = ""
            if len(device.parameters) > parameter_limit:
                extra = f", …(+{len(device.parameters) - parameter_limit})"
            label = f"[{params}{extra}]" if params or extra else ""
            print(
                f"    device {device.device_index}: {device.name} {label}".rstrip()
            )


if __name__ == "__main__":
    main()
