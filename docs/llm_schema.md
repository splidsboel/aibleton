# LLM Command Schema v0.1

This document describes the JSON structure the LLM must output so the assistant can translate natural-language requests into Ableton actions. The schema is intentionally simple and mirrors the existing orchestration actions.

## Envelope

```json
{
  "intent": "create_clip",
  "summary": "Create a 4 bar drum clip",
  "actions": [ ... ]
}
```

- `intent`: free-form string summarizing the request.
- `summary`: natural-language description of what the assistant plans to do.
- `actions`: ordered list of actionable objects. Each action has a required `type` field plus type-specific properties (see below).

## Action Types

### `set_tempo`
```json
{
  "type": "set_tempo",
  "tempo_bpm": 128.0
}
```
- `tempo_bpm`: number (float). Range validation: 20–300 BPM.

### `set_track_volume`
```json
{
  "type": "set_track_volume",
  "track_name": "Drums",
  "volume_db": -6.0
}
```
- `track_name`: string, case-insensitive match to Live track names.
- `volume_db`: number in dB.

### `create_midi_clip`
```json
{
  "type": "create_midi_clip",
  "track_name": "Drums",
  "clip_name": "Intro Beat",
  "length_bars": 4,
  "pattern": "kick-snare",
  "notes": [
    [36, 0.0, 0.5, 110, 0],
    [38, 1.0, 0.5, 100, 0]
  ]
}
```
- `length_bars`: integer > 0.
- `pattern`: optional string for preset patterns (fall back if `notes` omitted).
- `notes`: optional list of `[pitch, start_beat, duration_beats, velocity, mute]`.

### `launch_clip`
```json
{
  "type": "launch_clip",
  "track_name": "Drums",
  "clip_name": "Intro Beat"
}
```

### `set_device_parameter`
```json
{
  "type": "set_device_parameter",
  "track_name": "Drums",
  "device_name": "Saturator",
  "parameter_name": "Drive",
  "value": 24.0
}
```

## Validation & Error Handling
- The orchestration layer will reject unknown `type` values or missing required fields.
- Numeric ranges (BPM, velocity 0–127, etc.) should be enforced before committing the plan.
- Future schema versions should bump a `schema_version` field to ease migrations.