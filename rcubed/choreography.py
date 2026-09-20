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

from .config import GRIPPERS, GRIPPER_FACES, POSITIONS, ROTATION_PAIR, RobotConfig
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
        """All four holding, all four at B.

        Grippers are reset in opposite pairs: while left/right hold the cube,
        top/bottom release together, swing to B together and re-engage
        together (and vice versa). An opposite pair holds the cube on its own,
        so this halves the reset time compared with one gripper at a time."""
        self.engage_all()
        for pair in ((2, 8), (0, 6)):
            off_b = [g for g in pair if self.robot.gripper[g] != "B"]
            if not off_b:
                continue
            other = tuple(g for g in GRIPPERS if g not in pair)
            self.transfer_hold(other)  # other pair holds; this pair releases together
            for g in off_b:
                self.robot.set_gripper(g, "B")
            self.robot.settle(self.cfg.t("gripper_move"))
            self.engage(*pair)

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

    def park_for_photo(self, axis: str = "y") -> None:
        """Hold the cube with one opposite pair parked at A/C (fingers out of the
        camera's view), the other pair released. For the y pair this is the load
        pose: 2 at C, 8 at A. The cube does not move."""
        pair = ROTATION_PAIR[axis]
        other = tuple(g for g in GRIPPERS if g not in pair)
        targets = self.cfg.rotation_targets(axis)  # the quarter-turn end positions
        holding = set(self.robot.holding())
        if all(self.robot.gripper[g] in ("A", "C") for g in pair) and holding <= set(pair):
            # Already parked (e.g. a cube just inserted at the load pose): just make
            # sure the pair is holding.
            need = [g for g in pair if g not in holding]
            if need:
                self.engage(*need)
            return
        if not holding:
            self.engage_all()  # first-ever move: nothing held yet, establish a safe baseline
        self.transfer_hold(other)
        for g in other:
            if self.robot.gripper[g] != "B":
                self.robot.set_gripper(g, "B")
        for g in pair:
            if self.robot.gripper[g] != targets[g]:
                self.robot.set_gripper(g, targets[g])
        self.robot.settle(self.cfg.t("gripper_move"))
        self.transfer_hold(pair)

    def _synced_speeds(self, axis: str, targets: dict[int, str]) -> dict[int, int]:
        """Per-servo speed limits so both grippers of the pair finish together.

        The Maestro moves each servo at its own limit, so with equal limits the one
        with the shorter travel arrives first and the pair twists the cube. Give the
        longer travel the configured speed and scale the other down in proportion."""
        base = self.cfg.rotation_speed(axis)
        if base <= 0:
            return {g: 0 for g in targets}
        dist = {
            g: abs(self.cfg.gripper_us(g, pos) - self.cfg.gripper_us(g, self.robot.gripper[g]))
            for g, pos in targets.items()
        }
        longest = max(dist.values()) or 1
        return {g: max(1, round(base * d / longest)) for g, d in dist.items()}

    def _move_pair(self, axis: str, targets: dict[int, str]) -> None:
        """Command both grippers of a rotation with synchronised speeds."""
        speeds = self._synced_speeds(axis, targets)
        for g in targets:  # set every speed before the first target so they start together
            self.robot.set_speed(g, speeds[g])
        for g, pos in targets.items():
            self.robot.set_gripper(g, pos)

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
                targets = {g: ("A" if self.robot.gripper[g] == "C" else "C") for g in pair}
                self._move_pair(axis, targets)
                self.robot.settle(self.cfg.t("half_rotation"))
                self._after_rotation(axis)
                self.model.apply(rot)
                self.rotations += 1
                self._sync()
            else:
                self.rotate(axis)
                self.rotate(axis)
            return

        # If the pair is already gripping the cube off B and this rotation steps them
        # back, that sweep *is* the rotation -- no reset, no handover. This is the
        # undo case: x right after x', y right after y'.
        stepped = self._step_targets(rot)
        if stepped is not None and set(self.robot.holding()) == set(pair):
            log.debug("  [direct: %s]", " ".join(f"{g}->{p}" for g, p in stepped.items()))
            self._move_pair(axis, stepped)
        else:
            self._prep_rotation(axis)
            self._move_pair(axis, self.cfg.rotation_targets(rot))
        self.robot.settle(self.cfg.t(f"{axis}_rotation"))
        self._after_rotation(axis)
        self.model.apply(rot)
        self.rotations += 1
        self._sync()

    def _rotation_step(self, rot: str) -> dict[int, int]:
        """How far each gripper of the pair travels for one quarter rotation, as a
        signed number of positions. Derived from the config's B-relative targets, so
        `x` = {0: -1, 6: +1} and `x'` is its mirror. The two grippers of a pair always
        step in opposite directions -- that is what turns the cube between them."""
        b = POSITIONS.index("B")
        return {g: POSITIONS.index(pos) - b for g, pos in self.cfg.rotation_targets(rot).items()}

    def _step_targets(self, rot: str) -> dict[int, str] | None:
        """Where a quarter rotation lands if each gripper simply steps on from where
        it is now. None when either gripper would run off the end of the A..D range.

        Because the pair steps in opposite directions, this only ever succeeds when
        the rotation undoes the one that parked them -- and then both land on B.
        Repeating a rotation in the same direction always runs one gripper off the
        end, and falls back to resetting through B."""
        out = {}
        for g, step in self._rotation_step(rot).items():
            here = self.robot.gripper[g]
            if here is None:
                return None
            i = POSITIONS.index(here) + step
            if not 0 <= i < len(POSITIONS):
                return None
            out[g] = POSITIONS[i]
        return out

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
        for g in ROTATION_PAIR[axis]:  # back to unlimited for face turns and resets
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
