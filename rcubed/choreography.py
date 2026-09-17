"""Face turns and whole-cube rotations, built from Robot primitives.

Every sequence here follows the rules verified on the hardware in March/April
2026 (legacy/docs/RULES.md):

  * a face turn needs all four grippers holding; the turning gripper goes
    B->target, then its RP retracts, it returns to B, and the RP re-engages;
  * a y rotation is done by grippers 2 & 8 (RPs 3 & 9 hold, RPs 1 & 7 retract);
  * an x rotation is done by grippers 0 & 6 (RPs 1 & 7 hold, RPs 3 & 9 retract);
  * always engage the new pair before retracting the old one;
  * a finger may sit at A or C only while both neighbours are at B or D.

The Choreographer keeps a physical-frame CubeModel in sync with every action,
so it always knows which logical face is at which robot position.
"""
from __future__ import annotations

import logging

from .config import GRIPPERS, GRIPPER_FACES, ROTATION_PAIR, RobotConfig
from .cube_model import CubeModel, parse_moves, rotations_to_home
from .robot import Robot

log = logging.getLogger("rcubed.choreo")

SUFFIX = {"cw": "", "ccw": "'", "180": "2"}
DIRECTION = {"": "cw", "'": "ccw", "2": "180"}


class Choreographer:
    def __init__(self, robot: Robot, cfg: RobotConfig, model: CubeModel | None = None):
        self.robot = robot
        self.cfg = cfg
        if model is None and robot.extra.get("cube"):
            model = CubeModel(robot.extra["cube"])  # orientation remembered from the last run
        self.model = model or CubeModel()
        # Orientation of the *notation frame*: face letters in a move sequence
        # refer to this frame. Explicit x/y tokens from the caller rotate it;
        # helper rotations the robot does on its own (to reach F or B) do not.
        self.frame = CubeModel(self.model.state)
        self.turns = 0
        self.rotations = 0
        self._sync()

    def _sync(self) -> None:
        """Keep the cube model in the robot's persisted state."""
        self.robot.extra["cube"] = self.model.state

    # ── RP management ───────────────────────────────────────────────────
    def engage(self, *grippers: int, slow: bool = True) -> None:
        speed = self.cfg.speed("rp_engage") if slow else 0
        for g in grippers:
            self.robot.set_rp(self.cfg.rp_of(g), "hold", speed=speed)
        self.robot.settle(self.cfg.t("rp_engage"))

    def retract(self, *grippers: int) -> None:
        for g in grippers:
            self.robot.set_rp(self.cfg.rp_of(g), "retracted", speed=self.cfg.speed("rp_retract"))
        self.robot.settle(self.cfg.t("rp_retract"))

    def engage_all(self) -> None:
        missing = [g for g in GRIPPERS if not self.robot.is_holding(g)]
        if missing:
            self.engage(*missing)

    def release_all(self) -> None:
        held = self.robot.holding()
        if held:
            self.retract(*held)

    def transfer_hold(self, pair: tuple[int, ...]) -> None:
        """Make `pair` the holding pair: engage it first, then release the others."""
        need = [g for g in pair if not self.robot.is_holding(g)]
        if need:
            self.engage(*need)
        release = [g for g in GRIPPERS if g not in pair and self.robot.is_holding(g)]
        if release:
            self.retract(*release)

    # ── startup / loading ───────────────────────────────────────────────
    def safe_startup(self) -> None:
        """Reach all-B / all-retracted from an unknown state without collisions."""
        log.info("safe startup (state unknown)")
        self.robot.init_accel()
        for g in GRIPPERS:
            self.robot.set_rp(self.cfg.rp_of(g), "retracted", speed=0)
        self.robot.settle(self.cfg.t("rp_retract"))
        for g in (0, 6):  # opposite pair: cannot collide with each other
            self.robot.set_gripper(g, "B", force=True)
        self.robot.settle(self.cfg.t("gripper_move") + 0.5)
        for g in (2, 8):  # now safe: 0 & 6 are known to be at B
            self.robot.set_gripper(g, "B", force=True)
        self.robot.settle(self.cfg.t("gripper_move") + 0.5)
        self.robot.save_state()

    def ensure_known(self) -> None:
        if not self.robot.state_known:
            self.safe_startup()
        else:
            self.robot.init_accel()

    def load_position(self) -> None:
        """Fingers clear for inserting a cube: 0&6 at B, 2 at C, 8 at A, all released."""
        self.ensure_known()
        self.release_all()
        targets = self.cfg.load_position()
        moved = False
        for g in (0, 6, 2, 8):
            if self.robot.gripper[g] != targets[g]:
                self.robot.set_gripper(g, targets[g])
                moved = True
            if g == 6 and moved:
                self.robot.settle(self.cfg.t("gripper_move"))
        if moved:
            self.robot.settle(self.cfg.t("gripper_move"))
        self.robot.save_state()

    # ── gripper resets ──────────────────────────────────────────────────
    def reset_gripper(self, g: int) -> None:
        """Bring one gripper back to B while the others keep holding the cube."""
        if self.robot.gripper[g] == "B":
            return
        others = [h for h in self.robot.holding() if h != g]
        if len(others) < 2:
            raise RuntimeError(f"cannot reset gripper {g}: only {others} holding")
        was_holding = self.robot.is_holding(g)
        if was_holding:
            self.retract(g)
        self.robot.set_gripper(g, "B")
        self.robot.settle(self.cfg.t("gripper_move"))
        if was_holding:
            self.engage(g)

    def prepare_for_turn(self) -> None:
        """All four holding, all four at B."""
        self.engage_all()
        for g in GRIPPERS:
            self.reset_gripper(g)

    # ── physical primitives ─────────────────────────────────────────────
    def turn(self, g: int, direction: str) -> None:
        """Turn the face at gripper g: direction 'cw' | 'ccw' | '180'."""
        self.prepare_for_turn()
        face = self.cfg.face_of(g)
        log.info("turn %s%s (gripper %d)", face, SUFFIX[direction], g)
        self.robot.set_gripper(g, self.cfg.turn_target(direction))
        self.robot.settle(self.cfg.t("turn_180" if direction == "180" else "turn_90"))
        self.retract(g)
        self.robot.set_gripper(g, "B")
        self.robot.settle(self.cfg.t("gripper_move"))
        self.engage(g)
        self.model.apply(face + SUFFIX[direction])
        self.turns += 1
        self._sync()

    def _prep_rotation(self, axis: str) -> None:
        pair = ROTATION_PAIR[axis]
        other = tuple(g for g in GRIPPERS if g not in pair)
        if any(self.robot.gripper[g] != "B" for g in pair):
            self.transfer_hold(other)
            for g in pair:
                if self.robot.gripper[g] != "B":
                    self.robot.set_gripper(g, "B")
            self.robot.settle(self.cfg.t("gripper_move"))
        self.transfer_hold(pair)
        if any(self.robot.gripper[g] != "B" for g in other):
            for g in other:
                if self.robot.gripper[g] != "B":
                    self.robot.set_gripper(g, "B")
            self.robot.settle(self.cfg.t("gripper_move"))

    def _rotation_speed(self, axis: str, g: int) -> int | None:
        return self.cfg.x_speed(g) if axis == "x" else None

    def rotate(self, rot: str) -> None:
        """Whole-cube rotation: 'y', "y'", 'y2', 'x', "x'", 'x2'."""
        axis = rot[0]
        if axis not in ROTATION_PAIR:
            raise ValueError(f"robot cannot perform {rot}")
        pair = ROTATION_PAIR[axis]
        log.info("rotate %s", rot)

        if rot.endswith("2"):
            at_ac = all(self.robot.gripper[g] in ("A", "C") for g in pair)
            if at_ac and self.cfg.half_turn_by_toggle(axis):
                self._prep_rotation_keep(axis)
                for g in pair:
                    target = "A" if self.robot.gripper[g] == "C" else "C"
                    self.robot.set_gripper(g, target, speed=self._rotation_speed(axis, g))
                self.robot.settle(self.cfg.t("half_rotation"))
                self._after_rotation(axis)
                self.model.apply(rot)
                self.rotations += 1
                self._sync()
            else:
                self.rotate(axis)
                self.rotate(axis)
            return

        self._prep_rotation(axis)
        for g, pos in self.cfg.rotation_targets(rot).items():
            self.robot.set_gripper(g, pos, speed=self._rotation_speed(axis, g))
        self.robot.settle(self.cfg.t(f"{axis}_rotation"))
        self._after_rotation(axis)
        self.model.apply(rot)
        self.rotations += 1
        self._sync()

    def _prep_rotation_keep(self, axis: str) -> None:
        """Like _prep_rotation but the pair stays at A/C (for a half turn by toggle)."""
        pair = ROTATION_PAIR[axis]
        other = tuple(g for g in GRIPPERS if g not in pair)
        self.transfer_hold(pair)
        if any(self.robot.gripper[g] != "B" for g in other):
            for g in other:
                if self.robot.gripper[g] != "B":
                    self.robot.set_gripper(g, "B")
            self.robot.settle(self.cfg.t("gripper_move"))

    def _after_rotation(self, axis: str) -> None:
        if axis == "x":
            for g in ROTATION_PAIR[axis]:
                self.robot.set_speed(g, 0)

    # ── logical API (standard cube notation) ────────────────────────────
    def move(self, token: str) -> None:
        """Execute one token: a face turn (R, U', F2 ...) or a rotation (x, y' ...)."""
        [token] = parse_moves(token)
        face, suffix = token[0], token[1:]
        if face == "z":
            raise ValueError("this robot cannot do z rotations; use x and y")
        if face in "xy":
            self.rotate(token)
            self.frame.apply(token)
            return
        sticker = self.frame.center(face)          # which face the letter means
        pos = self.model.position_of(sticker)      # where it physically is now
        if pos not in GRIPPER_FACES:
            # F and B have no gripper: spin the cube so the face reaches R.
            self.rotate("y'" if pos == "F" else "y")
            pos = self.model.position_of(sticker)
        self.turn(self.cfg.gripper_for_face(pos), DIRECTION[suffix])

    def execute(self, solution: str, home: bool = True) -> None:
        """Execute a move sequence written in the cube's current orientation
        (which is what a Kociemba solution computed from the current state is)."""
        tokens = parse_moves(solution)
        log.info("execute %d moves: %s", len(tokens), solution)
        self.frame = CubeModel(self.model.state)
        for i, tok in enumerate(tokens, 1):
            log.info("── %d/%d %s", i, len(tokens), tok)
            self.move(tok)
        if home:
            self.go_home()
            self.prepare_for_turn()
        self.frame = CubeModel(self.model.state)
        self.robot.save_state()

    def go_home(self) -> None:
        """Undo any net whole-cube rotation."""
        for tok in rotations_to_home(self.model):
            self.rotate(tok)

    def status(self) -> str:
        return (
            f"{self.robot.describe()}\n"
            f"orientation: " + " ".join(f"{f}={self.model.center(f)}" for f in "URFDLB")
            + f"\nturns={self.turns} rotations={self.rotations}"
        )
