# Ableton Bridge Integration Guide

This guide explains how to connect the assistant to Ableton Live through AbletonOSC (or a compatible Remote Script) so actions created by the orchestrator can reach your Live set.

## 1. Install AbletonOSC
1. Clone the [AbletonOSC repository](https://github.com/ideoforms/AbletonOSC).
2. Copy the `AbletonOSC` folder into `~/Music/Ableton/User Library/Remote Scripts/`.
3. Restart Ableton Live, open **Preferences → Link/Tempo/MIDI**, and enable AbletonOSC on an empty Control Surface slot.

Once Live is running with the script enabled, it will listen for UDP packets (default port `11000`).

## 2. Configure the Assistant
1. Duplicate `config/aibleton.example.toml` to any of the recognised filenames (e.g. `aibleton.toml`) and adjust the host/port if AbletonOSC runs on another machine.
2. Set `send = true` to allow UDP packets to leave the assistant.
3. Optional: adjust `timeout` to tune UDP send behaviour.

The CLI automatically discovers `aibleton.toml` in the project root or you can pass `--config path/to/file`.

## 3. Run the CLI
```bash
PYTHONPATH=src python -m aibleton.cli.main --bridge osc --osc-send
```

For dry-run evaluation without emitting network traffic, omit `--osc-send` or set `send = false` in the config.

## 4. Smoke-Test the Connection
Use the helper script to verify tempo, clip, and volume commands:
```bash
PYTHONPATH=src python scripts/bridge_smoke.py --tempo 128 --volume "Drums:-4" --launch "Drums:Intro Beat"
```

When `send = false`, the script prints the OSC messages it would send. With UDP enabled, monitor Live to confirm tempo/volume updates and clip launches.

## 5. Known Limitations
- `create_midi_clip` assumes AbletonOSC supports `/live/clip/create` with arguments `(track_index, slot_index, length_beats)`.
- Track resolution relies on the context snapshot. Keep it updated so the assistant can map track names to indices correctly.
- Device parameter changes are not yet implemented; extend `AbletonOSCBridge._messages_for_action` to add additional mappings.

Refer back to `docs/post_mvp_plan.md` for the broader roadmap and next milestones.
