from __future__ import annotations

import argparse
import logging
from pathlib import Path

from dataclasses import replace

from ..bridge.config import OSCBridgeConfig
from ..bridge.logging import LoggingBridge
from ..bridge.osc import AbletonOSCBridge
from ..context.provider import MutableContextProvider
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
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper()))

    context_provider = MutableContextProvider(fixture_path=args.fixture)
    rule_based = RuleBasedOrchestrator(context_provider=context_provider)
    structured_parser = StructuredPlanParser()
    orchestrator = HybridOrchestrator(
        structured_parser=structured_parser, fallback=rule_based
    )
    safety = SafetyManager()

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

    if args.bridge == "osc":
        bridge = AbletonOSCBridge(
            config=config,
            context_provider=context_provider,
        )
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


def _print_help() -> None:
    print("Examples:")
    print("  set tempo to 128")
    print("  set drums volume to -5")
    print("  turn hi hat down by 3")
    print("  create 4 bar clip named intro on drums")
    print("  launch intro beat clip on drums")


def _confirm() -> bool:
    response = input("Proceed? [y/N] ").strip().lower()
    return response in {"y", "yes"}


if __name__ == "__main__":
    main()
