"""
sequencer.py — Step sequencer and beat maker.
Grid-based pattern editing, drum programming, MIDI export.
"""
import os
import math
import json
import tempfile
from typing import Optional

class Step:
    """A single step in a pattern grid."""
    __slots__ = ('active', 'velocity')
    def __init__(self, active: bool = False, velocity: int = 100):
        self.active = active
        self.velocity = velocity  # 0-127 MIDI velocity

class TrackRow:
    """A row in the sequencer grid (one instrument)."""
    def __init__(self, name: str, note: int = 36, color: str = "#3b82f6"):
        self.name = name
        self.note = note  # MIDI note number
        self.color = color
        self.steps: list[Step] = []

    def set_steps(self, count: int):
        self.steps = [Step() for _ in range(count)]

    def toggle_step(self, index: int):
        if 0 <= index < len(self.steps):
            self.steps[index].active = not self.steps[index].active

    def set_step(self, index: int, active: bool, velocity: int = 100):
        if 0 <= index < len(self.steps):
            self.steps[index].active = active
            self.steps[index].velocity = velocity


class Pattern:
    """A sequencer pattern — grid of steps x tracks."""
    def __init__(self, name: str = "Pattern 1", steps: int = 16, bpm: int = 120):
        self.name = name
        self.steps_count = steps
        self.bpm = bpm
        self.rows: list[TrackRow] = []
        self._init_default_rows()

    def _init_default_rows(self):
        """Create default drum kit rows."""
        defaults = [
            ("Kick", 36, "#ef4444"),
            ("Snare", 38, "#f59e0b"),
            ("Closed Hat", 42, "#10b981"),
            ("Open Hat", 46, "#3b82f6"),
            ("Clap", 39, "#8b5cf6"),
            ("Tom Low", 45, "#ec4899"),
            ("Tom Mid", 47, "#14b8a6"),
            ("Crash", 49, "#f97316"),
        ]
        for name, note, color in defaults:
            row = TrackRow(name, note, color)
            row.set_steps(self.steps_count)
            self.rows.append(row)

    def add_row(self, name: str, note: int = 60, color: str = "#3b82f6"):
        row = TrackRow(name, note, color)
        row.set_steps(self.steps_count)
        self.rows.append(row)

    def remove_row(self, index: int):
        if 0 <= index < len(self.rows):
            self.rows.pop(index)

    def set_steps_count(self, count: int):
        self.steps_count = count
        for row in self.rows:
            row.set_steps(count)

    def get_grid(self) -> list:
        """Return the pattern as a grid of booleans."""
        return [[s.active for s in row.steps] for row in self.rows]

    def set_grid(self, grid: list):
        """Set the pattern from a grid of booleans."""
        for i, row in enumerate(self.rows):
            for j, active in enumerate(grid[i] if i < len(grid) else []):
                if j < len(row.steps):
                    row.steps[j].active = active

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "steps": self.steps_count,
            "bpm": self.bpm,
            "rows": [{
                "name": r.name,
                "note": r.note,
                "color": r.color,
                "steps": [{"a": s.active, "v": s.velocity} for s in r.steps]
            } for r in self.rows]
        }

    def from_dict(self, data: dict):
        self.name = data.get("name", "Pattern")
        self.steps_count = data.get("steps", 16)
        self.bpm = data.get("bpm", 120)
        self.rows = []
        for r_data in data.get("rows", []):
            row = TrackRow(r_data["name"], r_data.get("note", 60), r_data.get("color", "#3b82f6"))
            row.set_steps(self.steps_count)
            for i, s_data in enumerate(r_data.get("steps", [])):
                if i < len(row.steps):
                    row.steps[i].active = s_data.get("a", False)
                    row.steps[i].velocity = s_data.get("v", 100)
            self.rows.append(row)
        if not self.rows:
            self._init_default_rows()

    def export_json(self, filepath: str) -> dict:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            return {"status": "exported", "path": filepath}
        except Exception as e:
            return {"error": str(e)}

    def import_json(self, filepath: str) -> dict:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.from_dict(data)
            return {"status": "imported", "path": filepath}
        except Exception as e:
            return {"error": str(e)}


# ─── Pattern presets ───
PATTERN_PRESETS = {
    "four-on-the-floor": {
        "Kick":      [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
        "Snare":     [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        "Closed Hat":[1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
        "Open Hat":  [0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,1,0],
    },
    "trap": {
        "Kick":      [1,0,0,0, 0,0,1,0, 0,0,0,0, 0,0,0,0],
        "Snare":     [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        "Closed Hat":[1,1,1,1, 1,1,1,1, 1,1,1,1, 1,1,1,1],
        "Open Hat":  [0,0,0,0, 0,0,0,1, 0,0,0,0, 0,0,0,0],
    },
    "breakbeat": {
        "Kick":      [1,0,0,0, 0,0,0,0, 1,0,0,0, 0,0,0,0],
        "Snare":     [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,1],
        "Closed Hat":[1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
    },
    "boom-bap": {
        "Kick":      [1,0,0,0, 0,0,1,0, 0,0,0,0, 1,0,0,0],
        "Snare":     [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        "Closed Hat":[1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
    },
    "drum-and-bass": {
        "Kick":      [1,0,0,0, 0,0,0,0, 0,0,1,0, 0,0,0,0],
        "Snare":     [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        "Closed Hat":[1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
        "Open Hat":  [0,0,1,0, 0,0,1,0, 0,0,1,0, 0,0,1,0],
    },
    "reggaeton": {
        "Kick":      [1,0,0,0, 0,0,1,0, 1,0,0,0, 0,0,1,0],
        "Snare":     [0,0,0,1, 0,0,0,0, 0,0,0,1, 0,0,0,0],
        "Closed Hat":[1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
    },
}


class Sequencer:
    """Main sequencer controller."""

    def __init__(self):
        self.patterns: list[Pattern] = [Pattern("Pattern 1")]
        self.current_pattern: int = 0
        self.playing: bool = False
        self.current_step: int = 0

    def get_current_pattern(self) -> Pattern:
        return self.patterns[self.current_pattern]

    def add_pattern(self, name: str = None) -> Pattern:
        name = name or f"Pattern {len(self.patterns) + 1}"
        p = Pattern(name)
        self.patterns.append(p)
        return p

    def apply_preset(self, preset_name: str) -> dict:
        """Apply a named preset to the current pattern."""
        preset = PATTERN_PRESETS.get(preset_name)
        if not preset:
            return {"error": f"Preset '{preset_name}' not found. Available: {list(PATTERN_PRESETS.keys())}"}
        pattern = self.get_current_pattern()
        for row in pattern.rows:
            row_values = preset.get(row.name)
            if row_values:
                for i, val in enumerate(row_values):
                    if i < len(row.steps):
                        row.steps[i].active = bool(val)
        return {"status": "applied", "preset": preset_name}

    def list_presets(self) -> list:
        return list(PATTERN_PRESETS.keys())

    def get_status(self) -> dict:
        return {
            "playing": self.playing,
            "current_step": self.current_step,
            "current_pattern": self.current_pattern,
            "pattern_count": len(self.patterns),
            "bpm": self.get_current_pattern().bpm,
        }
