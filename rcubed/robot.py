"""Servo primitives with a collision guard and persisted state.

The Robot knows where every gripper and rack-and-pinion (RP) servo is, refuses
gripper moves that would sweep two adjacent fingers through the same spot, and
saves its state between runs so the next script can skip the safe startup.

It knows nothing about cubes. That is choreography.py's job.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from .backends import Backend
from .config import ADJACENT, GRIPPERS, POSITIONS, RPS, RP_STATES, STATE_FILE, RobotConfig

log = logging.getLogger("rcubed.robot")


class CollisionError(RuntimeError):
    pass


class UnknownStateError(RuntimeError):
    pass


def positions_swept(frm: str, to: str) -> set[str]:
    """Positions a gripper passes through (excluding the start, including the end)."""
    i, j = POSITIONS.index(frm), POSITIONS.index(to)
    lo, hi = sorted((i, j))
    return set(POSITIONS[lo : hi + 1]) - {frm}


class Robot:
    def __init__(self, backend: Backend, cfg: RobotConfig, state_file: Path = STATE_FILE):
        self.backend = backend
        self.cfg = cfg
        self.state_file = Path(state_file)
        self.gripper: dict[int, str | None] = {g: None for g in GRIPPERS}
        self.rp: dict[int, str | None] = {r: None for r in RPS}

    # ── state ───────────────────────────────────────────────────────────
    @property
    def state_known(self) -> bool:
        return all(v is not None for v in self.gripper.values()) and all(
            v is not None for v in self.rp.values()
        )

    def holding(self) -> tuple[int, ...]:
        """Grippers whose RP is engaged."""
        return tuple(g for g in GRIPPERS if self.rp[self.cfg.rp_of(g)] == "hold")

    def is_holding(self, g: int) -> bool:
        return self.rp[self.cfg.rp_of(g)] == "hold"

    def describe(self) -> str:
        gs = " ".join(f"{g}:{self.gripper[g] or '?'}" for g in GRIPPERS)
        rs = " ".join(f"{r}:{(self.rp[r] or '?')[:4]}" for r in RPS)
        return f"grippers[{gs}]  rp[{rs}]"

    # ── safety ──────────────────────────────────────────────────────────
    def check_gripper_move(self, g: int, to: str) -> None:
        """Rule: a finger may only be at, or sweep through, A or C while both
        adjacent fingers sit at B or D. Opposite fingers can never collide."""
        frm = self.gripper[g]
        if frm is None:
            raise UnknownStateError(f"gripper {g} position unknown; run safe startup")
        if positions_swept(frm, to) & {"A", "C"}:
            for a in ADJACENT[g]:
                if self.gripper[a] not in ("B", "D"):
                    raise CollisionError(
                        f"gripper {g} {frm}->{to} would hit gripper {a} at {self.gripper[a]}"
                    )

    # ── primitives ──────────────────────────────────────────────────────
    def set_gripper(self, g: int, pos: str, *, speed: int | None = None, force: bool = False) -> None:
        if pos not in POSITIONS:
            raise ValueError(pos)
        if not force:
            self.check_gripper_move(g, pos)
        if speed is not None:
            self.backend.set_speed(g, speed)
        self.backend.set_target(g, self.cfg.gripper_us(g, pos))
        log.debug("gripper %d -> %s", g, pos)
        self.gripper[g] = pos

    def set_rp(self, r: int, state: str, *, speed: int) -> None:
        if state not in RP_STATES:
            raise ValueError(state)
        self.backend.set_speed(r, speed)
        self.backend.set_target(r, self.cfg.rp_us(r, state))
        log.debug("rp %d -> %s (speed %d)", r, state, speed)
        self.rp[r] = state

    def set_speed(self, channel: int, speed: int) -> None:
        self.backend.set_speed(channel, speed)

    def set_raw(self, channel: int, us: int) -> None:
        """Calibration only: bypasses all checks and state tracking."""
        self.backend.set_target(channel, us)

    def init_accel(self) -> None:
        for g in GRIPPERS:
            self.backend.set_accel(g, self.cfg.speed("gripper_accel"))

    def settle(self, seconds: float) -> None:
        """Wait the configured time, then keep waiting while the Maestro reports
        speed-limited channels still ramping (bounded by settle_poll_timeout)."""
        self.backend.sleep(seconds)
        deadline = time.monotonic() + self.cfg.t("settle_poll_timeout")
        while self.backend.moving() and time.monotonic() < deadline:
            self.backend.sleep(0.05)

    # ── persistence ─────────────────────────────────────────────────────
    @staticmethod
    def _boot_time() -> float | None:
        try:
            with open("/proc/uptime") as f:
                return time.time() - float(f.read().split()[0])
        except OSError:
            return None  # not Linux; skip the reboot check

    def save_state(self) -> None:
        if not self.state_known:
            return
        data = {
            "clean": True,
            "timestamp": time.time(),
            "grippers": {str(g): p for g, p in self.gripper.items()},
            "rp": {str(r): s for r, s in self.rp.items()},
        }
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(data, indent=2))

    def load_state(self) -> bool:
        """Restore a clean state written since the last boot. Returns success."""
        try:
            data = json.loads(self.state_file.read_text())
        except (OSError, ValueError):
            return False
        if not data.get("clean"):
            return False
        boot = self._boot_time()
        if boot is not None and data.get("timestamp", 0) < boot:
            return False
        try:
            self.gripper = {g: data["grippers"][str(g)] for g in GRIPPERS}
            self.rp = {r: data["rp"][str(r)] for r in RPS}
        except KeyError:
            self.gripper = {g: None for g in GRIPPERS}
            self.rp = {r: None for r in RPS}
            return False
        return True

    def invalidate_state(self) -> None:
        try:
            data = json.loads(self.state_file.read_text())
            data["clean"] = False
            self.state_file.write_text(json.dumps(data, indent=2))
        except (OSError, ValueError):
            pass

    def close(self) -> None:
        self.save_state()
        self.backend.close()
