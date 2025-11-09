from __future__ import annotations

import json
import unittest
from pathlib import Path

from aibleton.context.provider import MutableContextProvider
from aibleton.orchestrator.hybrid import HybridOrchestrator
from aibleton.orchestrator.rule_based import RuleBasedOrchestrator
from aibleton.orchestrator.schema import (
    ActionPlan,
    CreateMidiClipAction,
    OrchestrationError,
    SetDeviceParameterAction,
    SetTempoAction,
)
from aibleton.orchestrator.structured import StructuredPlanParser


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "aibleton"
    / "context"
    / "fixtures"
    / "default_set.json"
)


def build_hybrid() -> HybridOrchestrator:
    context = MutableContextProvider(fixture_path=FIXTURE_PATH)
    rule_based = RuleBasedOrchestrator(context_provider=context)
    parser = StructuredPlanParser()
    return HybridOrchestrator(structured_parser=parser, fallback=rule_based)


class StructuredParserTests(unittest.TestCase):
    def test_structured_parser_returns_action_plan(self) -> None:
        parser = StructuredPlanParser()
        payload = {
            "intent": "set_tempo",
            "summary": "Set tempo to 128 BPM.",
            "confidence": 0.9,
            "actions": [
                {"type": "set_tempo", "tempo_bpm": 128},
            ],
        }
        plan = parser.parse(json.dumps(payload))
        self.assertIsInstance(plan, ActionPlan)
        assert plan  # help type-checkers
        self.assertIsInstance(plan.actions[0], SetTempoAction)
        self.assertEqual(plan.actions[0].tempo_bpm, 128)

    def test_structured_parser_invalid_json_returns_none(self) -> None:
        parser = StructuredPlanParser()
        self.assertIsNone(parser.parse("This is not JSON"))

    def test_structured_parser_invalid_schema_raises(self) -> None:
        parser = StructuredPlanParser()
        bad_payload = {"summary": "Missing actions"}
        with self.assertRaises(OrchestrationError):
            parser.parse(json.dumps(bad_payload))

    def test_structured_parser_schema_version_mismatch(self) -> None:
        parser = StructuredPlanParser()
        payload = {
            "schema_version": "v0.0",
            "intent": "tempo",
            "summary": "",
            "actions": [{"type": "set_tempo", "tempo_bpm": 120}],
        }
        with self.assertRaises(OrchestrationError):
            parser.parse(json.dumps(payload))

    def test_structured_parser_rejects_bad_notes(self) -> None:
        parser = StructuredPlanParser()
        payload = {
            "intent": "bad notes",
            "summary": "",
            "actions": [
                {
                    "type": "create_midi_clip",
                    "track_name": "Drums",
                    "clip_name": "Bad",
                    "length_bars": 4,
                    "notes": [[36, 0, -1, 100, 0]],
                }
            ],
        }
        with self.assertRaises(OrchestrationError):
            parser.parse(json.dumps(payload))


class HybridOrchestratorTests(unittest.TestCase):
    def test_hybrid_orchestrator_fallback_rule_based(self) -> None:
        orchestrator = build_hybrid()
        plan = orchestrator.plan("set tempo to 124")
        self.assertEqual(plan.intent, "set_tempo")
        self.assertIsInstance(plan.actions[0], SetTempoAction)
        self.assertEqual(plan.actions[0].tempo_bpm, 124)

    def test_structured_command_round_trip(self) -> None:
        orchestrator = build_hybrid()
        payload = json.dumps(
            {
                "intent": "create_midi_clip",
                "summary": "Create clip on drums.",
                "actions": [
                    {
                        "type": "create_midi_clip",
                        "track_name": "Drums",
                        "clip_name": "Hybrid Test",
                        "length_bars": 4,
                        "pattern": "kick-snare",
                    }
                ],
            }
        )
        plan = orchestrator.plan(payload)
        self.assertIsInstance(plan.actions[0], CreateMidiClipAction)

    def test_rule_based_device_parameter(self) -> None:
        orchestrator = build_hybrid()
        plan = orchestrator.plan("set drums saturator drive to 18.5")
        self.assertEqual(plan.intent, "set_device_parameter")
        self.assertIsInstance(plan.actions[0], SetDeviceParameterAction)
        self.assertEqual(plan.actions[0].device_name, "Saturator")
        self.assertEqual(plan.actions[0].parameter_name, "Drive")
        self.assertAlmostEqual(plan.actions[0].value, 18.5)


if __name__ == "__main__":
    unittest.main()
