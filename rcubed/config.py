"""Load config/robot.json — the single source of truth for calibration, speeds and timing.

Nothing else in the package may hardcode a pulse width or a delay.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"
DEFAULT_CONFIG = CONFIG_DIR / "robot.json"
STATE_FILE = CONFIG_DIR / "robot_state.json"

GRIPPERS = (0, 2, 6, 8)
RPS = (1, 3, 7, 9)
POSITIONS = "ABCD"
RP_STATES = ("retracted", "hold")
# Physical positions that have a gripper. F and B have none.
GRIPPER_FACES = ("U", "R", "L", "D")
# Adjacent gripper pairs can collide; opposite pairs cannot.
ADJACENT = {0: (2, 8), 6: (2, 8), 2: (0, 6), 8: (0, 6)}
OPPOSITE = {0: 6, 6: 0, 2: 8, 8: 2}
# Which gripper pair performs which whole-cube rotation axis.
ROTATION_PAIR = {"y": (2, 8), "x": (0, 6)}


@dataclass(frozen=True)
class RobotConfig:
    raw: dict[str, Any]
    path: Path | None = None

    @classmethod
    def load(cls, path: Path | str | None = None) -> "RobotConfig":
        p = Path(path) if path else DEFAULT_CONFIG
        with open(p) as f:
            return cls(json.load(f), p)

    def scaled_timing(self, factor: float) -> "RobotConfig":
        """A copy with every wait multiplied by `factor`, for tuning runs.
        `settle_poll_timeout` is a safety bound and is left alone."""
        if factor == 1.0:
            return self
        timing = {
            k: (round(v * factor, 3) if isinstance(v, (int, float)) and k != "settle_poll_timeout" else v)
            for k, v in self.raw["timing"].items()
        }
        return RobotConfig({**self.raw, "timing": timing}, self.path)

    # ── grippers ────────────────────────────────────────────────────────
    def gripper_us(self, g: int, pos: str) -> int:
        return int(self.raw["grippers"][str(g)][pos])

    def face_of(self, g: int) -> str:
        return self.raw["grippers"][str(g)]["face"]

    def gripper_for_face(self, face: str) -> int:
        for g in GRIPPERS:
            if self.face_of(g) == face:
                return g
        raise KeyError(f"no gripper on face {face}")

    def rp_of(self, g: int) -> int:
        return int(self.raw["grippers"][str(g)]["rp"])

    def gripper_of_rp(self, r: int) -> int:
        for g in GRIPPERS:
            if self.rp_of(g) == r:
                return g
        raise KeyError(f"RP {r} belongs to no gripper")

    # ── rack-and-pinion ─────────────────────────────────────────────────
    def rp_us(self, r: int, state: str) -> int:
        return int(self.raw["rp"][str(r)][state])

    # ── choreography tables ─────────────────────────────────────────────
    def turn_target(self, direction: str) -> str:
        """Gripper position (from B) for a face turn: 'cw' | 'ccw' | '180'."""
        return self.raw["turn"][direction]

    def rotation_targets(self, rot: str) -> dict[int, str]:
        """Servo -> position for a quarter whole-cube rotation: 'y', "y'", 'x', "x'"."""
        return {int(k): v for k, v in self.raw["rotations"][rot].items()}

    def half_turn_by_toggle(self, axis: str) -> bool:
        return bool(self.raw["rotations"].get("half_turn_by_toggle", {}).get(axis, False))

    def load_position(self) -> dict[int, str]:
        return {int(k): v for k, v in self.raw["load_position"].items()}

    # ── speeds / timing ─────────────────────────────────────────────────
    def speed(self, key: str) -> int:
        return int(self.raw["speeds"][key])

    def rotation_speed(self, axis: str) -> int:
        """Speed limit for the longer-travelling gripper of a rotation pair (0 = unlimited)."""
        return int(self.raw["speeds"].get("rotation", {}).get(axis, 0))

    def t(self, key: str) -> float:
        return float(self.raw["timing"][key])

    # ── camera ──────────────────────────────────────────────────────────
    @property
    def camera(self) -> dict[str, Any]:
        return self.raw["camera"]
